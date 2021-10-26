import json
import time
import unittest

from app import app, storage, url_scheme_and_hostname
from config import build_requests_session
from data import model
from data.registry_model import registry_model
from data.database import Image, ManifestLegacyImage
from initdb import setup_database_for_testing, finished_database_for_testing
from util.secscan.secscan_util import get_blob_download_uri_getter
from util.secscan.v4.api import ClairSecurityScannerAPI, APIRequestFailure
from util.secscan.v4.fake import fake_security_scanner
from util.secscan.blob import BlobURLRetriever
from util.security.instancekeys import InstanceKeys


ADMIN_ACCESS_USER = "devtable"
SIMPLE_REPO = "simple"


def _get_legacy_image(namespace, repo, tag, include_storage=True):
    repo_ref = registry_model.lookup_repository(namespace, repo)
    repo_tag = registry_model.get_repo_tag(repo_ref, tag)
    manifest = registry_model.get_manifest_for_tag(repo_tag)
    return ManifestLegacyImage.get(manifest_id=manifest._db_id).image


class TestSecurityScanner(unittest.TestCase):
    def setUp(self):
        # Enable direct download in fake storage.
        storage.put_content(["local_us"], "supports_direct_download", b"true")

        # Have fake storage say all files exist for the duration of the test.
        storage.put_content(["local_us"], "all_files_exist", b"true")

        # Setup the database with fake storage.
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

        instance_keys = InstanceKeys(app)

        retriever = BlobURLRetriever(storage, instance_keys, app)

        self.api = ClairSecurityScannerAPI(
            "http://fakesecurityscanner", build_requests_session(), retriever
        )

    def tearDown(self):
        storage.remove(["local_us"], "supports_direct_download")
        storage.remove(["local_us"], "all_files_exist")

        finished_database_for_testing(self)
        self.ctx.__exit__(True, None, None)

    def assertAnalyzed(self, layer, security_scanner, isAnalyzed, engineVersion):
        self.assertEqual(isAnalyzed, layer.security_indexed)
        self.assertEqual(engineVersion, layer.security_indexed_engine)

        if isAnalyzed:
            self.assertTrue(security_scanner.has_layer(security_scanner.layer_id(layer)))

            # Ensure all parent layers are marked as analyzed.
            parents = model.image.get_parent_images(ADMIN_ACCESS_USER, SIMPLE_REPO, layer)
            for parent in parents:
                self.assertTrue(parent.security_indexed)
                self.assertEqual(engineVersion, parent.security_indexed_engine)
                self.assertTrue(security_scanner.has_layer(security_scanner.layer_id(parent)))

    def test_get_layer(self):
        """
        Test for basic retrieval of layers from the security scanner.
        """
        repo_ref = registry_model.lookup_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        repo_tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(repo_tag)
        layers = registry_model.list_manifest_layers(manifest, storage, True)
        registry_model.populate_legacy_images_for_testing(manifest, storage)

        with fake_security_scanner() as security_scanner:
            # Ensure the layer doesn't exist yet.
            self.assertIsNone(self.api.index_report(manifest.digest))

            # Add the layer.
            self.api.index(manifest, layers)

            # Retrieve the results.
            result = self.api.vulnerability_report(manifest.digest)
            self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
