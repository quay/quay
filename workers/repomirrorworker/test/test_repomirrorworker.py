import pytest
import mock
import json
from functools import wraps

from app import storage
from data.registry_model.blobuploader import upload_blob, BlobUploadSettings
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from data.registry_model import registry_model
from data.registry_model.datatypes import RepositoryReference
from data.model.test.test_repo_mirroring import create_mirror_repo_robot
from data.model.user import retrieve_robot_token
from data.database import Manifest, RepoMirrorConfig, RepoMirrorStatus

from workers.repomirrorworker import delete_obsolete_tags
from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker
from io import BytesIO
from util.repomirror.skopeomirror import SkopeoResults, SkopeoMirror

from test.fixtures import *


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
                "config": {"author": "Repo Mirror",},
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
                "inspect",
                "--tls-verify=False",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_rollback(run_skopeo_mock, initialized_db, app):
    """
    Tags in the repo:

    "updated" - this tag will be updated during the mirror
    "removed" - this tag will be removed during the mirror
    "created" - this tag will be created during the mirror
    """

    mirror, repo = create_mirror_repo_robot(["updated", "created", "zzerror"])
    _create_tag(repo, "updated")
    _create_tag(repo, "deleted")

    skopeo_calls = [
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:updated",
            ],
            "results": SkopeoResults(
                True, [], '{"RepoTags": ["latest", "updated", "created", "zzerror"]}', ""
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
        try:
            skopeo_call = skopeo_calls.pop(0)
            assert args == skopeo_call["args"]
            assert proxy == {}

            if args[1] == "copy" and args[7].endswith(":updated"):
                _create_tag(repo, "updated")
            elif args[1] == "copy" and args[7].endswith(":created"):
                _create_tag(repo, "created")

            return skopeo_call["results"]
        except Exception as e:
            skopeo_calls.append(skopeo_call)
            raise e

    run_skopeo_mock.side_effect = skopeo_test

    worker = RepoMirrorWorker()
    worker._process_mirrors()

    assert [] == skopeo_calls
    # TODO: how to assert tag.retarget_tag() and tag.delete_tag() called?


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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "--debug",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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
                "inspect",
                "--tls-verify=True",
                "--creds",
                "`rm -rf /`",
                "'docker://& rm -rf /;/namespace/repository:latest'",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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
                "inspect",
                "--tls-verify=True",
                "--creds",
                '`rm -rf /`:""$PATH\\"',
                "'docker://& rm -rf /;/namespace/repository:latest'",
            ],
            "results": SkopeoResults(True, [], '{"RepoTags": ["latest"]}', ""),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "copy",
                "--all",
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

    def skopeo_test(args, proxy):
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

    def skopeo_test(args, proxy):
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:7.1",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest 7.1 in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest latest in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:7.1",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest 7.1 in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest latest in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:7.1",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest 7.1 in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest latest in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
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
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:7.1",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest 7.1 in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
            ),
        },
        {
            "args": [
                "/usr/bin/skopeo",
                "inspect",
                "--tls-verify=True",
                "docker://registry.example.com/namespace/repository:latest",
            ],
            "results": SkopeoResults(
                False,
                [],
                "",
                'time="2019-09-18T13:29:40Z" level=fatal msg="Error reading manifest latest in registry.example.com/namespace/repository: manifest unknown: manifest unknown"',
            ),
        },
    ]
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert 2 == len(skopeo_calls)
    assert 3 == mirror.sync_retries_remaining
