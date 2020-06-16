import mock
import pytest

from data.secscan_model.datatypes import ScanLookupStatus, SecurityInformation
from data.secscan_model.secscan_v2_model import V2SecurityScanner
from data.registry_model import registry_model
from data.database import Manifest, Image, ManifestSecurityStatus, IndexStatus, IndexerVersion
from data.model.oci import shared
from data.model.image import set_secscan_status

from test.fixtures import *

from app import app, instance_keys, storage


def test_load_security_information_unknown_manifest(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    registry_model.populate_legacy_images_for_testing(manifest, storage)

    # Delete the manifest.
    Manifest.get(id=manifest._db_id).delete_instance(recursive=True)

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert (
        secscan.load_security_information(manifest).status
        == ScanLookupStatus.UNSUPPORTED_FOR_INDEXING
    )


def test_load_security_information_failed_to_index(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    registry_model.populate_legacy_images_for_testing(manifest, storage)

    # Set the index status.
    image = shared.get_legacy_image_for_manifest(manifest._db_id)
    image.security_indexed = False
    image.security_indexed_engine = 3
    image.save()

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.FAILED_TO_INDEX


def test_load_security_information_queued(initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    registry_model.populate_legacy_images_for_testing(manifest, storage)

    secscan = V2SecurityScanner(app, instance_keys, storage)
    assert secscan.load_security_information(manifest).status == ScanLookupStatus.NOT_YET_INDEXED


@pytest.mark.parametrize(
    "secscan_api_response",
    [
        ({"Layer": {}}),
        (
            {
                "Layer": {
                    "IndexedByVersion": 3,
                    "ParentName": "9c6afaebf33df8db2e3f38f95c402d82e025386730f6a8cbe0b780a6053cdd11.d4b545b4-49ce-4bc4-8bbe-b58bed7bddd9",
                    "Name": "ed209f9bdb3766c3da8a004a72e3a30901bde36c39466a3825af1cd12894e7a3.86f0a285-6f29-47c4-a3ae-7e2c70cad0ba",
                }
            }
        ),
        (
            {
                "Layer": {
                    "IndexedByVersion": 3,
                    "ParentName": "9c6afaebf33df8db2e3f38f95c402d82e025386730f6a8cbe0b780a6053cdd11.d4b545b4-49ce-4bc4-8bbe-b58bed7bddd9",
                    "Name": "ed209f9bdb3766c3da8a004a72e3a30901bde36c39466a3825af1cd12894e7a3.86f0a285-6f29-47c4-a3ae-7e2c70cad0ba",
                    "Features": [
                        {
                            "Name": "tzdata",
                            "VersionFormat": "",
                            "NamespaceName": "",
                            "AddedBy": "sha256:8d691f585fa8cec0eba196be460cfaffd69939782d6162986c3e0c5225d54f02",
                            "Version": "2019c-0+deb10u1",
                        }
                    ],
                }
            }
        ),
    ],
)
def test_load_security_information_api_responses(secscan_api_response, initialized_db):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    registry_model.populate_legacy_images_for_testing(manifest, storage)

    legacy_image_row = shared.get_legacy_image_for_manifest(manifest._db_id)
    assert legacy_image_row is not None
    set_secscan_status(legacy_image_row, True, 3)

    secscan = V2SecurityScanner(app, instance_keys, storage)
    secscan._legacy_secscan_api = mock.Mock()
    secscan._legacy_secscan_api.get_layer_data.return_value = secscan_api_response

    security_information = secscan.load_security_information(manifest).security_information

    assert isinstance(security_information, SecurityInformation)
    assert security_information.Layer.Name == secscan_api_response["Layer"].get("Name", "")
    assert security_information.Layer.ParentName == secscan_api_response["Layer"].get(
        "ParentName", ""
    )
    assert security_information.Layer.IndexedByVersion == secscan_api_response["Layer"].get(
        "IndexedByVersion", None
    )
    assert len(security_information.Layer.Features) == len(
        secscan_api_response["Layer"].get("Features", [])
    )


def test_perform_indexing(initialized_db):
    secscan = V2SecurityScanner(app, instance_keys, storage)

    with pytest.raises(NotImplementedError):
        secscan.perform_indexing()
