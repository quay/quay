from data.secscan_model.datatypes import ScanLookupStatus
from data.secscan_model.secscan_v2_model import V2SecurityScanner
from data.secscan_model.secscan_v4_model import V4SecurityScanner
from data.registry_model import registry_model

from test.fixtures import *

from app import app, instance_keys, storage


@pytest.fixture(params=[V2SecurityScanner, V4SecurityScanner])
def secscan_model(request, initialized_db):
    return request.param(app, instance_keys, storage)


def test_load_security_information(secscan_model):
    repository = registry_model.lookup_repository("devtable", "complex")
    for tag in registry_model.list_all_active_repository_tags(repository):
        manifest = registry_model.get_manifest_for_tag(tag)
        assert manifest
        assert (
            secscan_model.load_security_information(manifest, True).status
            == ScanLookupStatus.NOT_YET_INDEXED
        )


def test_perform_indexing(secscan_model):
    next_token = secscan_model.perform_indexing()
    assert next_token is not None

    next_token = secscan_model.perform_indexing(next_token)
    assert next_token is None
