import json
from functools import wraps
from io import BytesIO
from unittest.mock import patch

import mock
import pytest

from app import storage
from data.database import Manifest, RepoMirrorConfig, RepoMirrorStatus
from data.model.test.test_repo_mirroring import create_mirror_repo_robot
from data.model.user import retrieve_robot_token
from data.registry_model import registry_model
from data.registry_model.blobuploader import BlobUploadSettings, upload_blob
from data.registry_model.datatypes import RepositoryReference
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *
from util.repomirror.skopeomirror import SkopeoMirror, SkopeoResults
from workers.repomirrorworker import (
    _get_v2_bearer_token,
    copy_filtered_architectures,
    delete_obsolete_tags,
    process_mirrors,
    push_sparse_manifest_list,
)
from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker


def disable_existing_mirrors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for mirror in RepoMirrorConfig.select():
            mirror.is_enabled = False
            mirror.save()

        func(*args, **kwargs)

        for mirror in RepoMirrorConfig.select():
            mirror.is_enabled = True
            mirror.save()

    return wrapper


def _create_tag(repo, name):
    repo_ref = RepositoryReference.for_repo_obj(repo)

    with upload_blob(repo_ref, storage, BlobUploadSettings(500, 500)) as upload:
        app_config = {"TESTING": True}
        config_json = json.dumps(
            {
                "config": {
                    "author": "Repo Mirror",
                },
                "rootfs": {"type": "layers", "diff_ids": []},
                "history": [
                    {
                        "created": "2019-07-30T18:37:09.284840891Z",
                        "created_by": "base",
                        "author": "Repo Mirror",
                    },
                ],
            }
        )
        upload.upload_chunk(app_config, BytesIO(config_json.encode("utf-8")))
        blob = upload.commit_to_blob(app_config)
        assert blob

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(blob.digest, blob.compressed_size)
    builder.add_layer("sha256:abcd", 1234, urls=["http://hello/world"])
    manifest = builder.build()

    manifest, tag = registry_model.create_manifest_and_retarget_tag(
        repo_ref, manifest, name, storage, raise_on_error=True
    )
    assert tag
    assert tag.name == name


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_successful_mirror(run_skopeo_mock, initialized_db, app):
    """
    Basic test of successful mirror.
    """

    mirror, repo = create_mirror_repo_robot(
        ["latest", "7.1"], external_registry_config={"verify_tls": False}
    )

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_unsigned_images(run_skopeo_mock, initialized_db, app):
    """
    Test whether the insecure-policy option is added when a repository is passed with unsigned_images.
    """

    mirror, repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False, "unsigned_images": True}
    )

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "--insecure-policy",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_successful_disabled_sync_now(run_skopeo_mock, initialized_db, app):
    """
    Disabled mirrors still allow "sync now".
    """

    mirror, repo = create_mirror_repo_robot(["latest", "7.1"])
    mirror.is_enabled = False
    mirror.sync_status = RepoMirrorStatus.SYNC_NOW
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_successful_mirror_verbose_logs(run_skopeo_mock, initialized_db, app, monkeypatch):
    """
    Basic test of successful mirror with verbose logs turned on.
    """

    mirror, repo = create_mirror_repo_robot(["latest", "7.1"])

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "Success", ""),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    monkeypatch.setenv("DEBUGLOG", "true")
    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@pytest.mark.parametrize(
    "rollback_enabled, expected_delete_calls, expected_retarget_tag_calls",
    [
        (True, ["deleted", "zzerror", "updated", "created"], ["updated"]),
        (False, ["deleted", "zzerror"], []),
    ],
)
@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
@mock.patch("workers.repomirrorworker.retarget_tag")
@mock.patch("workers.repomirrorworker.delete_tag")
@mock.patch("workers.repomirrorworker.app")
def test_rollback(
    mock_app,
    delete_tag_mock,
    retarget_tag_mock,
    run_skopeo_mock,
    expected_retarget_tag_calls,
    expected_delete_calls,
    rollback_enabled,
    initialized_db,
    app,
):
    """
    Tags in the repo:

    "updated" - this tag will be updated during the mirror
    "removed" - this tag will be removed during the mirror
    "created" - this tag will be created during the mirror
    """
    mock_app.config = {
        "REPO_MIRROR_ROLLBACK": rollback_enabled,
        "REPO_MIRROR": True,
        "REPO_MIRROR_SERVER_HOSTNAME": "localhost:5000",
        "TESTING": True,
    }

    mirror, repo = create_mirror_repo_robot(["updated", "created", "zzerror"])
    _create_tag(repo, "updated")
    _create_tag(repo, "deleted")

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(
                True, [], '{"Tags": ["latest", "zzerror", "created", "updated"]}', ""
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:created",
                "docker://localhost:5000/mirror/repo:created",
            ],
            "results": SkopeoResults(True, [], "Success", ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:updated",
                "docker://localhost:5000/mirror/repo:updated",
            ],
            "results": SkopeoResults(True, [], "Success", ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:zzerror",
                "docker://localhost:5000/mirror/repo:zzerror",
            ],
            "results": SkopeoResults(False, [], "", "ERROR"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            if args[1] == "copy" and args[8].endswith(":updated"):
                _create_tag(repo, "updated")
            elif args[1] == "copy" and args[8].endswith(":created"):
                _create_tag(repo, "created")
            elif args[1] == "copy" and args[8].endswith(":zzerror"):
                _create_tag(repo, "zzerror")

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    def retarget_tag_test(name, manifest, is_reversion=False):
        assert expected_retarget_tag_calls.pop(0) == name
        assert is_reversion

    def delete_tag_test(repository_id, tag_name):
        assert expected_delete_calls.pop(0) == tag_name

    run_skopeo_mock.side_effect = skopeo_test
    retarget_tag_mock.side_effect = retarget_tag_test
    delete_tag_mock.side_effect = delete_tag_test
    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls
    assert [] == expected_retarget_tag_calls
    assert [] == expected_delete_calls


def test_remove_obsolete_tags(initialized_db):
    """
    As part of the mirror, the set of tags on the remote repository is compared to the local
    existing tags.

    Those not present on the remote are removed locally.
    """

    mirror, repository = create_mirror_repo_robot(["updated", "created"], repo_name="removed")

    _create_tag(repository, "oldtag")

    incoming_tags = ["one", "two"]
    deleted_tags = delete_obsolete_tags(mirror, incoming_tags)

    assert [tag.name for tag in deleted_tags] == ["oldtag"]


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_config_server_hostname(run_skopeo_mock, initialized_db, app, monkeypatch):
    """
    Set REPO_MIRROR_SERVER_HOSTNAME to override SERVER_HOSTNAME config.
    """

    mirror, repo = create_mirror_repo_robot(["latest", "7.1"])

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://config_server_hostname/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "Success", ""),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    monkeypatch.setenv("DEBUGLOG", "true")
    with patch.dict(
        "data.model.config.app_config", {"REPO_MIRROR_SERVER_HOSTNAME": "config_server_hostname"}
    ):
        worker = RepoMirrorWorker()
        worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_quote_params(run_skopeo_mock, initialized_db, app):
    """
    Basic test of successful mirror.
    """

    mirror, repo = create_mirror_repo_robot(["latest", "7.1"])
    mirror.external_reference = "& rm -rf /;/namespace/repository"
    mirror.external_registry_username = "`rm -rf /`"
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "--creds",
                "`rm -rf /`",
                "docker://& rm -rf /;/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "--src-creds",
                "`rm -rf /`",
                "'docker://& rm -rf /;/namespace/repository:latest'",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_quote_params_password(run_skopeo_mock, initialized_db, app):
    """
    Basic test of successful mirror.
    """

    mirror, repo = create_mirror_repo_robot(["latest", "7.1"])
    mirror.external_reference = "& rm -rf /;/namespace/repository"
    mirror.external_registry_username = "`rm -rf /`"
    mirror.external_registry_password = '""$PATH\\"'
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "--creds",
                '`rm -rf /`:""$PATH\\"',
                "docker://& rm -rf /;/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=True",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "--src-creds",
                '`rm -rf /`:""$PATH\\"',
                "'docker://& rm -rf /;/namespace/repository:latest'",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_inspect_error_mirror(run_skopeo_mock, initialized_db, app):
    """
    Test for no tag for skopeo inspect.

    The mirror is processed four times, asserting that the remaining syncs decrement until next sync
    is bumped to the future, confirming the fourth is never processed.
    """

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test
    worker = RepoMirrorWorker()

    mirror, repo = create_mirror_repo_robot(["7.1"])

    # Call number 1
    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error listing repository tags: fetching tags list: invalid status code from registry 404 (Not Found)"',
            ),
        },
    ]
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert [] == skopeo_calls
    assert 2 == mirror.sync_retries_remaining

    # Call number 2
    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error listing repository tags: fetching tags list: invalid status code from registry 404 (Not Found)"',
            ),
        },
    ]
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert [] == skopeo_calls
    assert 1 == mirror.sync_retries_remaining

    # Call number 3
    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error listing repository tags: fetching tags list: invalid status code from registry 404 (Not Found)"',
            ),
        },
    ]
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert [] == skopeo_calls
    assert 3 == mirror.sync_retries_remaining

    # Call number 4
    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error listing repository tags: fetching tags list: invalid status code from registry 404 (Not Found)"',
            ),
        },
    ]
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert 1 == len(skopeo_calls)
    assert 3 == mirror.sync_retries_remaining


