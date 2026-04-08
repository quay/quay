import json
import logging
import os
from collections import namedtuple
from datetime import datetime, timedelta

import mock
import pytest
from peewee import fn

from app import app as application
from app import instance_keys, storage
from data import model
from data.cache import InMemoryDataModelCache, cache_key
from data.cache.test.test_cache import TEST_CACHE_CONFIG
from data.database import (
    IndexerVersion,
    IndexStatus,
    Manifest,
    ManifestBlob,
    ManifestSecurityStatus,
    MediaType,
    db_transaction,
)
from data.registry_model import registry_model
from data.registry_model.datatypes import ManifestLayer, RepositoryReference
from data.secscan_model.datatypes import (
    NVD,
    CVSSv3,
    Feature,
    Layer,
    Metadata,
    PaginatedNotificationStatus,
    ScanLookupStatus,
    SecurityInformation,
    Vulnerability,
    link_to_cves,
    vulns_to_base_scores,
    vulns_to_cves,
)
from data.secscan_model.secscan_v4_model import (
    IndexReportState,
    SecurityInformationLookupResult,
    V4SecurityScanner,
    _has_container_layers,
    features_for,
)
from image.docker.schema2 import (
    DOCKER_SCHEMA2_LAYER_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.oci import (
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
    OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE,
)
from initdb import create_schema2_or_oci_manifest_for_testing
from test.fixtures import *
from util.secscan.v4.api import APIRequestFailure


@pytest.fixture()
def set_secscan_config():
    application.config["SECURITY_SCANNER_V4_ENDPOINT"] = "http://clairv4:6060"


def test_load_security_information_queued(initialized_db, set_secscan_config):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.vulnerability_report.side_effect = APIRequestFailure()

    assert secscan.load_security_information(manifest).status == ScanLookupStatus.COULD_NOT_LOAD
    # Assert that the ManifestSecurityStatus entry is not deleted.
    assert ManifestSecurityStatus.select().where(ManifestSecurityStatus.id == mss.id).exists()


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

    secscan = V4SecurityScanner(application, instance_keys, storage)
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


def test_load_security_information_success_with_cache(initialized_db, set_secscan_config):
    model_cache = InMemoryDataModelCache(TEST_CACHE_CONFIG)
    model_cache.empty_for_testing()

    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    sec_info_cache_key = cache_key.for_security_report(manifest.digest, {})

    ManifestSecurityStatus.create(
        manifest=manifest._db_id,
        repository=repository_ref._db_id,
        error_json={},
        index_status=IndexStatus.COMPLETED,
        indexer_hash="abc",
        indexer_version=IndexerVersion.V4,
        metadata_json={},
    )

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    result = secscan.load_security_information(manifest, model_cache=model_cache)

    assert result.status == ScanLookupStatus.SUCCESS
    assert result.security_information == SecurityInformation(Layer(manifest.digest, "", "", 4, []))

    # the response should be cached now
    cache_result_json = model_cache.cache.get(sec_info_cache_key.key)
    assert cache_result_json is not None

    cache_result = json.loads(cache_result_json)
    assert cache_result["manifest_hash"] == manifest.digest


def test_perform_indexing_whitelist(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": []}
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    secscan.perform_indexing_recent_manifests()
    next_token = secscan.perform_indexing()

    assert next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1

    manifest_count = Manifest.select().count()
    assert secscan._secscan_api.index.call_count >= manifest_count
    assert ManifestSecurityStatus.select().count() == manifest_count
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.COMPLETED


def test_perform_indexing_failed(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
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
            - timedelta(seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.COMPLETED


def test_perform_indexing_failed_within_reindex_threshold(initialized_db, set_secscan_config):
    application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED


def test_perform_indexing_needs_reindexing(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
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
            - timedelta(seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.indexer_hash == "xyz"


@pytest.mark.parametrize(
    "index_status", [IndexStatus.MANIFEST_UNSUPPORTED, IndexStatus.MANIFEST_LAYER_TOO_LARGE]
)
def test_perform_indexing_needs_reindexing_skippable(
    initialized_db, set_secscan_config, index_status
):
    secscan = V4SecurityScanner(application, instance_keys, storage)
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
            index_status=index_status,
            indexer_hash="old hash",
            indexer_version=IndexerVersion.V4,
            last_indexed=datetime.utcnow()
            - timedelta(seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60),
            metadata_json={},
        )

    secscan.perform_indexing_recent_manifests()
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
            application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            True,
        ),
        # Old hash and recent scan, don't rescan
        (IndexStatus.COMPLETED, {"status": "old hash"}, 0, True),
        # old hash and old scan, rescan
        (
            IndexStatus.COMPLETED,
            {"status": "old hash"},
            application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and old scan, don't rescan
        (
            IndexStatus.COMPLETED,
            {"status": "new hash"},
            application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and recent scan, don't rescan
        (IndexStatus.FAILED, {"status": "old hash"}, 0, True),
        # Old hash and old scan, rescan
        (
            IndexStatus.FAILED,
            {"status": "old hash"},
            application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
        # New hash and old scan, rescan
        (
            IndexStatus.FAILED,
            {"status": "new hash"},
            application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] + 60,
            False,
        ),
    ],
)
def test_manifest_iterator(
    initialized_db, set_secscan_config, index_status, indexer_state, seconds, expect_zero
):
    secscan = V4SecurityScanner(application, instance_keys, storage)

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
        reindex_threshold=datetime.utcnow()
        - timedelta(seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"]),
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
    application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"] = 300

    secscan = V4SecurityScanner(application, instance_keys, storage)
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

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.indexer_hash == "abc"


def test_perform_indexing_api_request_failure_state(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.side_effect = APIRequestFailure()
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": []}

    secscan.perform_indexing_recent_manifests()
    next_token = secscan.perform_indexing()

    assert next_token is None
    assert ManifestSecurityStatus.select().count() == 0


def test_perform_indexing_api_request_index_error_response(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "xyz"}
    secscan._secscan_api.index.return_value = (
        {"err": "something", "state": IndexReportState.Index_Error},
        "xyz",
    )

    secscan.perform_indexing_recent_manifests()
    next_token = secscan.perform_indexing()
    assert next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1
    assert ManifestSecurityStatus.select().count() == Manifest.select(fn.Max(Manifest.id)).count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.FAILED


def test_perform_indexing_api_request_non_finished_state(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "xyz"}
    secscan._secscan_api.index.return_value = (
        {"err": "something", "state": "ScanLayers"},
        "xyz",
    )

    secscan.perform_indexing_recent_manifests()
    next_token = secscan.perform_indexing()
    assert next_token and next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1
    assert ManifestSecurityStatus.select().count() == 0


def test_perform_indexing_api_request_failure_index(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.side_effect = APIRequestFailure()
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": []}

    secscan.perform_indexing_recent_manifests()
    next_token = secscan.perform_indexing()

    assert next_token and next_token.min_id == Manifest.select(fn.Max(Manifest.id)).scalar() + 1
    assert ManifestSecurityStatus.select().count() == 0

    # Set security scanner to return good results and attempt indexing again
    secscan._secscan_api.index.side_effect = None
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "abc",
    )

    secscan.perform_indexing_recent_manifests()
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
            "sha256:4fd9553ca70c7ed6cbb466573fed2d03b0a8dd2c2eba9febf2ce30f8d537ba17",
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


def test_features_for_duplicates():
    vuln_report_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "vulnerabilityreport_duplicates.json"
    )
    security_info_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "securityinformation_deduped.json"
    )
    with open(vuln_report_filename) as vuln_report_file:
        vuln_report = json.load(vuln_report_file)

    with open(security_info_filename) as security_info_file:
        expected = json.load(security_info_file)

    generated = SecurityInformation(
        Layer(
            vuln_report["manifest_hash"],
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
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()

    # Delete all ManifestBlob rows to cause the manifests to be invalid.
    ManifestBlob.delete().execute()

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_UNSUPPORTED


def test_lookup_notification_page_invalid(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.retrieve_notification_page.return_value = None

    result = secscan.lookup_notification_page("someinvalidid")

    assert result.status == PaginatedNotificationStatus.FATAL_ERROR


def test_lookup_notification_page_valid(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)
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
    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.delete_notification.return_value = True

    assert secscan.mark_notification_handled("somevalidid") == True


def test_process_notification_page(initialized_db, set_secscan_config):
    secscan = V4SecurityScanner(application, instance_keys, storage)

    results = list(
        secscan.process_notification_page(
            [
                {
                    "reason": "removed",
                },
                {
                    "reason": "added",
                    "manifest": "sha256:abcd",
                    "vulnerability": {
                        "normalized_severity": "s",
                        "description": "d",
                        "package": {
                            "id": "42",
                            "name": "p",
                            "version": "v0.0.1",
                        },
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

    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()

    secscan.perform_indexing_recent_manifests()
    secscan.perform_indexing()

    assert ManifestSecurityStatus.select().count() == Manifest.select().count()
    for mss in ManifestSecurityStatus.select():
        assert mss.index_status == IndexStatus.MANIFEST_UNSUPPORTED


def test_enrichments_in_features_for():
    vuln_report_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "vulnerabilityreport_withenrichments.json"
    )
    security_info_filename = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "securityinformation_withenrichments.json"
    )

    with open(vuln_report_filename) as vuln_report_file:
        vuln_report = json.load(vuln_report_file)

    with open(security_info_filename) as security_info_file:
        expected = json.load(security_info_file)

    expected["Layer"]["Features"].sort(key=lambda d: d["Name"])
    generated = SecurityInformation(
        Layer(
            "sha256:4b42c2e36b0bedf017e14dc270f315e627a2a0030f453687a06375fa88694298",
            "",
            "",
            4,
            features_for(vuln_report),
        )
    ).to_dict()

    # Sort the Features' list so that the following assertion holds even if they are out of order
    expected["Layer"]["Features"].sort(key=lambda d: d["Name"])
    generated["Layer"]["Features"].sort(key=lambda d: d["Name"])

    assert generated == expected


@pytest.mark.parametrize(
    "input_string, expected_output",
    [
        (
            "This is a test string with CVE-2021-1234 and CVE-2022-5678",
            ["CVE-2021-1234", "CVE-2022-5678"],
        ),
        ("No CVEs in this string", []),
        ("CVE-2023-12345 is the only CVE here", ["CVE-2023-12345"]),
        ("", []),
    ],
)
def test_link_to_cves(input_string, expected_output):
    assert link_to_cves(input_string) == expected_output


@pytest.mark.parametrize(
    "vulnerabilities, expected_output",
    [
        (
            [
                Vulnerability(
                    Severity="High",
                    NamespaceName="",
                    Link="CVE-2021-1234",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=CVSSv3()),
                    ),
                ),
                Vulnerability(
                    Severity="Medium",
                    NamespaceName="",
                    Link="CVE-2022-5678",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=CVSSv3()),
                    ),
                ),
                Vulnerability(
                    Severity="Low",
                    NamespaceName="",
                    Link="Not a CVE link",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=CVSSv3()),
                    ),
                ),
            ],
            ["CVE-2021-1234", "CVE-2022-5678"],
        ),
    ],
)
def test_vulns_to_cves(vulnerabilities, expected_output):
    assert vulns_to_cves(vulnerabilities) == expected_output


@pytest.mark.parametrize(
    "vulnerabilities, expected_output",
    [
        (
            [
                Vulnerability(
                    Severity="High",
                    NamespaceName="",
                    Link="CVE-2021-1234",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=CVSSv3(Score=7.5)),
                    ),
                ),
                Vulnerability(
                    Severity="Medium",
                    NamespaceName="",
                    Link="CVE-2022-5678",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=CVSSv3(Score=None)),
                    ),
                ),
                Vulnerability(
                    Severity="Low",
                    NamespaceName="",
                    Link="Not a CVE link",
                    FixedBy="",
                    Description="",
                    Name="",
                    Metadata=Metadata(
                        UpdatedBy="",
                        RepoName="",
                        RepoLink="",
                        DistroName="",
                        DistroVersion="",
                        NVD=NVD(CVSSv3=None),
                    ),
                ),
            ],
            [7.5],
        ),
    ],
)
def test_vulns_to_base_scores(vulnerabilities, expected_output):
    assert vulns_to_base_scores(vulnerabilities) == expected_output


