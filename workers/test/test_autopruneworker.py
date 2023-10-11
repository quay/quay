import json
import random
import time
import uuid
from unittest.mock import MagicMock, patch

from app import storage
from data import model
from data.database import AutoPruneTaskStatus, ImageStorageLocation, Tag
from data.model.oci.manifest import get_or_create_manifest
from data.model.oci.tag import list_repository_tag_history, retarget_tag
from data.queue import WorkQueue
from digest.digest_tools import sha256_digest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *
from util.bytes import Bytes
from util.timedeltastring import convert_to_timedelta
from workers.autopruneworker import AutoPruneWorker


def _populate_blob(content, repo):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = model.blob.store_blob_record_and_temp_link(
        "sellnsmall", repo.name, digest, location, len(content), 120
    )
    storage.put_content(["local_us"], model.storage.get_layer_path(blob), content)
    return blob, digest


def _create_manifest(repo):
    layer_json = json.dumps(
        {
            "id": "somelegacyid",
            "config": {
                "Labels": [],
            },
            "rootfs": {"type": "layers", "diff_ids": []},
            "history": [
                {
                    "created": "2018-04-03T18:37:09.284840891Z",
                    "created_by": "do something",
                },
            ],
        }
    )

    # Add a blob containing the config.
    _, config_digest = _populate_blob(layer_json, repo)

    v2_builder = DockerSchema2ManifestBuilder()
    v2_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    v2_manifest = v2_builder.build()

    return get_or_create_manifest(repo, v2_manifest, storage)


def _create_tag(repo, manifest, start=None):
    name = "tag-%s" % str(uuid.uuid4())
    now_ms = int(time.time() * 1000) if start is None else start
    created = Tag.create(
        name=name,
        repository=repo,
        lifetime_start_ms=now_ms,
        lifetime_end_ms=None,
        reversion=False,
        manifest=manifest,
        tag_kind=Tag.tag_kind.get_id("tag"),
    )
    return created


def _create_tags(repo, manifest, count, start_time_before=None):
    for _ in range(count):
        start_time = (
            _past_timestamp_ms(start_time_before) - random.randint(0, 1000000)
            if start_time_before is not None
            else None
        )
        _create_tag(repo, manifest, start_time)


def _assert_repo_tag_count(repo, count, assert_start_after=None):
    tags, _ = list_repository_tag_history(repo, 1, 100, active_tags_only=True)
    assert len(tags) == count
    if assert_start_after is not None:
        for tag in tags:
            assert tag.lifetime_start_ms > _past_timestamp_ms(assert_start_after)


def _past_timestamp_ms(time_delta):
    return int(time.time() * 1000) - convert_to_timedelta(time_delta).total_seconds() * 1000


def test_prune_multiple_repos_by_tag_count(initialized_db):
    with patch("data.model.autoprune.PAGINATE_SIZE", 2):
        assert model.autoprune.PAGINATE_SIZE == 2
        new_policy = model.autoprune.create_namespace_autoprune_policy(
            "sellnsmall", {"method": "number_of_tags", "value": 5}, create_task=True
        )
        repo1 = model.repository.create_repository(
            "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
        )
        repo2 = model.repository.create_repository(
            "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
        )
        repo3 = model.repository.create_repository(
            "sellnsmall", "repo3", None, repo_kind="image", visibility="public"
        )
        manifest_repo1 = _create_manifest(repo1)
        manifest_repo2 = _create_manifest(repo2)
        manifest_repo3 = _create_manifest(repo3)

        _create_tags(repo1, manifest_repo1.manifest, 10)
        _create_tags(repo2, manifest_repo2.manifest, 3)
        _create_tags(repo3, manifest_repo3.manifest, 5)

        _assert_repo_tag_count(repo1, 10)
        _assert_repo_tag_count(repo2, 3)
        _assert_repo_tag_count(repo3, 5)

        worker = AutoPruneWorker()
        worker.prune()

        _assert_repo_tag_count(repo1, 5)
        _assert_repo_tag_count(repo2, 3)
        _assert_repo_tag_count(repo3, 5)

        task = model.autoprune.fetch_autoprune_task_by_namespace_id(new_policy.namespace_id)
        assert task.status == "success"


