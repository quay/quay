from test.fixtures import *

import pytest
from mock import Mock, patch

from app import app, instance_keys, storage
from data.database import IndexerVersion, IndexStatus, ManifestSecurityStatus
from data.registry_model import registry_model
from data.secscan_model import secscan_model
from data.secscan_model.datatypes import (
    ScanLookupStatus,
    SecurityInformationLookupResult,
)
from data.secscan_model.secscan_v4_model import IndexReportState
from data.secscan_model.secscan_v4_model import ScanToken as V4ScanToken
from data.secscan_model.secscan_v4_model import V4SecurityScanner


@pytest.mark.parametrize(
    "indexed_v4, expected_status",
    [
        (False, ScanLookupStatus.NOT_YET_INDEXED),
        (True, ScanLookupStatus.UNSUPPORTED_FOR_INDEXING),
    ],
)
def test_load_security_information(indexed_v4, expected_status, initialized_db):
    secscan_model.configure(app, instance_keys, storage)

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.find_matching_tag(repository_ref, ["latest"])
    manifest = registry_model.get_manifest_for_tag(tag)
    assert manifest

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
        (None, V4ScanToken(56), None),
        (V4ScanToken(None), V4ScanToken(56), AssertionError),
        (V4ScanToken(1), V4ScanToken(56), None),
    ],
)
def test_perform_indexing(next_token, expected_next_token, expected_error, initialized_db):
    app.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"

    def secscan_api(*args, **kwargs):
        api = Mock()
        api.vulnerability_report.return_value = {"vulnerabilities": []}
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