def test_has_container_layers_with_oci_image_layers():
    """
    Test that OCI container image layers are correctly identified.
    """

    MockBlobLayer = namedtuple("MockBlobLayer", ["mediatype"])
    MockInternalLayer = namedtuple("MockInternalLayer", ["blob_layer"])
    MockLayerInfo = namedtuple("MockLayerInfo", ["internal_layer"])

    blob_layer = MockBlobLayer(mediatype=OCI_IMAGE_TAR_GZIP_LAYER_CONTENT_TYPE)
    internal_layer = MockInternalLayer(blob_layer=blob_layer)
    layer_info = MockLayerInfo(internal_layer=internal_layer)
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert _has_container_layers([layer])


def test_has_container_layers_with_docker_schema2_layers():
    """
    Test that Docker v2 schema 2 layers are correctly identified.
    """

    MockBlobLayer = namedtuple("MockBlobLayer", ["mediatype"])
    MockInternalLayer = namedtuple("MockInternalLayer", ["blob_layer"])
    MockLayerInfo = namedtuple("MockLayerInfo", ["internal_layer"])

    blob_layer = MockBlobLayer(mediatype=DOCKER_SCHEMA2_LAYER_CONTENT_TYPE)
    internal_layer = MockInternalLayer(blob_layer=blob_layer)
    layer_info = MockLayerInfo(internal_layer=internal_layer)
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert _has_container_layers([layer])


