import json
import os
import random
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app import storage
from data import model
from data.database import AutoPruneTaskStatus, ImageStorageLocation, Tag
from data.model.oci.manifest import get_or_create_manifest
from data.model.oci.tag import (
    get_tag,
    list_alive_tags,
    list_repository_tag_history,
    retarget_tag,
)
from data.model.user import get_active_namespaces
from data.queue import WorkQueue
from digest.digest_tools import sha256_digest
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *
from util.bytes import Bytes
from util.timedeltastring import convert_to_timedelta
from workers.autopruneworker import AutoPruneWorker


def _populate_blob(content, namespace, repo):
    content = Bytes.for_string_or_unicode(content).as_encoded_str()
    digest = str(sha256_digest(content))
    location = ImageStorageLocation.get(name="local_us")
    blob = model.blob.store_blob_record_and_temp_link(
        namespace, repo.name, digest, location, len(content), 120
    )
    storage.put_content(["local_us"], model.storage.get_layer_path(blob), content)
    return blob, digest


def create_manifest(namespace, repo):
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
    _, config_digest = _populate_blob(layer_json, namespace, repo)

    v2_builder = DockerSchema2ManifestBuilder()
    v2_builder.set_config_digest(config_digest, len(layer_json.encode("utf-8")))
    v2_manifest = v2_builder.build()

    return get_or_create_manifest(repo, v2_manifest, storage)


def create_tag(repo, manifest, start=None, name=None):
    name = "tag-%s" % str(uuid.uuid4()) if name is None else name
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
        create_tag(repo, manifest, start_time)


def _assert_repo_tag_count(repo, count, assert_start_after=None):
    tags, _ = list_repository_tag_history(repo, 1, 100, active_tags_only=True)
    assert len(tags) == count
    if assert_start_after is not None:
        for tag in tags:
            assert tag.lifetime_start_ms > _past_timestamp_ms(assert_start_after)


def _past_timestamp_ms(time_delta):
    return int(time.time() * 1000) - convert_to_timedelta(time_delta).total_seconds() * 1000


# Tests for namespace autoprune policy
def test_namespace_prune_multiple_repos_by_tag_count(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

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
    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)
    manifest_repo3 = create_manifest("sellnsmall", repo3)

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


def test_namespace_prune_multiple_repos_by_creation_date(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

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
    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)
    manifest_repo3 = create_manifest("sellnsmall", repo3)

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


def test_delete_autoprune_task_if_no_namespace_policy_exists(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    org = model.organization.get_organization("sellnsmall")
    model.autoprune.create_autoprune_task(org.id)

    worker = AutoPruneWorker()
    worker.prune()

    assert not model.autoprune.namespace_has_autoprune_task(org.id)
    assert not model.autoprune.namespace_has_autoprune_policy(org.id)


def test_fetch_tasks_in_correct_order(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

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


# Tests for repository autoprune policy
def test_repository_prune_multiple_repos_by_tag_count(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )
    repo2 = model.repository.create_repository(
        "buynlarge", "repo2", None, repo_kind="image", visibility="public"
    )

    new_repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "number_of_tags", "value": 5}, create_task=True
    )
    new_repo2_policy = model.autoprune.create_repository_autoprune_policy(
        "buynlarge", "repo2", {"method": "number_of_tags", "value": 4}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("buynlarge", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 10)
    _create_tags(repo2, manifest_repo2.manifest, 3)

    _assert_repo_tag_count(repo1, 10)
    _assert_repo_tag_count(repo2, 3)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 3)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo1_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo2_policy.namespace_id)
    assert task2.status == "success"


def test_repository_prune_multiple_repos_by_creation_date(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )
    repo2 = model.repository.create_repository(
        "buynlarge", "repo2", None, repo_kind="image", visibility="public"
    )
    repo3 = model.repository.create_repository(
        "library", "repo3", None, repo_kind="image", visibility="public"
    )

    new_repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "creation_date", "value": "1w"}, create_task=True
    )
    new_repo2_policy = model.autoprune.create_repository_autoprune_policy(
        "buynlarge", "repo2", {"method": "creation_date", "value": "5d"}, create_task=True
    )
    new_repo3_policy = model.autoprune.create_repository_autoprune_policy(
        "library", "repo3", {"method": "creation_date", "value": "24h"}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("buynlarge", repo2)
    manifest_repo3 = create_manifest("library", repo3)

    _create_tags(repo1, manifest_repo1.manifest, 5)
    _create_tags(repo1, manifest_repo1.manifest, 5, start_time_before="7d")
    _create_tags(repo2, manifest_repo2.manifest, 3, start_time_before="3d")
    _create_tags(repo2, manifest_repo2.manifest, 5, start_time_before="5d")
    _create_tags(repo3, manifest_repo3.manifest, 10)
    _create_tags(repo3, manifest_repo3.manifest, 5, start_time_before="24h")

    _assert_repo_tag_count(repo1, 10)
    _assert_repo_tag_count(repo2, 8)
    _assert_repo_tag_count(repo3, 15)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 5, assert_start_after="7d")
    _assert_repo_tag_count(repo2, 3, assert_start_after="5d")
    _assert_repo_tag_count(repo3, 10, assert_start_after="24h")

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo1_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo2_policy.namespace_id)
    assert task2.status == "success"

    task3 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo3_policy.namespace_id)
    assert task3.status == "success"


