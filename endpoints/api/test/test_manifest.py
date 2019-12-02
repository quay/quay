from data.registry_model import registry_model
from endpoints.api.manifest import RepositoryManifest
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity

from test.fixtures import *


def test_repository_manifest(client):
    with client_with_identity("devtable", client) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tags = registry_model.list_all_active_repository_tags(repo_ref)
        for tag in tags:
            manifest_digest = tag.manifest_digest
            if manifest_digest is None:
                continue

            params = {
                "repository": "devtable/simple",
                "manifestref": manifest_digest,
            }
            result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
            assert result["digest"] == manifest_digest
            assert result["manifest_data"]
            assert result["image"]