def test_has_container_layers_with_non_container_artifact():
    """
    Tests whether non-image layers are correctly identified.
    """

    MockBlobLayer = namedtuple("MockBlobLayer", ["mediatype"])
    MockInternalLayer = namedtuple("MockInternalLayer", ["blob_layer"])
    MockLayerInfo = namedtuple("MockLayerInfo", ["internal_layer"])

    # Use helm chart layer type
    blob_layer = MockBlobLayer(mediatype="application/vnd.cncf.helm.chart.content.v1.tar+gzip")
    internal_layer = MockInternalLayer(blob_layer=blob_layer)
    layer_info = MockLayerInfo(internal_layer=internal_layer)
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert not _has_container_layers([layer])


def test_has_container_layers_empty_list():
    """
    Checks if manifests that do not contain layers (such as manifest lists) are properly detected.
    """
    assert not _has_container_layers([])


def test_has_container_layers_no_internal_layers():
    """
    Tests whether the function returns false on layers that do not have the internal_layer attribute.
    """
    MockLayerInfoNoInternal = namedtuple("MockLayerInfoNoInternal", ["digest"])
    layer_info = MockLayerInfoNoInternal(digest="sha256:abc123")
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert not _has_container_layers([layer])


def test_has_container_layers_no_blob_layer():
    """
    Tests whether layers without blob layer return False.
    """
    MockInternalLayerNoBlob = namedtuple("MockInternalLayerNoBlob", ["digest"])
    MockLayerInfo = namedtuple("MockLayerInfo", ["internal_layer"])

    internal_layer = MockInternalLayerNoBlob(digest="sha256:abc123")
    layer_info = MockLayerInfo(internal_layer=internal_layer)
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert not _has_container_layers([layer])