def test_delete_autoprune_task_if_no_repository_policy_exists(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    org = model.organization.get_organization("sellnsmall")
    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )
    model.autoprune.create_autoprune_task(org.id)

    worker = AutoPruneWorker()
    worker.prune()

    assert not model.autoprune.namespace_has_autoprune_task(org.id)
    assert not model.autoprune.repository_has_autoprune_policy(repo1.id)


def test_nspolicy_tagcount_less_than_repopolicy_tagcount(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "number_of_tags", "value": 2}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "number_of_tags", "value": 4}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 5)
    _create_tags(repo2, manifest_repo2.manifest, 8)

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 8)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 2)
    _assert_repo_tag_count(repo2, 2)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy.namespace_id)
    assert task2.status == "success"


def test_repopolicy_tagcount_less_than_nspolicy_tagcount(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "number_of_tags", "value": 4}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )
    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "number_of_tags", "value": 2}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 5)
    _create_tags(repo2, manifest_repo2.manifest, 8)

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 8)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 2)
    _assert_repo_tag_count(repo2, 4)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo_policy.namespace_id)
    assert task2.status == "success"


def test_nspolicy_timespan_older_than_repopolicy_timespan(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "creation_date", "value": "5d"}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "creation_date", "value": "2d"}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 3)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="5d")
    _create_tags(repo1, manifest_repo1.manifest, 3, start_time_before="2d")
    _create_tags(repo1, manifest_repo1.manifest, 4, start_time_before="1d")
    _create_tags(repo2, manifest_repo2.manifest, 3)
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="5d")
    _create_tags(repo2, manifest_repo2.manifest, 3, start_time_before="2d")
    _create_tags(repo2, manifest_repo2.manifest, 4, start_time_before="1d")

    _assert_repo_tag_count(repo1, 12)
    _assert_repo_tag_count(repo2, 12)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 7)
    _assert_repo_tag_count(repo2, 10)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy.namespace_id)
    assert task2.status == "success"


def test_repopolicy_timespan_older_than_nspolicy_timespan(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "creation_date", "value": "2d"}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "creation_date", "value": "5d"}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 3)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="5d")
    _create_tags(repo1, manifest_repo1.manifest, 3, start_time_before="2d")
    _create_tags(repo1, manifest_repo1.manifest, 4, start_time_before="1d")
    _create_tags(repo2, manifest_repo2.manifest, 3)
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="5d")
    _create_tags(repo2, manifest_repo2.manifest, 3, start_time_before="2d")
    _create_tags(repo2, manifest_repo2.manifest, 4, start_time_before="1d")

    _assert_repo_tag_count(repo1, 12)
    _assert_repo_tag_count(repo2, 12)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 7)
    _assert_repo_tag_count(repo2, 7)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy.namespace_id)
    assert task2.status == "success"


def test_nspolicy_tagcount_repopolicy_creation_date_reconcile(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "number_of_tags", "value": 6}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "creation_date", "value": "3d"}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 1)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="3d")
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="1d")
    _create_tags(repo2, manifest_repo2.manifest, 3)
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="3d")
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="1d")

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 7)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 3)
    _assert_repo_tag_count(repo2, 6)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy.namespace_id)
    assert task2.status == "success"


def test_nspolicy_creation_date_repopolicy_tagcount_reconcile(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "creation_date", "value": "3d"}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo2", None, repo_kind="image", visibility="public"
    )

    repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "number_of_tags", "value": 6}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 2)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="3d")
    _create_tags(repo1, manifest_repo1.manifest, 3, start_time_before="1d")
    _create_tags(repo2, manifest_repo2.manifest, 3)
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="3d")
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="1d")

    _assert_repo_tag_count(repo1, 7)
    _assert_repo_tag_count(repo2, 7)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 5)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy.namespace_id)
    assert task2.status == "success"


