import unittest
import json

import pytest

from app import model_cache
from data.database import ProxyCacheConfig, User
from proxy import Proxy


@pytest.mark.e2e
class TestProxyE2E(unittest.TestCase):
    media_type = "application/vnd.docker.distribution.manifest.v2+json"
    registry = "docker.io"
    repo = "library/postgres"
    tag = 14
    tag_404 = 666
    digest_404 = "sha256:3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d"
    digest = None  # set by setup
    proxy = None  # set by setup
    org = None  # set by setup

    @pytest.fixture(autouse=True)
    def setup(self):
        config = ProxyCacheConfig(
            upstream_registry=self.registry,
            organization=User(username="cache-org", organization=True),
        )
        if self.proxy is None:
            self.proxy = Proxy(config, self.repo)

        if self.digest is None:
            resp = self.proxy.get_manifest(
                image_ref=self.tag,
                media_type=self.media_type,
            )
            self.assertEqual(resp["status"], 200)
            manifest = json.loads(resp["response"])
            self.digest = manifest["layers"][0]["digest"]

    def _lowercase_headers(self, headers: dict) -> dict:
        return {key.lower(): value for key, value in headers.items()}

    def test_manifest_exists(self):
        resp = self.proxy.manifest_exists(image_ref=self.tag)
        self.assertEqual(resp["status"], 200)
        self.assertEqual(resp["response"], "")
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)
        self.assertIn("docker-content-digest", headers)

    def test_manifest_exists_404(self):
        resp = self.proxy.manifest_exists(image_ref=self.tag_404)
        self.assertEqual(resp["status"], 404)
        self.assertEqual(resp["response"], "")
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)
        self.assertNotIn("docker-content-digest", headers)

    def test_get_manifest(self):
        resp = self.proxy.get_manifest(
            image_ref=self.tag,
            media_type=self.media_type,
        )
        self.assertEqual(resp["status"], 200)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)
        self.assertIn("docker-content-digest", headers)
        resp_len = headers["content-length"]
        self.assertEqual(str(len(resp["response"])), resp_len)

    def test_get_manifest_404(self):
        resp = self.proxy.get_manifest(
            image_ref=self.tag_404,
            media_type=self.media_type,
        )
        self.assertEqual(resp["status"], 404)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)
        self.assertNotIn("docker-content-digest", headers)

    def test_get_manifest_renews_expired_token(self):
        if not hasattr(model_cache, "empty_for_testing"):
            # don't continue testing if we can't empty the cache as it will certainly fail.
            return

        # by clearing the cache and proxy session we force the proxy to
        # re-authenticate against the upstream registry.
        model_cache.empty_for_testing()
        self.proxy._session.headers.pop("Authorization")

        resp = self.proxy.get_manifest(
            image_ref=self.tag,
            media_type=self.media_type,
        )
        self.assertEqual(resp["status"], 200)

    def test_blob_exists(self):
        resp = self.proxy.blob_exists(digest=self.digest)
        self.assertEqual(resp["status"], 200)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)

    def test_blob_exists_404(self):
        resp = self.proxy.blob_exists(digest=self.digest_404)
        self.assertEqual(resp["status"], 404)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)

    def test_get_blob(self):
        resp = self.proxy.get_blob(self.digest, self.media_type)
        self.assertEqual(resp["status"], 200)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)

    def test_get_blob_404(self):
        resp = self.proxy.get_blob(self.digest_404, self.media_type)
        self.assertEqual(resp["status"], 404)
        headers = self._lowercase_headers(resp["headers"])
        self.assertIn("content-length", headers)
