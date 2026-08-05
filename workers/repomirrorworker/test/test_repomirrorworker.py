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
from workers.repomirrorworker import delete_obsolete_tags, perform_mirror
from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker


@pytest.fixture(autouse=True)
def _mock_dns_for_ssrf_validation():
    """Keep repository mirror worker tests independent of external DNS."""
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns


def _assert_skopeo_args(actual_args, expected_args):
    """Assert skopeo args match, stripping transient authfile and legacy inline --*-creds pairs."""
    auth_flags = (
        "--authfile",
        "--src-authfile",
        "--dest-authfile",
        "--src-creds",
        "--dest-creds",
        "--creds",
    )

    def strip_cred_flags(args):
        a = list(args)
        for flag in auth_flags:
            while flag in a:
                i = a.index(flag)
                del a[i : i + 2]
        return a

    assert strip_cred_flags(actual_args) == strip_cred_flags(expected_args)

    is_copy = "copy" in actual_args
    if is_copy:
        assert "--src-authfile" in actual_args, "copy commands must use --src-authfile"
        assert "--dest-authfile" in actual_args, "copy commands must use --dest-authfile"
        assert "--authfile" not in actual_args, "copy commands must not use shared --authfile"
    else:
        assert "--authfile" in actual_args, "non-copy commands must use --authfile"

    for legacy in ("--src-creds", "--dest-creds", "--creds"):
        assert legacy not in actual_args


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
def test_blocked_mirror_source_never_invokes_skopeo(run_skopeo_mock, initialized_db, app):
    """Persisted legacy configurations are revalidated before network access."""
    mirror, _ = create_mirror_repo_robot(["latest"], repo_name="blocked_source")
    mirror.external_reference = "169.254.169.254/latest/meta-data"
    mirror.save()

    result = perform_mirror(SkopeoMirror(), mirror)

    assert result == RepoMirrorStatus.FAIL
    run_skopeo_mock.assert_not_called()
    updated = RepoMirrorConfig.get_by_id(mirror.id)
    assert updated.sync_status == RepoMirrorStatus.FAIL
    assert updated.sync_expiration_date is None


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_worker_reresolves_source_before_skopeo(
    run_skopeo_mock, initialized_db, app, _mock_dns_for_ssrf_validation
):
    mirror, _ = create_mirror_repo_robot(["latest"], repo_name="dns_revalidation")
    _mock_dns_for_ssrf_validation.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]

    result = perform_mirror(SkopeoMirror(), mirror)

    assert result == RepoMirrorStatus.FAIL
    run_skopeo_mock.assert_not_called()
    updated = RepoMirrorConfig.get_by_id(mirror.id)
    assert updated.sync_status == RepoMirrorStatus.FAIL
    assert updated.sync_expiration_date is None


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_allowlisted_private_mirror_source_invokes_skopeo(run_skopeo_mock, initialized_db, app):
    """The worker honors SSRF_ALLOWED_HOSTS for private enterprise registries."""
    mirror, _ = create_mirror_repo_robot(["latest"], repo_name="allowed_source")
    mirror.external_reference = "10.0.0.1/team/repository"
    mirror.save()
    run_skopeo_mock.return_value = SkopeoResults(True, [], '{"Tags": []}', "")

    from workers.repomirrorworker import app as worker_app

    with patch.dict(worker_app.config, {"SSRF_ALLOWED_HOSTS": ["10.0.0.0/8"]}):
        result = perform_mirror(SkopeoMirror(), mirror)

    assert result is None
    run_skopeo_mock.assert_called_once()
    updated = RepoMirrorConfig.get_by_id(mirror.id)
    assert updated.sync_status == RepoMirrorStatus.SUCCESS


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
    mirror.external_reference = "registry.example.com/namespace/repository;rm-rf"
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
                "docker://registry.example.com/namespace/repository;rm-rf",
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
                "'docker://registry.example.com/namespace/repository;rm-rf:latest'",
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
    mirror.external_reference = "registry.example.com/namespace/repository;rm-rf"
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
                "docker://registry.example.com/namespace/repository;rm-rf",
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
                "'docker://registry.example.com/namespace/repository;rm-rf:latest'",
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
