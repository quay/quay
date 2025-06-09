from unittest.mock import MagicMock, patch

import pytest

from data.model.organization import create_organization
from data.model.proxy_cache import create_proxy_cache_config
from data.model.user import get_user
from data.registry_model.registry_proxy_model import ProxyModel
from test.fixtures import *
from workers.proxycacheblobworker import ProxyCacheBlobWorker


@pytest.fixture()
def proxy_cache_blob_worker():
    return ProxyCacheBlobWorker(None)


@pytest.fixture()
@patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
def registry_proxy_model(initialized_db):
    orgname = "testorg"
    user = get_user("devtable")
    org = create_organization(orgname, "{self.orgname}@devtable.com", user)
    org.save()
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )
    return ProxyModel(
        orgname,
        "app-sre/ubi8-ubi",
        user,
    )


def test_proxy_cache_blob_download(proxy_cache_blob_worker, registry_proxy_model, app):
    # ImageStorage(placeholder) does not exist
    assert not proxy_cache_blob_worker._should_download_blob(
        "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
        1,
        registry_proxy_model,
    )
