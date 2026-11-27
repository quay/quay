"""Exercise actual OCI digest pushes and deletion, including referrer caching."""

import gzip
import io
import json
import tarfile
from unittest.mock import patch

import pytest
from flask import url_for

from app import app as realapp
from app import instance_keys, storage
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.cache.impl import InMemoryDataModelCache
from data.cache.test.test_cache import TEST_CACHE_CONFIG
from data.database import ImageStorageLocation, Tag
from data.model.blob import store_blob_record_and_temp_link
from data.model.oci.tag import filter_to_alive_tags
from data.model.repository import create_repository
from data.model.storage import get_layer_path
from data.registry_model import registry_model
from digest.digest_tools import sha256_digest
from endpoints.test.shared import add_csrf_param, conduct_call, toggle_feature
from image.oci.index import OCIIndexBuilder
from image.oci.manifest import OCIManifest, OCIManifestBuilder
from test.fixtures import *  # noqa: F401, F403
from util.bytes import Bytes
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token


@pytest.mark.parametrize("prime_cache", [False, True], ids=["cold", "primed"])
@pytest.mark.parametrize(
    "artifact_type", [None, "application/vnd.quay.test.referrer"], ids=["unfiltered", "filtered"]
)
@pytest.mark.parametrize("retained_by_index", [False, True], ids=["deleted", "live-child"])
def test_real_referrer_digest_deletion(client, app, prime_cache, artifact_type, retained_by_index):
    """Listings match GET visibility, including children retained by a live index."""
    create_repository("devtable", "aclifecycle", None)
    repository_name = "devtable/aclifecycle"
    user = model.user.get_user("devtable")
    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"],
        subject,
        context,
        [{"type": "repository", "name": repository_name, "actions": ["pull", "push"]}],
        600,
        instance_keys,
    )
    headers = {"Authorization": "Bearer " + token}
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w"):
        pass
    uncompressed_layer = tar_bytes.getvalue()
    layer = gzip.compress(uncompressed_layer, mtime=0)
    layer_digest = str(sha256_digest(layer))
    config = json.dumps(
        {
            "os": "linux",
            "architecture": "amd64",
            "rootfs": {"type": "layers", "diff_ids": [str(sha256_digest(uncompressed_layer))]},
            "history": [],
        }
    ).encode()
    digest = str(sha256_digest(config))
    location = ImageStorageLocation.get(name="local_us")
    for blob_digest, content in ((digest, config), (layer_digest, layer)):
        blob = store_blob_record_and_temp_link(
            "devtable", "aclifecycle", blob_digest, location, len(content), 120
        )
        storage.put_content(["local_us"], get_layer_path(blob), content)

    def build(subject_manifest=None, control=False):
        builder = OCIManifestBuilder()
        builder.set_config_digest(digest, len(config))
        builder.add_layer(layer_digest, len(layer))
        if subject_manifest is not None:
            builder.set_subject(
                subject_manifest.digest,
                len(subject_manifest.bytes.as_encoded_str()),
                subject_manifest.media_type,
            )
        if control:
            builder.add_annotation("quay.test.control", "retained")
        manifest = builder.build()
        if subject_manifest is not None and artifact_type is not None:
            payload = dict(manifest.manifest_dict)
            payload["artifactType"] = artifact_type
            manifest = OCIManifest(Bytes.for_string_or_unicode(json.dumps(payload)))
        return manifest

    def push(manifest):
        params = add_csrf_param(
            client, {"repository": repository_name, "manifest_ref": manifest.digest}
        )
        response = client.put(
            url_for("v2.write_manifest_by_digest", **params),
            data=manifest.bytes.as_encoded_str(),
            headers=headers,
            content_type=manifest.media_type,
        )
        assert response.status_code == 201, response.data

    def call(endpoint, method, digest, expected_code=200):
        params = {"repository": repository_name, "manifest_ref": digest}
        if endpoint == "v2.list_manifest_referrers" and artifact_type is not None:
            params["artifactType"] = artifact_type
        return conduct_call(
            client,
            endpoint,
            url_for,
            method,
            params,
            expected_code=expected_code,
            headers=dict(headers),
        )

    cache = InMemoryDataModelCache(TEST_CACHE_CONFIG)
    with (
        toggle_feature("REFERRERS_API", True),
        patch("endpoints.v2.manifest.model_cache", cache),
        patch("endpoints.v2.referrers.model_cache", cache),
    ):
        subject_manifest = build()
        referrer = build(subject_manifest)
        sibling = build(subject_manifest, control=True)
        push(subject_manifest)
        push(referrer)
        push(sibling)
        if retained_by_index:
            builder = OCIIndexBuilder()
            builder.add_manifest(referrer)
            retaining_index = builder.build()
            push(retaining_index)
        repository = registry_model.lookup_repository("devtable", "aclifecycle")
        stored = registry_model.lookup_manifest_by_digest(
            repository, referrer.digest, allow_hidden=True
        )
        assert stored is not None
        tags = list(
            filter_to_alive_tags(
                Tag.select().where(Tag.manifest == stored._db_id), allow_hidden=True
            )
        )
        assert tags and all(tag.hidden for tag in tags)
        call("v2.fetch_manifest_by_digest", "GET", referrer.digest)
        if prime_cache:
            response = call("v2.list_manifest_referrers", "GET", subject_manifest.digest)
            assert referrer.digest in {m["digest"] for m in json.loads(response.data)["manifests"]}

        call("v2.delete_manifest_by_digest", "DELETE", referrer.digest, 202)
        call(
            "v2.fetch_manifest_by_digest", "GET", referrer.digest, 200 if retained_by_index else 404
        )
        call("v2.fetch_manifest_by_digest", "GET", sibling.digest)
        call("v2.fetch_manifest_by_digest", "GET", subject_manifest.digest)
        response = call("v2.list_manifest_referrers", "GET", subject_manifest.digest)
        listed = {m["digest"] for m in json.loads(response.data)["manifests"]}
        uncached = {
            manifest.digest
            for manifest in registry_model.lookup_referrers_for_manifest(
                repository,
                registry_model.lookup_manifest_by_digest(
                    repository, subject_manifest.digest, allow_hidden=True
                ),
                artifact_type,
            )
        }
        print(
            "REFERRER_DIAGNOSTIC="
            + json.dumps(
                {
                    "prime_cache": prime_cache,
                    "listed_after_delete": referrer.digest in listed,
                    "uncached_after_delete": referrer.digest in uncached,
                }
            ),
            flush=True,
        )
        assert (referrer.digest in listed) == retained_by_index
        assert (referrer.digest in uncached) == retained_by_index
        assert sibling.digest in listed
        assert sibling.digest in uncached
        if retained_by_index:
            # The preceding list call cached the child while its index was alive.
            call("v2.delete_manifest_by_digest", "DELETE", retaining_index.digest, 202)
            assert (
                registry_model.lookup_manifest_by_digest(
                    repository, referrer.digest, allow_hidden=True
                )
                is None
            ), "deleted referrer remains reachable without cache"
            call("v2.fetch_manifest_by_digest", "GET", referrer.digest, 404)
            response = call("v2.list_manifest_referrers", "GET", subject_manifest.digest)
            remaining = {m["digest"] for m in json.loads(response.data)["manifests"]}
            assert referrer.digest not in remaining, "deleted index leaves a cached child referrer"
            assert sibling.digest in remaining