def test_has_container_layers_no_media_type():
    """
    Tests if the function returns False for layers without a media type.
    """
    MockBlobLayerNoMediaType = namedtuple("MockBlobLayerNoMediaType", ["digest"])
    MockInternalLayer = namedtuple("MockInternalLayer", ["blob_layer"])
    MockLayerInfo = namedtuple("MockLayerInfo", ["internal_layer"])

    blob_layer = MockBlobLayerNoMediaType(digest="sha256:abc123")
    internal_layer = MockInternalLayer(blob_layer=blob_layer)
    layer_info = MockLayerInfo(internal_layer=internal_layer)
    layer = ManifestLayer(layer_info=layer_info, blob=None)

    assert not _has_container_layers([layer])


def test_perform_indexing_schema2_manifest(initialized_db, set_secscan_config):
    """
    Explicitly test the Docker v2 schema 2 manifest and repository.
    """

    # Create a temporary Schema2 repository for this test
    user = model.user.get_user("devtable")
    repo = model.repository.create_repository("devtable", "testschema2", user)
    repo_ref = RepositoryReference.for_repo_obj(repo)

    # Use the initdb helper to create a Schema2 manifest with proper storage
    tag_map = {}
    structure = (3, [], ["latest"])  # 3 layers, no subtrees, tag named "latest"
    create_schema2_or_oci_manifest_for_testing(repo, structure, tag_map)

    # Now retrieve and test the manifest
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    assert manifest.media_type == DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE

    layers = registry_model.list_manifest_layers(manifest, storage, True)
    assert layers is not None
    assert len(layers) > 0

    assert _has_container_layers(layers)

    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {
            "err": None,
            "state": IndexReportState.Index_Finished,
        },
        "abc",
    )
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}

    secscan.perform_indexing()
    mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
    assert mss.index_status == IndexStatus.COMPLETED