def test_registry_prune(initialized_db):
    namespaces = [namespace.username for namespace in get_active_namespaces()]
    assert len(namespaces) > 5  # 5 is arbitrary, just need more than 2
    mock_config = {
        "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY": {"method": "number_of_tags", "value": 10},
        "DEFAULT_POLICY_FETCH_NAMESPACES_LIMIT": 2,
    }
    with patch("workers.autopruneworker.app.config", mock_config):
        with patch(
            "workers.autopruneworker.execute_namespace_policies", MagicMock()
        ) as mock_execute_namespace_policies:

            def assert_mock_execute_namespace_policies(
                policies, namespace, repo_page_limit, tag_page_limit, include_repo_policies
            ):
                assert len(policies) == 1
                assert policies[0].config == mock_config["DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"]
                assert include_repo_policies is False
                assert namespace.username in namespaces
                namespaces.remove(namespace.username)

            mock_execute_namespace_policies.side_effect = assert_mock_execute_namespace_policies
            worker = AutoPruneWorker()
            worker.prune_registry(skip_lock_for_testing=True)
            assert len(namespaces) == 0


def test_registry_prune_no_default_policy(initialized_db):
    worker = AutoPruneWorker()
    assert len(worker._operations) == 1


def test_registry_prune_invalid_policy(initialized_db):
    mock_config = {
        "DEFAULT_NAMESPACE_AUTOPRUNE_POLICY": {"method": "doesnotexist", "value": "doesnotexist"}
    }
    with patch("workers.autopruneworker.app.config", mock_config):
        errored = False
        try:
            worker = AutoPruneWorker()
            worker.prune_registry(skip_lock_for_testing=True)
        except model.InvalidNamespaceAutoPrunePolicy as ex:
            errored = True
        assert errored


@pytest.mark.parametrize(
    "tags, expected, matches",
    [
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test1", "test2", "test3", "test4", "test5"],
            True,
        ),
        (
            ["match1", "match2", "test1", "test2", "test3", "test4"],
            ["match1", "match2", "test1", "test2", "test3", "test4"],
            True,
        ),
        (
            ["match1", "match2", "match3", "test1", "test2", "test3", "test4"],
            ["match1", "match2", "match3", "test1", "test2", "test3", "test4"],
            True,
        ),
        (
            ["match1", "match2", "match3", "match4", "test1", "test2", "test3", "test4"],
            ["match1", "match2", "match3", "test1", "test2", "test3", "test4"],
            True,
        ),
        (
            [
                "match1",
                "match2",
                "test1",
                "test2",
                "test3",
                "test4",
                "match3",
                "match4",
            ],
            ["match1", "match2", "test1", "test2", "test3", "test4", "match3"],
            True,
        ),
        (
            ["match1", "match2", "match3", "test1", "test2", "test3", "test4", "match4", "match5"],
            ["match1", "match2", "match3", "test1", "test2", "test3", "test4"],
            True,
        ),
        (
            [
                "match1",
                "test1",
                "match2",
                "test2",
                "match3",
                "test3",
                "match4",
                "test4",
                "match5",
                "test5",
            ],
            ["match1", "test1", "match2", "test2", "match3", "test3", "test4", "test5"],
            True,
        ),
        (
            [
                "match1",
                "test1",
                "match2",
                "test2",
                "match3",
                "test3",
                "match4",
                "test4",
                "match5",
                "test5",
                "match6",
                "match7",
                "match8",
            ],
            ["match1", "test1", "match2", "test2", "match3", "test3", "test4", "test5"],
            True,
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test1", "test2", "test3"],
            False,
        ),
        (
            ["test1", "match1", "test2", "match2", "test3", "match3", "test4", "test5", "match4"],
            ["test1", "match1", "test2", "match2", "test3", "match3", "match4"],
            False,
        ),
        (
            ["match1", "match2", "match3", "match4", "match5", "test1", "test2", "test3", "test4"],
            ["match1", "match2", "match3", "match4", "match5", "test1", "test2", "test3"],
            False,
        ),
        (
            ["match1", "match2", "test1", "test2", "test3"],
            ["match1", "match2", "test1", "test2", "test3"],
            False,
        ),
        (
            ["match1", "match2", "match3", "test1", "test2"],
            ["match1", "match2", "match3", "test1", "test2"],
            False,
        ),
        (
            ["match1", "match2", "match3", "match4", "test1"],
            ["match1", "match2", "match3", "match4", "test1"],
            False,
        ),
        (
            ["match1", "match2", "match3", "match4", "match5"],
            ["match1", "match2", "match3", "match4", "match5"],
            False,
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test1", "test2", "test3"],
            False,
        ),
        (
            [
                "match1",
                "test1",
                "match2",
                "test2",
                "match3",
                "test3",
                "match4",
                "test4",
                "match5",
                "test5",
            ],
            ["match1", "test1", "match2", "test2", "match3", "test3", "match4", "match5"],
            False,
        ),
    ],
)
def test_prune_by_tag_count_with_tag_filter(tags, expected, matches, initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    new_repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall",
        "repo1",
        {
            "method": "number_of_tags",
            "value": 3,
            "tag_pattern": "match.*",
            "tag_pattern_matches": matches,
        },
        create_task=True,
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    now_ms = int(time.time() * 1000)
    for i, tag in enumerate(tags):
        creation_time = now_ms - i
        create_tag(repo1, manifest_repo1.manifest, start=creation_time, name=tag)

    _assert_repo_tag_count(repo1, len(tags))

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, len(expected))

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo1_policy.namespace_id)
    assert task1.status == "success"
    for tag in list_alive_tags(repo1):
        assert tag.name in expected
        expected.remove(tag.name)

    assert len(expected) == 0


