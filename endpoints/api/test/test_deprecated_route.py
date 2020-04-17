import pytest

from data import model
from data.model.oci import shared
from data.registry_model import registry_model
from endpoints.api.secscan import RepositoryImageSecurity
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def test_deprecated_route(client):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest", include_legacy_image=True)
    manifest = registry_model.get_manifest_for_tag(tag, backfill_if_necessary=True)
    image = shared.get_legacy_image_for_manifest(manifest._db_id)

    with client_with_identity("devtable", client) as cl:
        resp = conduct_api_call(
            cl,
            RepositoryImageSecurity,
            "get",
            {"repository": "devtable/simple", "imageid": image.docker_image_id},
            expected_code=200,
        )

        assert resp.headers["Deprecation"] == "true"