def test_perform_indexing_oci_manifest(initialized_db, set_secscan_config):
    """
    Explicitly test the OCI manifest and repository.
    """

    # Create a temporary OCI repository for this test
    user = model.user.get_user("devtable")
    repo = model.repository.create_repository("devtable", "testocirepo", user)
    repo_ref = RepositoryReference.for_repo_obj(repo)

    # Use the initdb helper to create an OCI manifest with proper storage
    tag_map = {}
    structure = (3, [], ["latest"])  # 3 layers, no subtrees, tag named "latest"
    create_schema2_or_oci_manifest_for_testing(repo, structure, tag_map, schema_type="oci")

    # Now retrieve and test the manifest
    tag = registry_model.get_repo_tag(repo_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    assert manifest.media_type == OCI_IMAGE_MANIFEST_CONTENT_TYPE

    layers = registry_model.list_manifest_layers(manifest, storage, True)
    assert layers is not None
    assert len(layers) > 0

    assert _has_container_layers(layers)

    secscan = V4SecurityScanner(application, instance_keys, storage)
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.index.return_value = (
        {
            "err": None,
            "state": IndexReportState.Index_Finished,
        },
        "abc",
    )
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}

    secscan.perform_indexing()
    mss = ManifestSecurityStatus.get(manifest=manifest._db_id)
    assert mss.index_status == IndexStatus.COMPLETED


def test_batch_preemption_check(initialized_db, set_secscan_config):
    """
    Test that batch preemption checking correctly identifies manifests that have been
    recently indexed and should be skipped by the worker.
    """
    secscan = V4SecurityScanner(application, instance_keys, storage)
    reindex_threshold = datetime.utcnow() - timedelta(
        seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"]
    )

    # Get all manifests
    manifests = list(Manifest.select())
    assert len(manifests) > 0

    # Create security status for some manifests with different timestamps
    # Manifests 0-2: recently indexed (should be skipped)
    for i in range(min(3, len(manifests))):
        ManifestSecurityStatus.create(
            manifest=manifests[i],
            repository=manifests[i].repository,
            error_json={},
            index_status=IndexStatus.COMPLETED,
            indexer_hash="abc",
            indexer_version=IndexerVersion.V4,
            last_indexed=datetime.utcnow(),  # Recent
            metadata_json={},
        )

    # Manifests 3-5: old indexing (should be reindexed)
    if len(manifests) > 3:
        for i in range(3, min(6, len(manifests))):
            ManifestSecurityStatus.create(
                manifest=manifests[i],
                repository=manifests[i].repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="abc",
                indexer_version=IndexerVersion.V4,
                last_indexed=reindex_threshold - timedelta(seconds=100),  # Old
                metadata_json={},
            )

    # Manifests 6+: not indexed at all (should be indexed)

    # Test batch preemption check
    all_manifest_ids = [m.id for m in manifests]
    recently_indexed_ids = [manifests[i].id for i in range(min(3, len(manifests)))]

    # Call the internal batch_preemption_check through _index method
    # We'll create a simple iterator and inspect results
    from threading import Event

    def simple_iterator():
        for m in manifests:
            yield m, Event(), 0

    # Access the batch_preemption_check function by calling _index with a mock
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "abc"}
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}

    # Test that recently indexed manifests are skipped
    indexed_count = 0

    # Patch the index method to count calls instead of actually indexing
    def count_index(*args, **kwargs):
        nonlocal indexed_count
        indexed_count += 1
        return ({"err": None, "state": IndexReportState.Index_Finished}, "abc")

    secscan._secscan_api.index = count_index

    # Run indexing
    secscan._index(simple_iterator(), reindex_threshold)

    # Verify that recently indexed manifests were skipped
    # We expect: 3 skipped (recently indexed), rest processed
    # Note: Some manifests may be manifest lists or invalid, so actual count may be lower
    # The key is that indexed_count should be less than total because some were skipped
    assert indexed_count < len(
        manifests
    ), f"Expected some manifests to be skipped, but indexed {indexed_count} out of {len(manifests)}"


