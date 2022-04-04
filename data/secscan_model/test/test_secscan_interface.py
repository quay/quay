import pytest

from mock import patch, Mock

from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformationLookupResult
from data.secscan_model.secscan_v2_model import V2SecurityScanner, ScanToken as V2ScanToken
from data.secscan_model.secscan_v4_model import (
    V4SecurityScanner,
    IndexReportState,
    ScanToken as V4ScanToken,
)
from data.secscan_model import secscan_model
from data.registry_model import registry_model
from data.model.oci import shared
from data.database import ManifestSecurityStatus, IndexerVersion, IndexStatus, ManifestLegacyImage

from test.fixtures import *

from app import app, instance_keys, storage


@pytest.mark.parametrize(
    "indexed_v2, indexed_v4, expected_status",
    [
        (False, False, ScanLookupStatus.NOT_YET_INDEXED),
        (False, True, ScanLookupStatus.UNSUPPORTED_FOR_INDEXING),
        (True, False, ScanLookupStatus.FAILED_TO_INDEX),
        (True, True, ScanLookupStatus.UNSUPPORTED_FOR_INDEXING),
    ],
)
def test_load_security_information(indexed_v2, indexed_v4, expected_status, initialized_db):
    secscan_model.configure(app, instance_keys, storage)

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.find_matching_tag(repository_ref, ["latest"])
    manifest = registry_model.get_manifest_for_tag(tag)
    assert manifest

    registry_model.populate_legacy_images_for_testing(manifest, storage)

    image = shared.get_legacy_image_for_manifest(manifest._db_id)

    if indexed_v2:
        image.security_indexed = False
        image.security_indexed_engine = 3
        image.save()
    else:
        ManifestLegacyImage.delete().where(
            ManifestLegacyImage.manifest == manifest._db_id
        ).execute()

    if indexed_v4:
        ManifestSecurityStatus.create(
            manifest=manifest._db_id,
            repository=repository_ref._db_id,
            error_json={},
            index_status=IndexStatus.MANIFEST_UNSUPPORTED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            metadata_json={},
        )

    result = secscan_model.load_security_information(manifest, True)

    assert isinstance(result, SecurityInformationLookupResult)
    assert result.status == expected_status


@pytest.mark.parametrize(
    "next_token, expected_next_token, expected_error",
    [
        (
            None,  # MIN(id) is used in this case (1 in test db)
            V4ScanToken(52, 50, {"state": "abc"}),
            None,
        ),
        (
            V4ScanToken(None, None, None),
            V4ScanToken(51, 50, {"state": "abc"}),
            AssertionError,
        ),
        (
            V4ScanToken(1, 50, {"state": "abc"}),
            V4ScanToken(52, 50, {"state": "abc"}),
            None,
        ),
        (
            V2ScanToken(158, 50, {"state": "abc"}),
            V4ScanToken(56, 50, {"state": "abc"}),
            AssertionError,
        ),
    ],
)
def test_perform_indexing(next_token, expected_next_token, expected_error, initialized_db):
    app.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"
    app.config["SECURITY_SCANNER_V4_BATCH_SIZE"] = 50  # There are 55 manifests in the test db set

    def secscan_api(*args, **kwargs):
        api = Mock()
        api.state.return_value = {"state": "abc"}
        api.index.return_value = ({"err": None, "state": IndexReportState.Index_Finished}, "abc")

        return api

    with patch("data.secscan_model.secscan_v4_model.ClairSecurityScannerAPI", secscan_api):
        secscan_model.configure(app, instance_keys, storage)

        if expected_error is not None:
            with pytest.raises(expected_error):
                secscan_model.perform_indexing(next_token)
        else:
            assert secscan_model.perform_indexing(next_token) == expected_next_token


def test_token_next_page():
    import random

    batch_size = random.randint(1, 1000)
    indexer_state = "test"
    min_id = 1

    scan_token = V4ScanToken(min_id, batch_size, indexer_state)
    next_token = scan_token.next_page()

    assert next_token.min_id == scan_token.min_id + batch_size + 1
    assert next_token.indexer_state == scan_token.indexer_state
    assert next_token.batch_size == scan_token.batch_size
