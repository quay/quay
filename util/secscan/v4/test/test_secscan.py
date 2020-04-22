import unittest
import pytest

from mock import patch

from app import instance_keys, storage
from config import build_requests_session
from util.secscan.v4.api import ClairSecurityScannerAPI, APIRequestFailure
from util.secscan.v4.fake import fake_security_scanner
from util.secscan.blob import BlobURLRetriever
from data.registry_model import registry_model
from data.secscan_model import secscan_model
from data.database import ManifestSecurityStatus

from test.fixtures import *
from app import app


def manifest_for(namespace, repository, tagname):
    repository_ref = registry_model.lookup_repository(namespace, repository)
    tag = registry_model.get_repo_tag(repository_ref, tagname)
    return registry_model.get_manifest_for_tag(tag)


@pytest.fixture()
def api():
    assert app is not None
    retriever = BlobURLRetriever(storage, instance_keys, app)
    return ClairSecurityScannerAPI(
        "http://fakesecurityscanner", build_requests_session(), retriever
    )


def test_state(api, initialized_db):
    with fake_security_scanner() as security_scanner:
        resp = api.state()

        assert resp["state"] == security_scanner.indexer_state


def test_state_incompatible_response(api, initialized_db):
    with fake_security_scanner(incompatible=True) as security_scanner:
        with pytest.raises(APIRequestFailure):
            api.state()


def test_index_report(api, initialized_db):
    with fake_security_scanner() as security_scanner:
        manifest = manifest_for("devtable", "simple", "latest")
        layers = registry_model.list_manifest_layers(manifest, storage, True)

        assert manifest.digest not in security_scanner.index_reports.keys()
        assert api.index_report(manifest.digest) is None

        (report, state) = api.index(manifest, layers)

        assert report is not None
        assert manifest.digest in security_scanner.index_reports.keys()

        index_report = api.index_report(manifest.digest)

        assert report == index_report


def test_index_incompatible_api_response(api, initialized_db):
    with fake_security_scanner(incompatible=True) as security_scanner:
        with pytest.raises(APIRequestFailure):
            manifest = manifest_for("devtable", "simple", "latest")
            layers = registry_model.list_manifest_layers(manifest, storage, True)

            api.index(manifest, layers)


def test_index_report_incompatible_api_response(api, initialized_db):
    with fake_security_scanner(incompatible=True) as security_scanner:
        with pytest.raises(APIRequestFailure):
            manifest = manifest_for("devtable", "simple", "latest")

            api.index_report(manifest.digest)


def test_vulnerability_report(api, initialized_db):
    with fake_security_scanner() as security_scanner:
        manifest = manifest_for("devtable", "simple", "latest")
        layers = registry_model.list_manifest_layers(manifest, storage, True)

        assert manifest.digest not in security_scanner.index_reports.keys()
        assert api.vulnerability_report(manifest.digest) is None

        api.index(manifest, layers)
        report = api.vulnerability_report(manifest.digest)

        assert manifest.digest in security_scanner.vulnerability_reports.keys()
        assert report is not None


def test_vulnerability_report_incompatible_api_response(api, initialized_db):
    with fake_security_scanner(incompatible=True) as security_scanner:
        with pytest.raises(APIRequestFailure):
            manifest = manifest_for("devtable", "simple", "latest")
            layers = registry_model.list_manifest_layers(manifest, storage, True)

            api.vulnerability_report(manifest.digest)
