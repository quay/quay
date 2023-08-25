import json
import unittest

import pytest

from app import model_cache
from data.database import ProxyCacheConfig, User
from proxy import Proxy, UpstreamRegistryError


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
            raw_manifest, content_type = self.proxy.get_manifest(
                image_ref=self.tag,
            )
            manifest = json.loads(raw_manifest)
            self.digest = manifest["fsLayers"][0]["blobSum"]

    def test_manifest_exists(self):
        digest = self.proxy.manifest_exists(image_ref=self.tag)
        self.assertIsNotNone(digest)

    def test_manifest_exists_404(self):
        with pytest.raises(UpstreamRegistryError):
            self.proxy.manifest_exists(image_ref=self.tag_404)

    def test_get_manifest(self):
        try:
            self.proxy.get_manifest(image_ref=self.tag)
        except Exception as e:
            assert False, f"unexpected exception {e}"

    def test_get_manifest_404(self):
        with pytest.raises(UpstreamRegistryError):
            self.proxy.get_manifest(image_ref=self.tag_404)

    def test_get_manifest_renews_expired_token(self):
        if not hasattr(model_cache, "empty_for_testing"):
            # don't continue testing if we can't empty the cache as it will certainly fail.
            return

        # by clearing the cache and proxy session we force the proxy to
        # re-authenticate against the upstream registry.
        model_cache.empty_for_testing()
        self.proxy._session.headers.pop("Authorization")
        try:
            self.proxy.get_manifest(image_ref=self.tag)
        except Exception as e:
            assert False, f"unexpected exception {e}"

    def test_blob_exists(self):
        try:
            self.proxy.blob_exists(digest=self.digest)
        except Exception as e:
            assert False, f"unexpected exception {e}"

    def test_blob_exists_404(self):
        with pytest.raises(UpstreamRegistryError):
            self.proxy.blob_exists(digest=self.digest_404)

    def test_get_blob(self):
        try:
            self.proxy.get_blob(self.digest)
        except Exception as e:
            assert False, f"unexpected exception {e}"

    def test_get_blob_404(self):
        with pytest.raises(UpstreamRegistryError):
            self.proxy.get_blob(self.digest_404)
