import pytest
from mock import patch, Mock

from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformationLookupResult
from data.secscan_model.secscan_v2_model import V2SecurityScanner, ScanToken as V2ScanToken
from data.secscan_model.secscan_v4_model import (
    V4SecurityScanner,
    IndexReportState,
    ScanToken as V4ScanToken,
)
from data.secscan_model import secscan_model, SplitScanToken
from data.registry_model import registry_model

from test.fixtures import *

from app import app, instance_keys, storage


@pytest.mark.parametrize(
    "repository, v4_whitelist",
    [(("devtable", "complex"), []), (("devtable", "complex"), ["devtable"]),],
)
def test_load_security_information_v2_only(repository, v4_whitelist, initialized_db):
    app.config["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"] = v4_whitelist

    secscan_model.configure(app, instance_keys, storage)

    repo = registry_model.lookup_repository(*repository)
    for tag in registry_model.list_all_active_repository_tags(repo):
        manifest = registry_model.get_manifest_for_tag(tag)
        assert manifest

        result = secscan_model.load_security_information(manifest, True)
        assert isinstance(result, SecurityInformationLookupResult)
        assert result.status == ScanLookupStatus.NOT_YET_INDEXED


@pytest.mark.parametrize(
    "repository, v4_whitelist",
    [
        (("devtable", "complex"), []),
        (("devtable", "complex"), ["devtable"]),
        (("buynlarge", "orgrepo"), ["devtable"]),
        (("buynlarge", "orgrepo"), ["devtable", "buynlarge"]),
        (("buynlarge", "orgrepo"), ["devtable", "buynlarge", "sellnsmall"]),
    ],
)
def test_load_security_information(repository, v4_whitelist, initialized_db):
    app.config["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"] = v4_whitelist
    app.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"
    secscan_api = Mock()

    with patch("data.secscan_model.secscan_v4_model.ClairSecurityScannerAPI", secscan_api):
        secscan_model.configure(app, instance_keys, storage)

        repo = registry_model.lookup_repository(*repository)
        for tag in registry_model.list_all_active_repository_tags(repo):
            manifest = registry_model.get_manifest_for_tag(tag)
            assert manifest

            result = secscan_model.load_security_information(manifest, True)
            assert isinstance(result, SecurityInformationLookupResult)
            assert result.status == ScanLookupStatus.NOT_YET_INDEXED


@pytest.mark.parametrize(
    "next_token, expected_next_token",
    [
        (None, SplitScanToken("v4", None)),
        (SplitScanToken("v4", V4ScanToken(1)), SplitScanToken("v4", None)),
        (SplitScanToken("v4", None), SplitScanToken("v2", V2ScanToken(158))),
        (SplitScanToken("v2", V2ScanToken(158)), SplitScanToken("v2", None)),
        (SplitScanToken("v2", None), None),
    ],
)
def test_perform_indexing_v2_only(next_token, expected_next_token, initialized_db):
    def layer_analyzer(*args, **kwargs):
        return Mock()

    with patch("util.secscan.analyzer.LayerAnalyzer", layer_analyzer):
        secscan_model.configure(app, instance_keys, storage)

        assert secscan_model.perform_indexing(next_token) == expected_next_token


@pytest.mark.parametrize(
    "next_token, expected_next_token",
    [
        (None, SplitScanToken("v4", V4ScanToken(56))),
        (SplitScanToken("v4", V4ScanToken(1)), SplitScanToken("v4", V4ScanToken(56))),
        (SplitScanToken("v4", None), SplitScanToken("v2", V2ScanToken(158))),
        (SplitScanToken("v2", V2ScanToken(158)), SplitScanToken("v2", None)),
        (SplitScanToken("v2", None), None),
    ],
)
def test_perform_indexing(next_token, expected_next_token, initialized_db):
    app.config["SECURITY_SCANNER_V4_NAMESPACE_WHITELIST"] = ["devtable"]
    app.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"

    def secscan_api(*args, **kwargs):
        api = Mock()
        api.state.return_value = {"state": "abc"}
        api.index.return_value = ({"err": None, "state": IndexReportState.Index_Finished}, "abc")

        return api

    def layer_analyzer(*args, **kwargs):
        return Mock()

    with patch("data.secscan_model.secscan_v4_model.ClairSecurityScannerAPI", secscan_api):
        with patch("util.secscan.analyzer.LayerAnalyzer", layer_analyzer):
            secscan_model.configure(app, instance_keys, storage)

            assert secscan_model.perform_indexing(next_token) == expected_next_token
