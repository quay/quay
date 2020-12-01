import base64

import pytest
from mock import patch

from data.registry_model import registry_model
from endpoints.test.shared import gen_basic_auth
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.secscan import RepositoryImageSecurity, RepositoryManifestSecurity

from test.fixtures import *


@pytest.mark.parametrize(
    "endpoint, anonymous_allowed, auth_headers, expected_code",
    [
        pytest.param(RepositoryImageSecurity, True, gen_basic_auth("devtable", "password"), 200),
        pytest.param(RepositoryImageSecurity, False, gen_basic_auth("devtable", "password"), 200),
        pytest.param(RepositoryManifestSecurity, True, gen_basic_auth("devtable", "password"), 200),
        pytest.param(
            RepositoryManifestSecurity, False, gen_basic_auth("devtable", "password"), 200
        ),
        pytest.param(RepositoryImageSecurity, True, None, 401),
        pytest.param(RepositoryImageSecurity, False, None, 401),
        pytest.param(RepositoryManifestSecurity, True, None, 401),
        pytest.param(RepositoryManifestSecurity, False, None, 401),
    ],
)
def test_get_security_info_with_pull_secret(
    endpoint, anonymous_allowed, auth_headers, expected_code, client
):
    with patch("features.ANONYMOUS_ACCESS", anonymous_allowed):
        repository_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repository_ref, "latest")
        manifest = registry_model.get_manifest_for_tag(tag)

        params = {
            "repository": "devtable/simple",
            "imageid": tag.manifest.legacy_image_root_id,
            "manifestref": manifest.digest,
        }

        headers = {}
        if auth_headers is not None:
            headers["Authorization"] = auth_headers

        conduct_api_call(
            client, endpoint, "GET", params, None, headers=headers, expected_code=expected_code
        )
