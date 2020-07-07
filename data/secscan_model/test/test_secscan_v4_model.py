from peewee import fn
import mock
import pytest
import os
import json

from datetime import datetime, timedelta

from data.secscan_model.secscan_v4_model import V4SecurityScanner, IndexReportState, features_for
from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformation, Layer
from data.database import (
    Manifest,
    Repository,
    ManifestSecurityStatus,
    IndexStatus,
    IndexerVersion,
    User,
)
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.registry_model import registry_model
from util.secscan.v4.api import APIRequestFailure
from util.canonicaljson import canonicalize

from test.fixtures import *

from app import app, instance_keys, storage


@pytest.fixture()
def set_secscan_config():
    app.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"


def test_load_security_information_queued(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    secscan = V4SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.NOT_YET_INDEXED


def test_load_security_information_failed_to_index(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        error_json='failed to fetch layers: encountered error while fetching a layer: fetcher: unknown content-type "binary/octet-stream"',
        index_status=IndexStatus.FAILED,
        indexer_hash="",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    secscan = V4SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.FAILED_TO_INDEX


def test_load_security_information_api_returns_none(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        error_json={},
        index_status=IndexStatus.COMPLETED,
        indexer_hash="abc",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.vulnerability_report.return_value = None

    assert secscan.load_security_information(manifest).status == ScanLookupStatus.NOT_YET_INDEXED


def test_load_security_information_api_request_failure(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    mss = ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        error_json={},
        index_status=IndexStatus.COMPLETED,
        indexer_hash="abc",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.vulnerability_report.side_effect = APIRequestFailure()

    assert secscan.load_security_information(manifest).status == ScanLookupStatus.COULD_NOT_LOAD
    assert not ManifestSecurityStatus.select().where(ManifestSecurityStatus.id == mss.id).exists()


def test_load_security_information_success(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        error_json={},
        index_status=IndexStatus.COMPLETED,
        indexer_hash="abc",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.vulnerability_report.return_value = {
        "manifest_hash": manifest.digest,
        "state": "IndexFinished",
        "packages": {},
        "distributions": {},
        "repository": {},
        "environments": {},
        "package_vulnerabilities": {},
        "success": True,
        "err": "",
    }

    result = secscan.load_security_information(manifest)

    assert result.status == ScanLookupStatus.SUCCESS
    assert result.security_information == SecurityInformation(Layer(manifest.digest, "", "", 4, []))


def test_perform_indexing_whitelist(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    next_token = secscan.perform_indexing()

    assert next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1

    assert secscan._secscan_api.index.call_count == Manifest.select().count()
    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.COMPLETED


def test_perform_indexing_failed(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    for manifest in Manifest.select():
        ManifestSecurityStatus.create(
            manifest=manifest,
            repository=manifest.repository,
            error_json={},
            index_status=IndexStatus.FAILED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            last_indexed=datetime.utcnow()
            - timedelta(seconds=app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.COMPLETED


def test_perform_indexing_failed_within_reindex_threshold(initialized_db, set_secscan_config):
    app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    for manifest in Manifest.select():
        ManifestSecurityStatus.create(
            manifest=manifest,
            repository=manifest.repository,
            error_json={},
            index_status=IndexStatus.FAILED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            metadata_json={},
        )

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED


def test_perform_indexing_needs_reindexing(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "xyz"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "xyz",
    )

    for manifest in Manifest.select():
        ManifestSecurityStatus.create(
            manifest=manifest,
            repository=manifest.repository,
            error_json={},
            index_status=IndexStatus.COMPLETED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            last_indexed=datetime.utcnow()
            - timedelta(seconds=app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.indexer_hash == "xyz"


def test_perform_indexing_needs_reindexing_within_reindex_threshold(
    initialized_db, set_secscan_config
):
    app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "xyz"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "xyz",
    )

    for manifest in Manifest.select():
        ManifestSecurityStatus.create(
            manifest=manifest,
            repository=manifest.repository,
            error_json={},
            index_status=IndexStatus.COMPLETED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            metadata_json={},
        )

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.indexer_hash == "abc"


def test_perform_indexing_api_request_failure_state(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.side_effect = APIRequestFailure()

    next_token = secscan.perform_indexing()

    assert next_token is None
    assert ManifestSecurityStatus.select().count() == 0


def test_perform_indexing_api_request_failure_index(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.side_effect = APIRequestFailure()

    next_token = secscan.perform_indexing()

    assert next_token is None
    assert ManifestSecurityStatus.select().count() == 0

    # Set security scanner to return good results and attempt indexing again
    secscan._secscan_api.index.side_effect = None
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    next_token = secscan.perform_indexing()

    assert next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1
    assert ManifestSecurityStatus.select().count() == Manifest.select(fn.Max(Manifest.id)).count()


def test_features_for():
    vuln_report_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "vulnerabilityreport.json"
    )
    security_info_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "securityinformation.json"
    )

    with open(vuln_report_filename) as vuln_report_file:
        vuln_report = json.load(vuln_report_file)

    with open(security_info_filename) as security_info_file:
        security_info = json.load(security_info_file)

    expected = security_info["data"]
    expected["Layer"]["Features"].sort(key=lambda d: d["Name"])
    generated = SecurityInformation(
        Layer(
            "sha256:b05ac1eeec8635442fa5d3e55d6ef4ad287b9c66055a552c2fd309c334563b0a",
            "",
            "",
            4,
            features_for(vuln_report),
        )
    ).to_dict()

    # Sort the Features' list so that the following assertion holds even if they are out of order
    # (Ordering of the dicts' key iteration is different from Python 2 to 3)
    expected["Layer"]["Features"].sort(key=lambda d: d["Name"])
    generated["Layer"]["Features"].sort(key=lambda d: d["Name"])

    assert generated == expected