def test_prune_multiple_repos_by_creation_date(initialized_db):
    with patch("data.model.autoprune.PAGINATE_SIZE", 2):
        assert model.autoprune.PAGINATE_SIZE == 2
        new_policy = model.autoprune.create_namespace_autoprune_policy(
            "sellnsmall", {"method": "creation_date", "value": "1w"}, create_task=True
        )
        repo1 = model.repository.create_repository(
            "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
        )
        repo2 = model.repository.create_repository(
            "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
        )
        repo3 = model.repository.create_repository(
            "sellnsmall", "repo3", None, repo_kind="image", visibility="public"
        )
        manifest_repo1 = _create_manifest(repo1)
        manifest_repo2 = _create_manifest(repo2)
        manifest_repo3 = _create_manifest(repo3)

        _create_tags(repo1, manifest_repo1.manifest, 5)
        _create_tags(repo1, manifest_repo1.manifest, 5, start_time_before="7d")
        _create_tags(repo2, manifest_repo2.manifest, 5, start_time_before="7d")
        _create_tags(repo3, manifest_repo3.manifest, 10)

        _assert_repo_tag_count(repo1, 10)
        _assert_repo_tag_count(repo2, 5)
        _assert_repo_tag_count(repo3, 10)

        worker = AutoPruneWorker()
        worker.prune()

        _assert_repo_tag_count(repo1, 5, assert_start_after="7d")
        _assert_repo_tag_count(repo2, 0, assert_start_after="7d")
        _assert_repo_tag_count(repo3, 10, assert_start_after="7d")

        task = model.autoprune.fetch_autoprune_task_by_namespace_id(new_policy.namespace_id)
        assert task.status == "success"


def test_delete_autoprune_task_if_no_policy_exists(initialized_db):
    org = model.organization.get_organization("sellnsmall")
    model.autoprune.create_autoprune_task(org.id)

    worker = AutoPruneWorker()
    worker.prune()

    assert not model.autoprune.namespace_has_autoprune_task(org.id)
    assert not model.autoprune.namespace_has_autoprune_policy(org.id)


def test_fetch_tasks_in_correct_order(initialized_db):
    # Start with an empty table
    for task in AutoPruneTaskStatus.select():
        model.autoprune.delete_autoprune_task(task)

    sellnsmall = model.organization.get_organization("sellnsmall")
    buynlarge = model.organization.get_organization("buynlarge")
    library = model.organization.get_organization("library")
    devtable = model.user.get_user("devtable")
    freshuser = model.user.get_user("freshuser")
    randomuser = model.user.get_user("randomuser")

    queue = WorkQueue("testgcnamespace", lambda db: db.transaction())
    model.user.mark_namespace_for_deletion(library, [], queue)
    model.user.mark_namespace_for_deletion(randomuser, [], queue)

    AutoPruneTaskStatus.create(namespace=sellnsmall, status="queued", last_ran_ms=None)
    AutoPruneTaskStatus.create(
        namespace=buynlarge, status="queued", last_ran_ms=_past_timestamp_ms("7d")
    )
    AutoPruneTaskStatus.create(
        namespace=devtable, status="queued", last_ran_ms=_past_timestamp_ms("5w")
    )
    AutoPruneTaskStatus.create(
        namespace=freshuser, status="queued", last_ran_ms=_past_timestamp_ms("2w")
    )
    AutoPruneTaskStatus.create(
        namespace=library, status="queued", last_ran_ms=_past_timestamp_ms("7d")
    )
    AutoPruneTaskStatus.create(namespace=randomuser, status="queued", last_ran_ms=None)

    expected_calls = [buynlarge.id, freshuser.id, devtable.id, sellnsmall.id]
    should_never_be_called = [library.id, randomuser.id]
    with patch(
        "workers.autopruneworker.get_namespace_autoprune_policies_by_id", MagicMock()
    ) as mock_get_policies:

        def assert_mock_get_policies(namespace_id):
            assert namespace_id not in should_never_be_called
            expected_namespace_id = expected_calls.pop()
            assert namespace_id == expected_namespace_id

        mock_get_policies.side_effect = assert_mock_get_policies

        worker = AutoPruneWorker()
        worker.prune()

        assert len(expected_calls) == 0