# Sample manifest list for architecture filtering tests
SAMPLE_MANIFEST_LIST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "manifests": [
            {
                "digest": "sha256:amd64digest",
                "size": 1234,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            {
                "digest": "sha256:arm64digest",
                "size": 1234,
                "platform": {"architecture": "arm64", "os": "linux"},
            },
            {
                "digest": "sha256:ppc64ledigest",
                "size": 1234,
                "platform": {"architecture": "ppc64le", "os": "linux"},
            },
        ],
    }
)


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.push_sparse_manifest_list")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_with_architecture_filter(run_skopeo_mock, push_manifest_mock, initialized_db, app):
    """
    Test that architecture filtering copies only specified architectures.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    mirror.architecture_filter = ["amd64", "arm64"]
    mirror.save()

    push_manifest_mock.return_value = True

    skopeo_calls = [
        # list-tags call
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        # inspect --raw call for manifest list
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--raw",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], SAMPLE_MANIFEST_LIST, ""),
        },
        # copy by digest for amd64
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--preserve-digests",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository@sha256:amd64digest",
                "docker://localhost:5000/mirror/repo@sha256:amd64digest",
            ],
            "results": SkopeoResults(True, [], "copied amd64", ""),
        },
        # copy by digest for arm64
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--preserve-digests",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository@sha256:arm64digest",
                "docker://localhost:5000/mirror/repo@sha256:arm64digest",
            ],
            "results": SkopeoResults(True, [], "copied arm64", ""),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls
    push_manifest_mock.assert_called_once()


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_without_architecture_filter_uses_all(run_skopeo_mock, initialized_db, app):
    """
    Test that without architecture filter, the standard --all copy is used.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    # Ensure no architecture filter is set
    mirror.architecture_filter = []
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


