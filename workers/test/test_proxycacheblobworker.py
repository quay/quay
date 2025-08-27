from unittest.mock import MagicMock, patch

import pytest

from data.model.organization import create_organization
from data.model.proxy_cache import create_proxy_cache_config
from data.model.repository import create_repository
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


def test_process_queue_item_with_none_username(proxy_cache_blob_worker, initialized_db):
    """Test that worker handles None username for public repositories (PROJQUAY-9346)"""

    # Setup test data
    orgname = "testorg"
    user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", user)
    org.save()

    # Create proxy cache config for the organization
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )

    # Create a test repository
    repo = create_repository(orgname, "test_repo", user)

    # Create job details with None username (public repository scenario)
    job_details = {
        "repo_id": repo.id,
        "namespace": orgname,
        "digest": "sha256:test_digest",
        "username": None,  # This simulates public repository access
    }

    # Mock the _should_download_blob method to return False so we don't actually download
    with patch.object(proxy_cache_blob_worker, "_should_download_blob", return_value=False):
        # This should not raise an exception
        proxy_cache_blob_worker.process_queue_item(job_details)


def test_process_queue_item_with_username(proxy_cache_blob_worker, initialized_db):
    """Test that worker handles normal username case correctly"""
    from data.model.organization import create_organization
    from data.model.proxy_cache import create_proxy_cache_config
    from data.model.repository import create_repository
    from data.model.user import create_user_noverify, get_user

    # Setup test data
    orgname = "testorg2"
    admin_user = get_user("devtable")
    org = create_organization(orgname, f"{orgname}@devtable.com", admin_user)
    org.save()

    # Create proxy cache config for the organization
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )

    # Create a test repository
    repo = create_repository(orgname, "test_repo", admin_user)

    # Create a test user
    test_user = create_user_noverify("testuser", "testuser@example.com")

    # Create job details with actual username
    job_details = {
        "repo_id": repo.id,
        "namespace": orgname,
        "digest": "sha256:test_digest",
        "username": "testuser",
    }

    # Mock the _should_download_blob method to return False so we don't actually download
    with patch.object(proxy_cache_blob_worker, "_should_download_blob", return_value=False):
        # This should work normally
        proxy_cache_blob_worker.process_queue_item(job_details)
