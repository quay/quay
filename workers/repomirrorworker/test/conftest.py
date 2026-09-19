"""Shared fixtures and helpers for repomirrorworker tests."""

import json
import logging
from functools import wraps
from io import BytesIO
from unittest.mock import patch

import pytest

logger = logging.getLogger(__name__)

SKOPEO_BIN = "/usr/bin/skopeo"


@pytest.fixture(autouse=True)
def _mock_dns_for_ssrf_validation():
    """Keep mirror worker tests independent of external DNS."""
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns


def disable_existing_mirrors(func):
    """Decorator that disables all existing mirrors before the test and restores after."""
    from data.database import RepoMirrorConfig

    @wraps(func)
    def wrapper(*args, **kwargs):
        original_states = {m.id: m.is_enabled for m in RepoMirrorConfig.select()}
        for mirror in RepoMirrorConfig.select():
            mirror.is_enabled = False
            mirror.save()

        try:
            func(*args, **kwargs)
        finally:
            for mirror in RepoMirrorConfig.select():
                mirror.is_enabled = original_states.get(mirror.id, mirror.is_enabled)
                mirror.save()

    return wrapper


def create_tag(repo, name):
    """Create a real tag+manifest in the database to simulate a skopeo push landing."""
    from app import storage
    from data.registry_model import registry_model
    from data.registry_model.blobuploader import BlobUploadSettings, upload_blob
    from data.registry_model.datatypes import RepositoryReference
    from image.docker.schema2.manifest import DockerSchema2ManifestBuilder

    repo_ref = RepositoryReference.for_repo_obj(repo)

    with upload_blob(repo_ref, storage, BlobUploadSettings(500, 500)) as upload:
        app_config = {"TESTING": True}
        config_json = json.dumps(
            {
                "config": {"author": "Repo Mirror"},
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
        if not blob:
            raise RuntimeError(f"Failed to commit config blob for tag '{name}'")

    builder = DockerSchema2ManifestBuilder()
    builder.set_config_digest(blob.digest, blob.compressed_size)
    builder.add_layer("sha256:abcd", 1234, urls=["http://hello/world"])
    manifest = builder.build()

    manifest, tag = registry_model.create_manifest_and_retarget_tag(
        repo_ref, manifest, name, storage, raise_on_error=True
    )
    if not tag:
        raise RuntimeError(f"Failed to create tag '{name}' in repo '{repo.name}'")
    if tag.name != name:
        raise RuntimeError(f"Tag name mismatch: expected '{name}', got '{tag.name}'")
    return tag


def assert_skopeo_args(actual_args, expected_args):
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


def make_skopeo_side_effect(skopeo_calls, repo=None, create_tags_on_copy=False):
    """
    Build a side-effect function that pops expected skopeo call entries.

    When *create_tags_on_copy* is True and *repo* is provided, the side-effect
    will call create_tag() for every successful ``copy`` call, simulating a
    real skopeo push landing in Quay's storage.
    """

    def side_effect(args, proxy, timeout=300):
        skopeo_call = skopeo_calls.pop(0)
        assert_skopeo_args(args, skopeo_call["args"])

        result = skopeo_call["results"]

        if create_tags_on_copy and repo and "copy" in args and result.success:
            dest = args[-1].strip("'")
            tag_name = dest.rsplit(":", 1)[-1]
            create_tag(repo, tag_name)

        return result

    return side_effect


def alive_tag_names(repo):
    """Return sorted list of alive tag names for the given repository."""
    from data.model.oci.tag import lookup_alive_tags_shallow

    tags, _ = lookup_alive_tags_shallow(repo.id)
    return sorted(t.name for t in tags)


def run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=None, create_tags_on_copy=False):
    """Wire up skopeo side-effect, run the mirror worker, and assert all calls were consumed."""
    from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker

    run_skopeo_mock.side_effect = make_skopeo_side_effect(
        skopeo_calls, repo=repo, create_tags_on_copy=create_tags_on_copy
    )
    worker = RepoMirrorWorker()
    worker._process_mirrors()
    assert skopeo_calls == [], f"Unconsumed skopeo calls: {skopeo_calls}"