SAMPLE_SINGLE_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {"mediaType": "application/vnd.docker.container.image.v1+json"},
        "layers": [],
    }
)


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_single_arch_image_with_filter(run_skopeo_mock, initialized_db, app):
    """
    Test that single-arch images fall back to standard copy when architecture filter is set.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    mirror.architecture_filter = ["amd64"]
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        # inspect --raw returns single manifest (not manifest list)
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--raw",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], SAMPLE_SINGLE_MANIFEST, ""),
        },
        # Falls back to standard copy with --all
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "copied", ""),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_mirror_no_matching_architectures(run_skopeo_mock, initialized_db, app):
    """
    Test that mirroring fails gracefully when no architectures match.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    # Request an architecture that doesn't exist in the manifest list
    mirror.architecture_filter = ["s390x"]
    mirror.save()

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--raw",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], SAMPLE_MANIFEST_LIST, ""),
        },
    ]

    def skopeo_test(args, proxy, timeout=300):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    # All expected calls should have been made
    assert [] == skopeo_calls
    # Mirror should fail due to no matching architectures
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.FAIL


# =============================================================================
# Tests for _get_v2_bearer_token()
# =============================================================================


class MockResponse:
    """Mock response object for requests."""

    def __init__(self, status_code, headers=None, json_data=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self._json_data = json_data
        self.text = text

    def json(self):
        return self._json_data


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_success(mock_get, initialized_db, app):
    """
    Test successful token acquisition with WWW-Authenticate header parsing.
    """
    # First call to v2 endpoint returns 401 with WWW-Authenticate header
    challenge_response = MockResponse(
        401,
        headers={
            "WWW-Authenticate": 'Bearer realm="https://auth.example.com/token",service="registry.example.com",scope="repository:namespace/repo:pull"'
        },
    )

    # Second call to token endpoint returns the token
    token_response = MockResponse(
        200,
        json_data={"token": "test-bearer-token-12345"},
    )

    mock_get.side_effect = [challenge_response, token_response]

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token == "test-bearer-token-12345"
    assert mock_get.call_count == 2

    # Verify first call was to v2 endpoint
    first_call = mock_get.call_args_list[0]
    assert first_call[0][0] == "https://registry.example.com/v2/"

    # Verify second call was to token endpoint with correct auth
    second_call = mock_get.call_args_list[1]
    assert "https://auth.example.com/token" in second_call[0][0]
    assert second_call[1]["auth"] == ("testuser", "testpass")


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_access_token_key(mock_get, initialized_db, app):
    """
    Test token acquisition when response uses access_token key instead of token.
    """
    challenge_response = MockResponse(
        401,
        headers={
            "WWW-Authenticate": 'Bearer realm="https://auth.example.com/token",service="registry.example.com"'
        },
    )

    # Some registries return "access_token" instead of "token"
    token_response = MockResponse(
        200,
        json_data={"access_token": "access-token-67890"},
    )

    mock_get.side_effect = [challenge_response, token_response]

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token == "access-token-67890"


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_no_auth_required(mock_get, initialized_db, app):
    """
    Test that None is returned when v2 endpoint returns 200 (no auth required).
    """
    # V2 endpoint returns 200 - no authentication required
    mock_get.return_value = MockResponse(200)

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None
    assert mock_get.call_count == 1


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_no_www_auth_header(mock_get, initialized_db, app):
    """
    Test that None is returned when no WWW-Authenticate header is present.
    """
    # 401 response but no WWW-Authenticate header
    mock_get.return_value = MockResponse(401, headers={})

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_invalid_realm(mock_get, initialized_db, app):
    """
    Test that None is returned when realm cannot be parsed from header.
    """
    # WWW-Authenticate header without realm
    mock_get.return_value = MockResponse(
        401,
        headers={"WWW-Authenticate": 'Bearer service="registry.example.com"'},
    )

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_request_exception(mock_get, initialized_db, app):
    """
    Test that None is returned when a request exception occurs.
    """
    import requests

    mock_get.side_effect = requests.RequestException("Connection failed")

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_token_request_fails(mock_get, initialized_db, app):
    """
    Test that None is returned when token request fails with non-200 status.
    """
    challenge_response = MockResponse(
        401,
        headers={
            "WWW-Authenticate": 'Bearer realm="https://auth.example.com/token",service="registry.example.com"'
        },
    )

    # Token request fails
    token_response = MockResponse(401, text="Unauthorized")

    mock_get.side_effect = [challenge_response, token_response]

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_json_decode_error(mock_get, initialized_db, app):
    """
    Test that None is returned when token response is not valid JSON.
    """
    challenge_response = MockResponse(
        401,
        headers={
            "WWW-Authenticate": 'Bearer realm="https://auth.example.com/token",service="registry.example.com"'
        },
    )

    # Token request returns 200 but with non-JSON body
    import json

    token_response = MockResponse(200, text="<html>Not JSON</html>")
    token_response.json = mock.Mock(
        side_effect=json.JSONDecodeError("Expecting value", "<html>Not JSON</html>", 0)
    )

    mock_get.side_effect = [challenge_response, token_response]

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token is None


@mock.patch("workers.repomirrorworker.requests.get")
def test_get_v2_bearer_token_realm_with_existing_query_params(mock_get, initialized_db, app):
    """
    Test that existing query params in realm URL are preserved.
    """
    challenge_response = MockResponse(
        401,
        headers={
            "WWW-Authenticate": 'Bearer realm="https://auth.example.com/token?foo=bar",service="registry.example.com"'
        },
    )

    token_response = MockResponse(200)
    token_response.json = mock.Mock(return_value={"token": "test-token"})

    mock_get.side_effect = [challenge_response, token_response]

    token = _get_v2_bearer_token(
        server="registry.example.com",
        scheme="https",
        namespace="namespace",
        repo_name="repo",
        username="testuser",
        password="testpass",
        verify_tls=True,
    )

    assert token == "test-token"
    # Verify the token URL was called with proper query params
    token_call = mock_get.call_args_list[1]
    token_url = token_call[0][0]
    assert "foo=bar" in token_url or "foo" in token_url
    assert "scope=" in token_url
    assert "service=" in token_url


# =============================================================================
# Tests for push_sparse_manifest_list() with bearer token logic
# =============================================================================


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_with_bearer_token(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test that bearer token is used when token exchange succeeds.
    """
    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = "bearer-token-456"
    mock_put.return_value = MockResponse(201)

    manifest_bytes = b'{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.docker.distribution.manifest.list.v2+json"

    result = push_sparse_manifest_list(mirror, "latest", manifest_bytes, media_type)

    assert result is True
    mock_put.assert_called_once()

    # Verify bearer token was used (Authorization header, no auth tuple)
    call_kwargs = mock_put.call_args[1]
    assert call_kwargs["headers"]["Authorization"] == "Bearer bearer-token-456"
    assert call_kwargs["auth"] is None


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_fallback_to_basic_auth(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test fallback to basic auth when token exchange returns None.
    """
    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = None  # Token exchange failed
    mock_put.return_value = MockResponse(200)

    manifest_bytes = '{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.oci.image.index.v1+json"

    result = push_sparse_manifest_list(mirror, "v1.0", manifest_bytes, media_type)

    assert result is True
    mock_put.assert_called_once()

    # Verify basic auth was used (auth tuple, no Authorization header)
    call_kwargs = mock_put.call_args[1]
    assert "Authorization" not in call_kwargs["headers"]
    assert call_kwargs["auth"] == (mirror.internal_robot.username, "robot-token-123")


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_put_fails(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test that False is returned when PUT request fails.
    """
    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = "bearer-token-456"
    mock_put.return_value = MockResponse(500, text="Internal Server Error")

    manifest_bytes = b'{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.docker.distribution.manifest.list.v2+json"

    result = push_sparse_manifest_list(mirror, "latest", manifest_bytes, media_type)

    assert result is False


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_request_exception(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test that False is returned when a request exception occurs.
    """
    import requests

    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = "bearer-token-456"
    mock_put.side_effect = requests.RequestException("Connection failed")

    manifest_bytes = b'{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.docker.distribution.manifest.list.v2+json"

    result = push_sparse_manifest_list(mirror, "latest", manifest_bytes, media_type)

    assert result is False


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_uses_config_scheme(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test that the URL scheme comes from app config.
    """
    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = "bearer-token-456"
    mock_put.return_value = MockResponse(201)

    manifest_bytes = b'{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.docker.distribution.manifest.list.v2+json"

    with patch.dict(app.config, {"PREFERRED_URL_SCHEME": "http"}):
        result = push_sparse_manifest_list(mirror, "latest", manifest_bytes, media_type)

    assert result is True

    # Verify URL uses configured scheme
    call_args = mock_put.call_args[0]
    assert call_args[0].startswith("http://")


@mock.patch("workers.repomirrorworker.retrieve_robot_token")
@mock.patch("workers.repomirrorworker._get_v2_bearer_token")
@mock.patch("workers.repomirrorworker.requests.put")
def test_push_sparse_manifest_list_string_manifest(
    mock_put, mock_get_token, mock_retrieve_robot_token, initialized_db, app
):
    """
    Test that string manifest bytes are properly encoded to UTF-8.
    """
    mirror, repo = create_mirror_repo_robot(["latest"])

    mock_retrieve_robot_token.return_value = "robot-token-123"
    mock_get_token.return_value = "bearer-token-456"
    mock_put.return_value = MockResponse(201)

    # Pass manifest as string instead of bytes
    manifest_str = '{"schemaVersion": 2, "manifests": []}'
    media_type = "application/vnd.docker.distribution.manifest.list.v2+json"

    result = push_sparse_manifest_list(mirror, "latest", manifest_str, media_type)

    assert result is True

    # Verify data was encoded to bytes
    call_kwargs = mock_put.call_args[1]
    assert isinstance(call_kwargs["data"], bytes)
    assert call_kwargs["data"] == manifest_str.encode("utf-8")


# =============================================================================
# Tests for process_mirrors() edge cases
# =============================================================================


@mock.patch("workers.repomirrorworker.features")
def test_process_mirrors_feature_disabled(mock_features, _initialized_db, _app):
    """
    When REPO_MIRROR feature is disabled, process_mirrors returns None immediately.
    """
    mock_features.REPO_MIRROR = False

    result = process_mirrors(mock.Mock())
    assert result is None


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.perform_mirror")
@mock.patch("workers.repomirrorworker.model")
@mock.patch("workers.repomirrorworker.features")
def test_process_mirrors_preempted_exception(
    mock_features, mock_model, mock_perform, _initialized_db, _app
):
    """
    When perform_mirror raises PreemptedException, the abort signal is set and iteration continues.
    """
    from workers.repomirrorworker import PreemptedException

    mock_features.REPO_MIRROR = True
    mock_abt = mock.Mock()
    mock_mirror = mock.Mock()
    mock_model.repositories_to_mirror.return_value = (
        iter([(mock_mirror, mock_abt, 5)]),
        "next_token",
    )
    mock_perform.side_effect = PreemptedException()

    result = process_mirrors(mock.Mock())

    mock_abt.set.assert_called_once()
    assert result == "next_token"


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.perform_mirror")
@mock.patch("workers.repomirrorworker.model")
@mock.patch("workers.repomirrorworker.features")
def test_process_mirrors_generic_exception(
    mock_features, mock_model, mock_perform, _initialized_db, _app
):
    """
    When perform_mirror raises a generic Exception, process_mirrors returns None.
    """
    mock_features.REPO_MIRROR = True
    mock_abt = mock.Mock()
    mock_mirror = mock.Mock()
    mock_model.repositories_to_mirror.return_value = (
        iter([(mock_mirror, mock_abt, 5)]),
        "next_token",
    )
    mock_perform.side_effect = RuntimeError("unexpected error")

    result = process_mirrors(mock.Mock())

    assert result is None


# =============================================================================
# Tests for copy_filtered_architectures() edge cases
# =============================================================================


@disable_existing_mirrors
def test_copy_filtered_architectures_inspect_failure(_initialized_db, _app):
    """
    When skopeo inspect_raw fails, copy_filtered_architectures returns failure result.
    """
    mirror, _repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )

    mock_skopeo = mock.Mock()
    mock_skopeo.inspect_raw.return_value = SkopeoResults(False, [], "", "inspect failed")

    result = copy_filtered_architectures(mock_skopeo, mirror, "latest", ["amd64"])

    assert result.success is False
    assert "inspect failed" in result.stderr


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.retrieve_robot_token")
def test_copy_filtered_architectures_arch_copy_failure(mock_token, _initialized_db, _app):
    """
    When copying an architecture by digest fails, copy_filtered_architectures returns failure.
    """
    mirror, _repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    mock_token.return_value = "robot_token"

    mock_skopeo = mock.Mock()
    mock_skopeo.inspect_raw.return_value = SkopeoResults(True, [], SAMPLE_MANIFEST_LIST, "")
    mock_skopeo.copy_by_digest.return_value = SkopeoResults(False, [], "", "digest copy failed")

    result = copy_filtered_architectures(mock_skopeo, mirror, "latest", ["amd64"])

    assert result.success is False
    assert "digest copy failed" in result.stderr


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.push_sparse_manifest_list")
@mock.patch("workers.repomirrorworker.retrieve_robot_token")
def test_copy_filtered_architectures_manifest_push_failure(
    mock_token, mock_push, _initialized_db, _app
):
    """
    When pushing the sparse manifest list fails, copy_filtered_architectures returns failure.
    """
    mirror, _repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )
    mock_token.return_value = "robot_token"
    mock_push.return_value = False

    mock_skopeo = mock.Mock()
    mock_skopeo.inspect_raw.return_value = SkopeoResults(True, [], SAMPLE_MANIFEST_LIST, "")
    mock_skopeo.copy_by_digest.return_value = SkopeoResults(True, [], "copied", "")

    result = copy_filtered_architectures(mock_skopeo, mirror, "latest", ["amd64"])

    assert result.success is False
    assert "sparse manifest" in result.stderr.lower()


# =============================================================================
# Tests for perform_mirror() edge cases
# =============================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_perform_mirror_empty_tags(run_skopeo_mock, _initialized_db, _app):
    """
    When tags_to_mirror returns an empty list (no tags match pattern),
    mirror succeeds with no sync.
    """
    mirror, _repo = create_mirror_repo_robot(["nonexistent-pattern*"])

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest", "v1.0"]}', ""),
        },
    ]

    def skopeo_test(args, _proxy, timeout=300):
        skopeo_call = skopeo_calls.pop(0)
        assert args == skopeo_call["args"]
        return skopeo_call["results"]

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
@mock.patch("workers.repomirrorworker.check_repo_mirror_sync_status")
def test_perform_mirror_cancel_during_sync(
    mock_check_status, run_skopeo_mock, _initialized_db, _app
):
    """
    When cancel is detected during tag sync, mirror is cancelled.
    """
    mirror, _repo = create_mirror_repo_robot(
        ["latest"], external_registry_config={"verify_tls": False}
    )

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "list-tags",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository",
            ],
            "results": SkopeoResults(True, [], '{"Tags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
                "--remove-signatures",
                "--src-tls-verify=False",
                "--dest-tls-verify=True",
                "--dest-creds",
                "%s:%s"
                % (mirror.internal_robot.username, retrieve_robot_token(mirror.internal_robot)),
                "docker://registry.example.com/namespace/repository:latest",
                "docker://localhost:5000/mirror/repo:latest",
            ],
            "results": SkopeoResults(True, [], "stdout", "stderr"),
        },
    ]

    def skopeo_test(args, _proxy, timeout=300):
        skopeo_call = skopeo_calls.pop(0)
        assert args == skopeo_call["args"]
        return skopeo_call["results"]

    run_skopeo_mock.side_effect = skopeo_test
    mock_check_status.return_value = RepoMirrorStatus.CANCEL

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.CANCEL
