import base64

import pytest

from data.registry_model import registry_model
from endpoints.test.shared import gen_basic_auth
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.secscan import RepositoryImageSecurity, RepositoryManifestSecurity

from test.fixtures import *


@pytest.mark.parametrize(
    "endpoint",
    [
        RepositoryImageSecurity,
        RepositoryManifestSecurity,
    ],
)
def test_get_security_info_with_pull_secret(endpoint, client):
    repository_ref = registry_model.lookup_repository("devtable", "simple")
    tag = registry_model.get_repo_tag(repository_ref, "latest")
    manifest = registry_model.get_manifest_for_tag(tag)

    params = {
        "repository": "devtable/simple",
        "imageid": tag.manifest.legacy_image_root_id,
        "manifestref": manifest.digest,
    }

    headers = {
        "Authorization": gen_basic_auth("devtable", "password"),
    }

    conduct_api_call(client, endpoint, "GET", params, None, headers=headers, expected_code=200)
