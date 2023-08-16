import io
from unittest.mock import MagicMock

import pytest

from image.shared.schemas import parse_manifest_from_bytes
from proxy import UpstreamRegistryError
from util.bytes import Bytes


@pytest.fixture()
def proxy_manifest_response():
    def _proxy_manifest_response(expected_manifest_ref, manifest_json, manifest_media_type):
        def mock_manifest_exists(manifest_ref, media_type=None):
            # we only want to respond with a 200 when the digest matches the
            # one we're mocking for.
            if manifest_ref != expected_manifest_ref:
                raise UpstreamRegistryError(404)
            return parse_manifest_from_bytes(
                Bytes.for_string_or_unicode(manifest_json),
                manifest_media_type,
            ).digest

        def mock_get_manifest(manifest_ref, media_type=None):
            if manifest_ref != expected_manifest_ref:
                raise UpstreamRegistryError(404)
            return manifest_json, manifest_media_type

        def mock_blob_exists(digest):
            return {"status": 200}

        def mock_get_blob(digest):
            return io.BytesIO(b"test"), 4

        proxy_mock = MagicMock()
        proxy_mock.manifest_exists.side_effect = mock_manifest_exists
        proxy_mock.get_manifest.side_effect = mock_get_manifest
        proxy_mock.blob_exists.side_effect = mock_blob_exists
        proxy_mock.get_blob.side_effect = mock_get_blob
        return proxy_mock

    return _proxy_manifest_response
