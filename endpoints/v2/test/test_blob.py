import hashlib
import json
import unittest
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from playhouse.test_utils import assert_query_count

from app import app as realapp
from app import instance_keys, storage
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.cache import InMemoryDataModelCache, NoopDataModelCache
from data.cache.test.test_cache import TEST_CACHE_CONFIG
from data.database import ImageStorage, ImageStorageLocation, ImageStoragePlacement
from data.model.storage import get_layer_path
from data.registry_model import registry_model
from data.registry_model.registry_proxy_model import ProxyModel
from digest.digest_tools import sha256_digest
from endpoints.test.shared import conduct_call
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from proxy.fixtures import *  # noqa: F401, F403
from test.fixtures import *
from util.bytes import Bytes
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token

HELLO_WORLD_DIGEST = "sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4"
HELLO_WORLD_SCHEMA2_MANIFEST_JSON = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 1469,
      "digest": "sha256:feb5d9fea6a5e9606aa995e879d862b825965ba48de054caab5ef356dc6b3412"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 2479,
         "digest": "sha256:2db29710123e3e53a794f2694094b9b4338aa9ee5c40b930cb8063a1be392c54"
      }
   ]
}"""


class TestBlobPullThroughStorage:
    orgname = "cache"
    registry = "docker.io"
    image_name = "library/hello-world"
    repository = f"{orgname}/{image_name}"
    tag = "14"
    # digest for 'test'. matches the one used in proxy/fixtures.py
    digest = "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    config = None
    org = None
    manifest = None
    repo_ref = None
    blob = None

    @pytest.fixture(autouse=True)
    def setup(self, client, app, proxy_manifest_response):
        self.client = client

        self.user = model.user.get_user("devtable")
        context, subject = build_context_and_subject(ValidatedAuthContext(user=self.user))
        access = [
            {
                "type": "repository",
                "name": self.repository,
                "actions": ["pull"],
            }
        ]
        token = generate_bearer_token(
            realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
        )
        self.headers = {
            "Authorization": f"Bearer {token}",
        }

        if self.org is None:
            self.org = model.organization.create_organization(
                self.orgname, "{self.orgname}@devtable.com", self.user
            )
            self.org.save()
            self.config = model.proxy_cache.create_proxy_cache_config(
                org_name=self.orgname,
                upstream_registry=self.registry,
                expiration_s=3600,
            )

        if self.repo_ref is None:
            r = model.repository.create_repository(self.orgname, self.image_name, self.user)
            assert r is not None
            self.repo_ref = registry_model.lookup_repository(self.orgname, self.image_name)
            assert self.repo_ref is not None

        def get_blob(layer):
            content = Bytes.for_string_or_unicode(layer).as_encoded_str()
            digest = str(sha256_digest(content))
            blob = model.blob.store_blob_record_and_temp_link(
                self.orgname,
                self.image_name,
                digest,
                ImageStorageLocation.get(name="local_us"),
                len(content),
                120,
            )
            storage.put_content(["local_us"], get_layer_path(blob), content)
            return blob, digest

        if self.manifest is None:
            layer1 = json.dumps(
                {
                    "config": {},
                    "rootfs": {"type": "layers", "diff_ids": []},
                    "history": [{}],
                }
            )
            _, config_digest = get_blob(layer1)
            layer2 = "test"
            _, blob_digest = get_blob(layer2)
            builder = DockerSchema2ManifestBuilder()
            builder.set_config_digest(config_digest, len(layer1.encode("utf-8")))
            builder.add_layer(blob_digest, len(layer2.encode("utf-8")))
            manifest = builder.build()
            created_manifest = model.oci.manifest.get_or_create_manifest(
                self.repo_ref.id, manifest, storage
            )
            self.manifest = created_manifest.manifest
            assert self.digest == blob_digest
            assert self.manifest is not None

        if self.blob is None:
            self.blob = ImageStorage.filter(ImageStorage.content_checksum == self.digest).get()

    def test_create_blob_placement_on_first_time_download(self, proxy_manifest_response):
        proxy_mock = proxy_manifest_response(
            self.tag, HELLO_WORLD_SCHEMA2_MANIFEST_JSON, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        params = {
            "repository": self.repository,
            "digest": self.digest,
        }

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            with patch("endpoints.v2.blob.model_cache", NoopDataModelCache(TEST_CACHE_CONFIG)):
                conduct_call(
                    self.client,
                    "v2.download_blob",
                    url_for,
                    "GET",
                    params,
                    expected_code=200,
                    headers=self.headers,
                )
        placements = ImageStoragePlacement.filter(ImageStoragePlacement.storage == self.blob)
        assert placements.count() == 1

    def test_store_blob_on_first_time_download(self, proxy_manifest_response):
        proxy_mock = proxy_manifest_response(
            self.tag, HELLO_WORLD_SCHEMA2_MANIFEST_JSON, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        params = {
            "repository": self.repository,
            "digest": self.digest,
        }

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            with patch("endpoints.v2.blob.model_cache", NoopDataModelCache(TEST_CACHE_CONFIG)):
                conduct_call(
                    self.client,
                    "v2.download_blob",
                    url_for,
                    "GET",
                    params,
                    expected_code=200,
                    headers=self.headers,
                )

        path = get_layer_path(self.blob)
        assert path is not None

        placements = ImageStoragePlacement.filter(ImageStoragePlacement.storage == self.blob)
        locations = [placements.get().location.name]
        assert storage.exists(locations, path), f"blob not found in storage at path {path}"


@pytest.mark.e2e
class TestBlobPullThroughProxy(unittest.TestCase):
    org = "cache"
    registry = "docker.io"
    image_name = "library/postgres"
    repository = f"{org}/{image_name}"
    manifest_digest = "sha256:3039f467c7f92ee93a68dc88237495624c27921927b147d8b4e914f885c89d9f"
    config = None
    blob_digest = None
    repo_ref = None

    @pytest.fixture(autouse=True)
    def setup(self, client, app):
        self.client = client

        self.user = model.user.get_user("devtable")
        context, subject = build_context_and_subject(ValidatedAuthContext(user=self.user))
        access = [
            {
                "type": "repository",
                "name": self.repository,
                "actions": ["pull"],
            }
        ]
        token = generate_bearer_token(
            realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
        )
        self.headers = {
            "Authorization": f"Bearer {token}",
        }

        try:
            model.organization.get(self.org)
        except Exception:
            org = model.organization.create_organization(self.org, "cache@devtable.com", self.user)
            org.save()

        if self.config is None:
            self.config = model.proxy_cache.create_proxy_cache_config(
                org_name=self.org,
                upstream_registry=self.registry,
                expiration_s=3600,
            )

        if self.repo_ref is None:
            r = model.repository.create_repository(self.org, self.image_name, self.user)
            assert r is not None
            self.repo_ref = registry_model.lookup_repository(self.org, self.image_name)
            assert self.repo_ref is not None

        if self.blob_digest is None:
            proxy_model = ProxyModel(self.org, self.image_name, self.user)
            manifest = proxy_model.lookup_manifest_by_digest(self.repo_ref, self.manifest_digest)
            self.blob_digest = manifest.get_parsed_manifest().blob_digests[0]

    def test_pull_from_dockerhub(self):
        params = {
            "repository": self.repository,
            "digest": self.blob_digest,
        }
        conduct_call(
            self.client,
            "v2.download_blob",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=self.headers,
        )

    def test_pull_from_dockerhub_404(self):
        digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
        params = {
            "repository": self.repository,
            "digest": digest,
        }
        conduct_call(
            self.client,
            "v2.download_blob",
            url_for,
            "GET",
            params,
            expected_code=404,
            headers=self.headers,
        )

    def test_check_blob_exists_from_dockerhub(self):
        params = {
            "repository": self.repository,
            "digest": self.blob_digest,
        }
        conduct_call(
            self.client,
            "v2.check_blob_exists",
            url_for,
            "HEAD",
            params,
            expected_code=200,
            headers=self.headers,
        )

    def test_check_blob_exists_from_dockerhub_404(self):
        digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
        params = {
            "repository": self.repository,
            "digest": digest,
        }
        conduct_call(
            self.client,
            "v2.check_blob_exists",
            url_for,
            "HEAD",
            params,
            expected_code=404,
            headers=self.headers,
        )


@pytest.mark.parametrize(
    "method, endpoint, expected_count",
    [
        ("GET", "download_blob", 1),
        ("HEAD", "check_blob_exists", 0),
    ],
)
@patch("endpoints.v2.blob.model_cache", InMemoryDataModelCache(TEST_CACHE_CONFIG))
def test_blob_caching(method, endpoint, expected_count, client, app):
    digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
    location = ImageStorageLocation.get(name="local_us")
    model.blob.store_blob_record_and_temp_link("devtable", "simple", digest, location, 1, 10000000)

    params = {
        "repository": "devtable/simple",
        "digest": digest,
    }

    user = model.user.get_user("devtable")

    access = [
        {
            "type": "repository",
            "name": "devtable/simple",
            "actions": ["pull"],
        }
    ]

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token,
    }

    # Run without caching to make sure the request works. This also preloads some of
    # our global model caches.
    conduct_call(
        client, "v2." + endpoint, url_for, method, params, expected_code=200, headers=headers
    )
    # First request should make a DB query to retrieve the blob.
    conduct_call(
        client, "v2." + endpoint, url_for, method, params, expected_code=200, headers=headers
    )

    # turn off pull-thru proxy cache. it adds an extra query to the pull operation
    # for checking whether the namespace is a cache org or not before retrieving
    # the blob.
    with patch("endpoints.decorators.features.PROXY_CACHE", False):
        # Subsequent requests should use the cached blob.
        # one query for the get_authenticated_user()
        with assert_query_count(expected_count):
            conduct_call(
                client,
                "v2." + endpoint,
                url_for,
                method,
                params,
                expected_code=200,
                headers=headers,
            )


@pytest.mark.parametrize(
    "mount_digest, source_repo, username, include_from_param, expected_code",
    [
        # Unknown blob.
        ("sha256:unknown", "devtable/simple", "devtable", True, 202),
        ("sha256:unknown", "devtable/simple", "devtable", False, 202),
        # Blob not in repo.
        ("sha256:" + hashlib.sha256(b"a").hexdigest(), "devtable/complex", "devtable", True, 202),
        ("sha256:" + hashlib.sha256(b"a").hexdigest(), "devtable/complex", "devtable", False, 202),
        # # Blob in repo.
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "devtable", True, 201),
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "devtable", False, 202),
        # # No access to repo.
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "public", True, 202),
        ("sha256:" + hashlib.sha256(b"b").hexdigest(), "devtable/complex", "public", False, 202),
        # # Public repo.
        ("sha256:" + hashlib.sha256(b"c").hexdigest(), "public/publicrepo", "devtable", True, 201),
        ("sha256:" + hashlib.sha256(b"c").hexdigest(), "public/publicrepo", "devtable", False, 202),
    ],
)
def test_blob_mounting(
    mount_digest, source_repo, username, include_from_param, expected_code, client, app
):
    location = ImageStorageLocation.get(name="local_us")

    # Store and link some blobs.
    digest = "sha256:" + hashlib.sha256(b"a").hexdigest()
    model.blob.store_blob_record_and_temp_link("devtable", "simple", digest, location, 1, 10000000)

    digest = "sha256:" + hashlib.sha256(b"b").hexdigest()
    model.blob.store_blob_record_and_temp_link("devtable", "complex", digest, location, 1, 10000000)

    digest = "sha256:" + hashlib.sha256(b"c").hexdigest()
    model.blob.store_blob_record_and_temp_link(
        "public", "publicrepo", digest, location, 1, 10000000
    )

    params = {
        "repository": "devtable/building",
        "mount": mount_digest,
    }
    if include_from_param:
        params["from"] = source_repo

    user = model.user.get_user(username)
    access = [
        {
            "type": "repository",
            "name": "devtable/building",
            "actions": ["pull", "push"],
        }
    ]

    if source_repo.find(username) == 0:
        access.append(
            {
                "type": "repository",
                "name": source_repo,
                "actions": ["pull"],
            }
        )

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token,
    }

    conduct_call(
        client,
        "v2.start_blob_upload",
        url_for,
        "POST",
        params,
        expected_code=expected_code,
        headers=headers,
    )

    repository = model.repository.get_repository("devtable", "building")

    if expected_code == 201:
        # Ensure the blob now exists under the repo.
        assert model.oci.blob.get_repository_blob_by_digest(repository, mount_digest)
    else:
        assert model.oci.blob.get_repository_blob_by_digest(repository, mount_digest) is None


def test_blob_upload_offset(client, app):
    user = model.user.get_user("devtable")
    access = [
        {
            "type": "repository",
            "name": "devtable/simple",
            "actions": ["pull", "push"],
        }
    ]

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token,
    }

    # Create a blob upload request.
    params = {
        "repository": "devtable/simple",
    }
    response = conduct_call(
        client, "v2.start_blob_upload", url_for, "POST", params, expected_code=202, headers=headers
    )

    upload_uuid = response.headers["Docker-Upload-UUID"]

    # Attempt to start an upload past index zero.
    params = {
        "repository": "devtable/simple",
        "upload_uuid": upload_uuid,
    }

    headers = {
        "Authorization": "Bearer %s" % token,
        "Content-Range": "13-50",
    }

    conduct_call(
        client,
        "v2.upload_chunk",
        url_for,
        "PATCH",
        params,
        expected_code=416,
        headers=headers,
        body="something",
    )


def test_blob_upload_when_pushes_disabled(client, app):
    user = model.user.get_user("devtable")
    access = [
        {
            "type": "repository",
            "name": "devtable/simple",
            "actions": ["pull", "push"],
        }
    ]

    context, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"], subject, context, access, 600, instance_keys
    )

    headers = {
        "Authorization": "Bearer %s" % token,
    }

    # Create a blob upload request.
    params = {
        "repository": "devtable/simple",
    }

    # Disable pushes before conducting the call
    realapp.config["DISABLE_PUSHES"] = True
    conduct_call(
        client,
        "v2.start_blob_upload",
        url_for,
        "POST",
        params,
        expected_code=405,
        headers=headers,
    )

    # re-enable pushes, since the setting persists across all tests
    realapp.config["DISABLE_PUSHES"] = False