@pytest.mark.parametrize(
    "tags, expected, matches",
    [
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test1", "test2", "test3", "test4", "test5"],
            True,
        ),
        (["match1", "match2", "test1", "test2", "test3"], ["test1", "test2", "test3"], True),
        (["match1", "match2", "match3", "test1", "test2"], ["test1", "test2"], True),
        (["match1", "match2", "match3", "match4", "test1"], ["match4", "test1"], True),
        (["match1", "match2", "match3", "match4", "match5"], ["match4", "match5"], True),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test4", "test5"],
            False,
        ),
        (["match1", "test1", "test2", "test3", "test4"], ["match1", "test3", "test4"], False),
        (
            ["match1", "match2", "test1", "test2", "test3"],
            ["match1", "match2", "test2", "test3"],
            False,
        ),
        (
            ["match1", "match2", "match3", "test1", "test2"],
            ["match1", "match2", "match3", "test1", "test2"],
            False,
        ),
        (
            ["match1", "match2", "match3", "match4", "test1"],
            ["match1", "match2", "match3", "match4", "test1"],
            False,
        ),
        (
            ["match1", "match2", "match3", "match4", "match5"],
            ["match1", "match2", "match3", "match4", "match5"],
            False,
        ),
    ],
)
def test_prune_by_creation_date_with_tag_filter(tags, expected, matches, initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    new_repo1_policy = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall",
        "repo1",
        {
            "method": "creation_date",
            "value": "5d",
            "tag_pattern": "match.*",
            "tag_pattern_matches": matches,
        },
        create_task=True,
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    for i, tag in enumerate(tags):
        # Set the first 3 tags to be old enough to be pruned
        # We do the -1 to ensure that the creation time is less than the current time
        creation_time = _past_timestamp_ms("5d") - 1 if i < 3 else None
        create_tag(repo1, manifest_repo1.manifest, start=creation_time, name=tag)

    _assert_repo_tag_count(repo1, 5)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, len(expected))

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(new_repo1_policy.namespace_id)
    assert task1.status == "success"
    for tag in list_alive_tags(repo1):
        assert tag.name in expected
        expected.remove(tag.name)

    assert len(expected) == 0


def test_multiple_policies_for_namespace(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    ns_policy1 = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall",
        {
            "method": "creation_date",
            "value": "3d",
            "tag_pattern": ".*",
            "tag_pattern_matches": True,
        },
        create_task=True,
    )

    ns_policy2 = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "number_of_tags", "value": 5}, create_task=True
    )

    ns_policy3 = model.autoprune.create_namespace_autoprune_policy(
        "sellnsmall", {"method": "creation_date", "value": "2d"}, create_task=True
    )

    repo1 = model.repository.create_repository(
        "sellnsmall", "latest", None, repo_kind="image", visibility="public"
    )

    repo2 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    manifest_repo2 = create_manifest("sellnsmall", repo2)

    _create_tags(repo1, manifest_repo1.manifest, 2)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="4d")
    _create_tags(repo1, manifest_repo1.manifest, 3, start_time_before="1d")
    _create_tags(repo2, manifest_repo2.manifest, 3)
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="4d")
    _create_tags(repo2, manifest_repo2.manifest, 2, start_time_before="1d")

    _assert_repo_tag_count(repo1, 7)
    _assert_repo_tag_count(repo2, 7)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 5)
    _assert_repo_tag_count(repo2, 5)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy1.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy2.namespace_id)
    assert task2.status == "success"

    task3 = model.autoprune.fetch_autoprune_task_by_namespace_id(ns_policy3.namespace_id)
    assert task3.status == "success"


