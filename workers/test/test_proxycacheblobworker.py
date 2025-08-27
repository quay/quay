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


@patch("data.model.repository.lookup_repository")
@patch("data.registry_model.datatypes.RepositoryReference.for_id")
@patch("data.registry_model.registry_proxy_model.ProxyModel")
def test_process_queue_item_with_none_username(
    mock_proxy_model, mock_repo_ref, mock_lookup_repo, proxy_cache_blob_worker
):
    """Test that worker handles None username for public repositories (PROJQUAY-9346)"""
    # Setup mocks
    mock_repo = MagicMock()
    mock_repo.name = "test_repo"
    mock_lookup_repo.return_value = mock_repo
    mock_repo_ref.return_value = MagicMock()

    mock_proxy_instance = MagicMock()
    mock_proxy_model.return_value = mock_proxy_instance
    mock_proxy_instance._should_download_blob = MagicMock(return_value=False)

    # Create job details with None username (public repository scenario)
    job_details = {
        "repo_id": 123,
        "namespace": "test_namespace",
        "digest": "sha256:test_digest",
        "username": None,  # This simulates public repository access
    }

    # This should not raise an exception
    with patch("data.model.user.get_username") as mock_get_username:
        proxy_cache_blob_worker.process_queue_item(job_details)

        # user.get_username should not be called when username is None
        mock_get_username.assert_not_called()

        # ProxyModel should be created with None user
        mock_proxy_model.assert_called_once_with(
            "test_namespace", "test_repo", None  # user_ref should be None
        )


@patch("data.model.repository.lookup_repository")
@patch("data.registry_model.datatypes.RepositoryReference.for_id")
@patch("data.model.user.get_username")
@patch("data.registry_model.registry_proxy_model.ProxyModel")
def test_process_queue_item_with_username(
    mock_proxy_model, mock_get_username, mock_repo_ref, mock_lookup_repo, proxy_cache_blob_worker
):
    """Test that worker handles normal username case correctly"""
    # Setup mocks
    mock_repo = MagicMock()
    mock_repo.name = "test_repo"
    mock_lookup_repo.return_value = mock_repo
    mock_repo_ref.return_value = MagicMock()

    mock_user = MagicMock()
    mock_get_username.return_value = mock_user

    mock_proxy_instance = MagicMock()
    mock_proxy_model.return_value = mock_proxy_instance
    mock_proxy_instance._should_download_blob = MagicMock(return_value=False)

    # Create job details with actual username
    job_details = {
        "repo_id": 123,
        "namespace": "test_namespace",
        "digest": "sha256:test_digest",
        "username": "testuser",
    }

    # This should work normally
    proxy_cache_blob_worker.process_queue_item(job_details)

    # user.get_username should be called with the username
    mock_get_username.assert_called_once_with("testuser")

    # ProxyModel should be created with the user
    mock_proxy_model.assert_called_once_with("test_namespace", "test_repo", mock_user)
