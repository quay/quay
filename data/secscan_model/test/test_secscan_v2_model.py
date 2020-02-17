from data.secscan_model.datatypes import ScanLookupStatus
from data.secscan_model.secscan_v2_model import V2SecurityScanner
from data.registry_model import registry_model
from data.registry_model.datatypes import SecurityScanStatus
from data.database import Manifest
from data.model.oci import shared

from test.fixtures import *

from app import app, instance_keys, storage


def test_load_security_information_unknown_manifest(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(tag, backfill_if_necessary=True)

    # Delete the manifest.
    Manifest.get(id=manifest._db_id).delete_instance(recursive=True)

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert (
        secscan.load_security_information(manifest).status
        == ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
    )


def test_load_security_information_failed_to_index(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(tag, backfill_if_necessary=True)

    # Set the index status.
    image = shared.get_legacy_image_for_manifest(manifest._db_id)
    image.security_indexed = False
    image.security_indexed_engine = 3
    image.save()

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.FAILED_TO_INDEX


def test_load_security_information_queued(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(tag, backfill_if_necessary=True)

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.NOT_YET_INDEXED