def test_multiple_policies_for_repository(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    repo1_policy1 = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall",
        "repo1",
        {
            "method": "creation_date",
            "value": "3d",
            "tag_pattern": ".*",
            "tag_pattern_matches": True,
        },
        create_task=True,
    )

    repo1_policy2 = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "number_of_tags", "value": 3}, create_task=True
    )

    repo1_policy3 = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall", "repo1", {"method": "creation_date", "value": "2d"}, create_task=True
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)

    _create_tags(repo1, manifest_repo1.manifest, 2)
    _create_tags(repo1, manifest_repo1.manifest, 2, start_time_before="4d")
    _create_tags(repo1, manifest_repo1.manifest, 3, start_time_before="1d")

    _assert_repo_tag_count(repo1, 7)

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, 3)

    task1 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy1.namespace_id)
    assert task1.status == "success"

    task2 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy2.namespace_id)
    assert task2.status == "success"

    task3 = model.autoprune.fetch_autoprune_task_by_namespace_id(repo1_policy3.namespace_id)
    assert task3.status == "success"


@pytest.mark.parametrize(
    "tags, expected, plcy1, plcy2",
    [
        (
            ["test1", "test2", "check1", "test3", "check2"],
            ["test1", "test2", "test3", "check2"],
            ["creation_date", "5m", "^c", True],
            ["number_of_tags", 4, None, None],
        ),
        (
            ["test1", "test2", "check1", "test3", "check2"],
            ["test1", "test2", "test3", "check2"],
            ["number_of_tags", 4, None, None],
            ["creation_date", "5m", "^c", True],
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test4", "test5"],
            ["creation_date", "5m", None, None],
            ["number_of_tags", 4, None, None],
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test4", "test5"],
            ["number_of_tags", 4, None, None],
            ["creation_date", "5m", None, None],
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test4", "test5"],
            ["number_of_tags", 2, None, None],
            ["number_of_tags", 3, None, None],
        ),
        (
            ["test1", "test2", "test3", "test4", "test5"],
            ["test4", "test5"],
            ["number_of_tags", 3, None, None],
            ["number_of_tags", 2, None, None],
        ),
        (
            ["test1", "test2", "check1", "test3", "check2"],
            ["check1", "test3", "check2"],
            ["number_of_tags", 4, None, None],
            ["creation_date", "5m", "^c", False],
        ),
        (
            ["test1", "test2", "check1", "test3", "check2"],
            ["check1", "test3", "check2"],
            ["creation_date", "5m", "^c", False],
            ["number_of_tags", 4, None, None],
        ),
    ],
)
def test_policy_order(tags, expected, plcy1, plcy2, initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        model.autoprune.SKIP_LOCKED = False

    repo1 = model.repository.create_repository(
        "sellnsmall", "repo1", None, repo_kind="image", visibility="public"
    )

    policy1 = model.autoprune.create_repository_autoprune_policy(
        "sellnsmall",
        "repo1",
        {
            "method": plcy1[0],
            "value": plcy1[1],
            "tag_pattern": plcy1[2],
            "tag_pattern_matches": plcy1[3],
        },
        create_task=True,
    )

    model.autoprune.create_repository_autoprune_policy(
        "sellnsmall",
        "repo1",
        {
            "method": plcy2[0],
            "value": plcy2[1],
            "tag_pattern": plcy2[2],
            "tag_pattern_matches": plcy2[3],
        },
    )

    manifest_repo1 = create_manifest("sellnsmall", repo1)
    for i, tag in enumerate(tags):
        # Set the first 3 tags to be old enough to be pruned
        # We do the -1 to ensure that the creation time is less than the current time
        creation_time = _past_timestamp_ms("5m") - 1 if i < 3 else None
        create_tag(repo1, manifest_repo1.manifest, start=creation_time, name=tag)

    _assert_repo_tag_count(repo1, len(tags))

    worker = AutoPruneWorker()
    worker.prune()

    _assert_repo_tag_count(repo1, len(expected))

    task = model.autoprune.fetch_autoprune_task_by_namespace_id(policy1.namespace_id)
    assert task.status == "success"

    for tag in list_alive_tags(repo1):
        assert tag.name in expected
        expected.remove(tag.name)

    assert len(expected) == 0