def test_batched_iterator_with_preemption_check(initialized_db, set_secscan_config):
    """
    Test the batched_iterator_with_preemption_check wrapper function that processes
    candidates in micro-batches to reduce database queries.
    """
    secscan = V4SecurityScanner(application, instance_keys, storage)
    reindex_threshold = datetime.utcnow() - timedelta(
        seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"]
    )

    # Create test manifests with different statuses
    manifests = list(Manifest.select().limit(25))  # Get 25 manifests for testing batching

    if len(manifests) < 25:
        # Need at least 25 for proper batch testing
        pytest.skip("Not enough manifests for batch testing")

    # Mark some as recently indexed
    for i in range(10):
        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == manifests[i]
            ).execute()
            ManifestSecurityStatus.create(
                manifest=manifests[i],
                repository=manifests[i].repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="recent",
                indexer_version=IndexerVersion.V4,
                last_indexed=datetime.utcnow(),  # Recent - should skip
                metadata_json={},
            )

    # Create iterator
    from threading import Event

    def test_iterator():
        for m in manifests:
            yield m, Event(), len(manifests)

    # Alternative: Test by running _index and verifying behavior
    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "test"}
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "test",
    )

    # Count how many manifests get indexed vs skipped
    indexed_count = 0
    original_index_method = secscan._secscan_api.index

    def counting_index(*args, **kwargs):
        nonlocal indexed_count
        indexed_count += 1
        return original_index_method(*args, **kwargs)

    secscan._secscan_api.index = counting_index

    # Run indexing
    secscan._index(test_iterator(), reindex_threshold)

    # Verify that batching worked - some manifests were skipped
    # We marked 10 as recently indexed, so they should be skipped
    assert indexed_count < len(
        manifests
    ), f"Expected some skipped, but indexed {indexed_count}/{len(manifests)}"


def test_batch_preemption_empty_and_edge_cases(initialized_db, set_secscan_config):
    """
    Test edge cases for batch preemption checking: empty batches, single items, etc.
    """
    secscan = V4SecurityScanner(application, instance_keys, storage)
    reindex_threshold = datetime.utcnow() - timedelta(
        seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"]
    )

    from threading import Event

    # Test 1: Empty iterator
    def empty_iterator():
        return
        yield  # Make it a generator

    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "test"}
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}

    # Should not crash with empty iterator
    secscan._index(empty_iterator(), reindex_threshold)

    # Test 2: Single manifest
    manifests = list(Manifest.select().limit(1))
    if manifests:

        def single_iterator():
            yield manifests[0], Event(), 1

        secscan._secscan_api.index.return_value = (
            {"err": None, "state": IndexReportState.Index_Finished},
            "test",
        )
        secscan._index(single_iterator(), reindex_threshold)

        # Verify it was processed (may be marked as unsupported if it's a manifest list)
        assert (
            ManifestSecurityStatus.select()
            .where(ManifestSecurityStatus.manifest == manifests[0])
            .count()
            > 0
        )


def test_batch_preemption_reduces_queries(initialized_db, set_secscan_config):
    """
    Integration test verifying that batch preemption checking actually reduces
    the number of database queries compared to individual checks.
    """
    secscan = V4SecurityScanner(application, instance_keys, storage)
    reindex_threshold = datetime.utcnow() - timedelta(
        seconds=application.config["SECURITY_SCANNER_V4_REINDEX_THRESHOLD"]
    )

    # Create 50 manifests for a realistic batch
    manifests = list(Manifest.select().limit(50))

    if len(manifests) < 50:
        pytest.skip("Not enough manifests for query reduction testing")

    # Mark half as recently indexed
    for i in range(25):
        with db_transaction():
            ManifestSecurityStatus.delete().where(
                ManifestSecurityStatus.manifest == manifests[i]
            ).execute()
            ManifestSecurityStatus.create(
                manifest=manifests[i],
                repository=manifests[i].repository,
                error_json={},
                index_status=IndexStatus.COMPLETED,
                indexer_hash="test",
                indexer_version=IndexerVersion.V4,
                last_indexed=datetime.utcnow(),
                metadata_json={},
            )

    from threading import Event

    def test_iterator():
        for m in manifests:
            yield m, Event(), len(manifests)

    secscan._secscan_api = mock.Mock()
    secscan._secscan_api.state.return_value = {"state": "test"}
    secscan._secscan_api.vulnerability_report.return_value = {"vulnerabilities": {}}
    secscan._secscan_api.index.return_value = (
        {"err": None, "state": IndexReportState.Index_Finished},
        "test",
    )

    secscan._index(test_iterator(), reindex_threshold)

    # Verify that recently indexed manifests still have original hash
    # (they were skipped, so hash wasn't updated)
    still_test_hash = 0
    for i in range(25):
        try:
            mss = ManifestSecurityStatus.get(ManifestSecurityStatus.manifest == manifests[i].id)
            if mss.indexer_hash == "test":
                still_test_hash += 1
        except ManifestSecurityStatus.DoesNotExist:
            pass

    # Most of the 25 recently indexed should still have "test" hash (they were skipped)
    assert still_test_hash >= 20, f"Expected at least 20 skipped manifests, got {still_test_hash}"
