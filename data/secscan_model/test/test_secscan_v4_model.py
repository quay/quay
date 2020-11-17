from peewee import fn
import mock
import pytest
import os
import json

from datetime import datetime, timedelta

from data.secscan_model.secscan_v4_model import V4SecurityScanner, IndexReportState, features_for
from data.secscan_model.datatypes import (
    ScanLookupStatus,
    SecurityInformation,
    Layer,
    PaginatedNotificationStatus,
)
from data.database import (
    Manifest,
    Repository,
    ManifestSecurityStatus,
    IndexStatus,
    IndexerVersion,
    User,
    ManifestBlob,
    db_transaction,
    MediaType,
)
from data.registry_model.datatypes import Manifest as ManifestDataType
from data.registry_model import registry_model
from util.secscan.v4.api import APIRequestFailure
from util.canonicaljson import canonicalize
from image.docker.schema2 import DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE

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


def test_perform_indexing_needs_reindexing_skip_unsupported(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "new hash"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "new hash",
    )

    for manifest in Manifest.select():
        ManifestSecurityStatus.create(
            manifest=manifest,
            repository=manifest.repository,
            error_json={},
            index_status=IndexStatus.MANIFEST_UNSUPPORTED,
            indexer_hash="old hash",
            indexer_version=IndexerVersion.V4,
            last_indexed=datetime.utcnow()
            - timedelta(seconds=app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing()

    # Since this manifest should not be scanned, the old hash should remain
    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.indexer_hash == "old hash"


@pytest.mark.parametrize(
    "index_status, indexer_state, seconds, expect_zero",
    [
        # Unsupported manifest, never rescan
        (
            IndexStatus.MANIFEST_UNSUPPORTED,
            {"status": "old hash"},
            app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            True,
        ),
        # Old hash and recent scan, don't rescan
        (IndexStatus.COMPLETED, {"status": "old hash"}, 0, True),
        # Old hash and old scan, rescan
        (
            IndexStatus.COMPLETED,
            {"status": "old hash"},
            app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and old scan, don't rescan
        (
            IndexStatus.COMPLETED,
            {"status": "new hash"},
            app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and recent scan, don't rescan
        (IndexStatus.FAILED, {"status": "old hash"}, 0, True),
        # Old hash and old scan, rescan
        (
            IndexStatus.FAILED,
            {"status": "old hash"},
            app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and old scan, rescan
        (
            IndexStatus.FAILED,
            {"status": "new hash"},
            app.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
    ],
)
def test_manifest_iterator(
    initialized_db, set_secscan_config, index_status, indexer_state, seconds, expect_zero
):
    secscan = V4SecurityScanner(app, instance_keys, storage)

    for manifest in Manifest.select():
        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == manifest,
                ManifestSecurityStatus.repository == manifest.repository,
            ).execute()
            ManifestSecurityStatus.create(
                manifest=manifest,
                repository=manifest.repository,
                error_json={},
                index_status=index_status,
                indexer_hash="old hash",
                indexer_version=IndexerVersion.V4,
                last_indexed=datetime.utcnow() - timedelta(seconds=seconds),
                metadata_json={},
            )

    iterator = secscan._get_manifest_iterator(
        indexer_state,
        Manifest.select(fn.Min(Manifest.id)).scalar(),
        Manifest.select(fn.Max(Manifest.id)).scalar(),
    )

    count = 0
    for candidate, abt, num_remaining in iterator:
        count = count + 1

    if expect_zero:
        assert count == 0
    else:
        assert count != 0


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


def test_perform_indexing_invalid_manifest(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()

    # Delete all ManifestBlob rows to cause the manifests to be invalid.
    ManifestBlob.delete().execute()

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_UNSUPPORTED


def test_lookup_notification_page_invalid(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.retrieve_notification_page.return_value = None

    result = secscan.lookup_notification_page("someinvalidid")

    assert result.status == PaginatedNotificationStatus.FATAL_ERROR


def test_lookup_notification_page_valid(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.retrieve_notification_page.return_value = {
        "notifications": [
            {
                "id": "5e4b387e-88d3-4364-86fd-063447a6fad2",
                "manifest": "sha256:35c102085707f703de2d9eaad8752d6fe1b8f02b5d2149f1d8357c9cc7fb7d0a",
                "reason": "added",
                "vulnerability": {},
            }
        ],
        "page": {},
    }

    result = secscan.lookup_notification_page("5e4b387e-88d3-4364-86fd-063447a6fad2")

    assert result.status == PaginatedNotificationStatus.SUCCESS
    assert result.next_page_index is None
    assert (
        result.data[0]["manifest"]
        == "sha256:35c102085707f703de2d9eaad8752d6fe1b8f02b5d2149f1d8357c9cc7fb7d0a"
    )


def test_mark_notification_handled(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.delete_notification.return_value = True

    assert secscan.mark_notification_handled("somevalidid") == True


def test_process_notification_page(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(app, instance_keys, storage)

    results = list(
        secscan.process_notification_page(
            [
                {"reason": "removed",},
                {
                    "reason": "added",
                    "manifest": "sha256:abcd",
                    "vulnerability": {
                        "normalized_severity": "s",
                        "description": "d",
                        "package": {"id": "42", "name": "p", "version": "v0.0.1",},
                        "name": "n",
                        "fixed_in_version": "f",
                        "links": "l",
                    },
                },
            ]
        )
    )

    assert len(results) == 1
    assert results[0].manifest_digest == "sha256:abcd"
    assert results[0].vulnerability.Severity == "s"
    assert results[0].vulnerability.Description == "d"
    assert results[0].vulnerability.NamespaceName == "p"
    assert results[0].vulnerability.Name == "n"
    assert results[0].vulnerability.FixedBy == "f"
    assert results[0].vulnerability.Link == "l"


def test_perform_indexing_manifest_list(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)
    Manifest.update(
        media_type=MediaType.get(name=DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE)
    ).execute()

    secscan = V4SecurityScanner(app, instance_keys, storage)
    secscan._secscan_api = mock.Mock()

    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_UNSUPPORTED
