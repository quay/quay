from unittest.mock import MagicMock, Mock, patch

import pytest

from endpoints.api.manifest import RepositoryManifestPullStatistics
from endpoints.api.tag import RepositoryTagPullStatistics


class TestRepositoryTagPullStatistics:
    """Test cases for tag pull statistics API endpoint."""

    def test_get_tag_pull_statistics_feature_disabled(self):
        """Test that endpoint returns 404 when feature is disabled."""
        with patch("endpoints.api.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = False

            endpoint = RepositoryTagPullStatistics()
            with pytest.raises(Exception) as exc_info:
                endpoint.get("namespace", "repo", "tag")

            assert "Image pull statistics feature is not enabled" in str(exc_info.value)

    @patch("endpoints.api.tag.registry_model")
    @patch("endpoints.api.tag.app")
    def test_get_tag_pull_statistics_success(self, mock_app, mock_registry_model):
        """Test successful retrieval of tag pull statistics."""
        # Mock feature flag
        with patch("endpoints.api.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Mock repository and tag lookup
            mock_repo_ref = Mock()
            mock_tag_ref = Mock()
            mock_tag_ref.manifest_digest = "sha256:abc123"
            mock_registry_model.lookup_repository.return_value = mock_repo_ref
            mock_registry_model.get_repo_tag.return_value = mock_tag_ref

            # Mock pull metrics
            mock_pull_metrics = Mock()
            mock_pull_metrics.get_tag_pull_statistics.return_value = {
                "pull_count": 5,
                "last_pull_date": "2024-01-01T10:00:00Z",
                "current_manifest_digest": "sha256:abc123",
            }
            mock_pull_metrics.get_manifest_pull_statistics.return_value = {
                "pull_count": 10,
                "last_pull_date": "2024-01-01T10:00:00Z",
            }
            mock_app.extensions = {"pullmetrics": mock_pull_metrics}

            endpoint = RepositoryTagPullStatistics()
            result = endpoint.get("namespace", "repo", "tag")

            assert result["tag_name"] == "tag"
            assert result["tag_pull_count"] == 5
            assert result["last_tag_pull_date"] == "2024-01-01T10:00:00Z"
            assert result["current_manifest_digest"] == "sha256:abc123"
            assert result["manifest_pull_count"] == 10
            assert result["last_manifest_pull_date"] == "2024-01-01T10:00:00Z"

    @patch("endpoints.api.tag.registry_model")
    @patch("endpoints.api.tag.app")
    def test_get_tag_pull_statistics_no_data(self, mock_app, mock_registry_model):
        """Test tag pull statistics when no data is available."""
        # Mock feature flag
        with patch("endpoints.api.tag.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Mock repository and tag lookup
            mock_repo_ref = Mock()
            mock_tag_ref = Mock()
            mock_tag_ref.manifest_digest = "sha256:abc123"
            mock_registry_model.lookup_repository.return_value = mock_repo_ref
            mock_registry_model.get_repo_tag.return_value = mock_tag_ref

            # Mock pull metrics with no data
            mock_pull_metrics = Mock()
            mock_pull_metrics.get_tag_pull_statistics.return_value = None
            mock_app.extensions = {"pullmetrics": mock_pull_metrics}

            endpoint = RepositoryTagPullStatistics()
            result = endpoint.get("namespace", "repo", "tag")

            assert result["tag_name"] == "tag"
            assert result["tag_pull_count"] == 0
            assert result["last_tag_pull_date"] is None
            assert result["current_manifest_digest"] == "sha256:abc123"
            assert result["manifest_pull_count"] == 0
            assert result["last_manifest_pull_date"] is None


class TestRepositoryManifestPullStatistics:
    """Test cases for manifest pull statistics API endpoint."""

    def test_get_manifest_pull_statistics_feature_disabled(self):
        """Test that endpoint returns 404 when feature is disabled."""
        with patch("endpoints.api.manifest.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = False

            endpoint = RepositoryManifestPullStatistics()
            with pytest.raises(Exception) as exc_info:
                endpoint.get("namespace", "repo", "sha256:abc123")

            assert "Image pull statistics feature is not enabled" in str(exc_info.value)

    @patch("endpoints.api.manifest.registry_model")
    @patch("endpoints.api.manifest.app")
    def test_get_manifest_pull_statistics_success(self, mock_app, mock_registry_model):
        """Test successful retrieval of manifest pull statistics."""
        # Mock feature flag
        with patch("endpoints.api.manifest.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Mock repository and manifest lookup
            mock_repo_ref = Mock()
            mock_manifest = Mock()
            mock_registry_model.lookup_repository.return_value = mock_repo_ref
            mock_registry_model.lookup_manifest_by_digest.return_value = mock_manifest

            # Mock pull metrics
            mock_pull_metrics = Mock()
            mock_pull_metrics.get_manifest_pull_statistics.return_value = {
                "pull_count": 15,
                "last_pull_date": "2024-01-01T10:00:00Z",
            }
            mock_app.extensions = {"pullmetrics": mock_pull_metrics}

            endpoint = RepositoryManifestPullStatistics()
            result = endpoint.get("namespace", "repo", "sha256:abc123")

            assert result["manifest_digest"] == "sha256:abc123"
            assert result["manifest_pull_count"] == 15
            assert result["last_manifest_pull_date"] == "2024-01-01T10:00:00Z"

    @patch("endpoints.api.manifest.registry_model")
    @patch("endpoints.api.manifest.app")
    def test_get_manifest_pull_statistics_no_data(self, mock_app, mock_registry_model):
        """Test manifest pull statistics when no data is available."""
        # Mock feature flag
        with patch("endpoints.api.manifest.features") as mock_features:
            mock_features.IMAGE_PULL_STATS = True

            # Mock repository and manifest lookup
            mock_repo_ref = Mock()
            mock_manifest = Mock()
            mock_registry_model.lookup_repository.return_value = mock_repo_ref
            mock_registry_model.lookup_manifest_by_digest.return_value = mock_manifest

            # Mock pull metrics with no data
            mock_pull_metrics = Mock()
            mock_pull_metrics.get_manifest_pull_statistics.return_value = None
            mock_app.extensions = {"pullmetrics": mock_pull_metrics}

            endpoint = RepositoryManifestPullStatistics()
            result = endpoint.get("namespace", "repo", "sha256:abc123")

            assert result["manifest_digest"] == "sha256:abc123"
            assert result["manifest_pull_count"] == 0
            assert result["last_manifest_pull_date"] is None
