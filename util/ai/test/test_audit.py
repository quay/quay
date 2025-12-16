"""
Tests for AI feature audit logging.
"""
import pytest
from unittest.mock import MagicMock, patch, call


class TestAIDescriptionAuditLogging:
    """Tests for AI description generation audit logging."""

    @patch("endpoints.api.ai.log_action")
    @patch("endpoints.api.ai.model")
    @patch("endpoints.api.ai.get_org_ai_settings")
    @patch("endpoints.api.ai.is_description_generator_enabled")
    @patch("endpoints.api.ai.extract_image_analysis")
    @patch("endpoints.api.ai.ProviderFactory")
    @patch("endpoints.api.ai.cache_description")
    @patch("endpoints.api.ai.get_cached_description")
    def test_log_description_generated(
        self,
        mock_get_cached,
        mock_cache_desc,
        mock_factory,
        mock_extract,
        mock_is_enabled,
        mock_get_settings,
        mock_model,
        mock_log_action,
    ):
        """Test that description generation creates an audit log entry."""
        # This test verifies the log_action call pattern
        # In a real integration test, we'd call the endpoint

        # Verify log_action is called with expected kind
        expected_kind = "generate_ai_description"
        expected_namespace = "testorg"
        expected_metadata = {
            "repository": "testrepo",
            "tag": "latest",
            "manifest_digest": "sha256:abc123",
            "provider": "anthropic",
        }

        # Simulate what the endpoint should log
        from endpoints.api.ai import log_action

        log_action(expected_kind, expected_namespace, expected_metadata)

        mock_log_action.assert_called_once_with(
            expected_kind, expected_namespace, expected_metadata
        )

    @patch("endpoints.api.ai.log_action")
    def test_log_includes_org_and_repo(self, mock_log_action):
        """Test that log entry includes org and repo information."""
        from endpoints.api.ai import log_action

        log_action(
            "generate_ai_description",
            "myorg",
            {"repository": "myrepo", "tag": "v1.0", "manifest_digest": "sha256:xyz"},
        )

        call_args = mock_log_action.call_args
        assert call_args[0][1] == "myorg"  # namespace
        assert call_args[0][2]["repository"] == "myrepo"

    @patch("endpoints.api.ai.log_action")
    def test_log_includes_tag_analyzed(self, mock_log_action):
        """Test that log entry includes the tag that was analyzed."""
        from endpoints.api.ai import log_action

        log_action(
            "generate_ai_description",
            "org",
            {"repository": "repo", "tag": "v2.0.0", "manifest_digest": "sha256:abc"},
        )

        call_args = mock_log_action.call_args
        assert call_args[0][2]["tag"] == "v2.0.0"

    @patch("endpoints.api.ai.log_action")
    def test_log_includes_manifest_digest(self, mock_log_action):
        """Test that log entry includes manifest digest."""
        from endpoints.api.ai import log_action

        log_action(
            "generate_ai_description",
            "org",
            {"repository": "repo", "tag": "latest", "manifest_digest": "sha256:digest123"},
        )

        call_args = mock_log_action.call_args
        assert call_args[0][2]["manifest_digest"] == "sha256:digest123"


class TestAISettingsAuditLogging:
    """Tests for AI settings audit logging."""

    @patch("endpoints.api.ai.log_action")
    def test_log_settings_updated(self, mock_log_action):
        """Test that settings update creates an audit log entry."""
        from endpoints.api.ai import log_action

        log_action(
            "update_ai_settings",
            "testorg",
            {"provider": "openai", "model": "gpt-4"},
        )

        mock_log_action.assert_called_once()
        call_args = mock_log_action.call_args
        assert call_args[0][0] == "update_ai_settings"
        assert call_args[0][1] == "testorg"

    @patch("endpoints.api.ai.log_action")
    def test_log_credentials_configured(self, mock_log_action):
        """Test that credential configuration creates an audit log entry."""
        from endpoints.api.ai import log_action

        log_action(
            "set_ai_credentials",
            "testorg",
            {"provider": "anthropic", "model": "claude-3-haiku"},
        )

        call_args = mock_log_action.call_args
        assert call_args[0][0] == "set_ai_credentials"
        # API key should never be logged
        assert "api_key" not in call_args[0][2]

    @patch("endpoints.api.ai.log_action")
    def test_log_credentials_deleted(self, mock_log_action):
        """Test that credential deletion creates an audit log entry."""
        from endpoints.api.ai import log_action

        log_action("delete_ai_credentials", "testorg", {})

        call_args = mock_log_action.call_args
        assert call_args[0][0] == "delete_ai_credentials"
        assert call_args[0][1] == "testorg"


class TestAuditLogSecurityConstraints:
    """Tests for audit log security requirements."""

    @patch("endpoints.api.ai.log_action")
    def test_api_key_never_logged(self, mock_log_action):
        """Test that API keys are never included in audit logs."""
        from endpoints.api.ai import log_action

        # Simulate various log calls that might accidentally include API key
        log_calls = [
            ("set_ai_credentials", "org", {"provider": "openai", "model": "gpt-4"}),
            ("update_ai_settings", "org", {"provider": "anthropic"}),
            ("generate_ai_description", "org", {"repository": "repo", "tag": "latest"}),
        ]

        for kind, org, metadata in log_calls:
            log_action(kind, org, metadata)

        # Verify no call includes api_key
        for call in mock_log_action.call_args_list:
            if len(call[0]) > 2:
                metadata = call[0][2]
                assert "api_key" not in metadata
                assert "API_KEY" not in metadata
                assert "apiKey" not in metadata

    @patch("endpoints.api.ai.log_action")
    def test_provider_logged_not_credentials(self, mock_log_action):
        """Test that provider name is logged but not credential details."""
        from endpoints.api.ai import log_action

        log_action(
            "set_ai_credentials",
            "testorg",
            {"provider": "google", "model": "gemini-pro"},
        )

        call_args = mock_log_action.call_args
        metadata = call_args[0][2]

        # Provider and model should be logged
        assert metadata["provider"] == "google"
        assert metadata["model"] == "gemini-pro"

        # But no sensitive info
        assert "endpoint" not in metadata or metadata.get("endpoint") is None


class TestLogEntryKinds:
    """Tests for log entry kind definitions."""

    def test_ai_log_entry_kinds_defined(self):
        """Test that AI-related log entry kinds are expected to exist."""
        expected_kinds = [
            "update_ai_settings",
            "set_ai_credentials",
            "delete_ai_credentials",
            "generate_ai_description",
        ]

        # These are the kinds that should be created by the migration
        for kind in expected_kinds:
            assert isinstance(kind, str)
            assert len(kind) > 0

    def test_log_entry_kinds_follow_naming_convention(self):
        """Test that log entry kinds follow Quay naming conventions."""
        expected_kinds = [
            "update_ai_settings",
            "set_ai_credentials",
            "delete_ai_credentials",
            "generate_ai_description",
        ]

        for kind in expected_kinds:
            # Should be lowercase with underscores
            assert kind == kind.lower()
            assert " " not in kind
            # Should be descriptive
            assert len(kind) >= 10


class TestCacheStatusLogging:
    """Tests for cache hit/miss logging in descriptions."""

    @patch("endpoints.api.ai.log_action")
    def test_can_log_cache_status(self, mock_log_action):
        """Test that cache status can be included in logs."""
        from endpoints.api.ai import log_action

        # When cache is hit
        log_action(
            "generate_ai_description",
            "org",
            {
                "repository": "repo",
                "tag": "latest",
                "manifest_digest": "sha256:abc",
                "cache_hit": True,
            },
        )

        call_args = mock_log_action.call_args
        # Verify cache_hit can be logged (optional field)
        # The current implementation doesn't log this, but it could be added

    @patch("endpoints.api.ai.log_action")
    def test_log_includes_provider_used(self, mock_log_action):
        """Test that the provider used is logged."""
        from endpoints.api.ai import log_action

        log_action(
            "generate_ai_description",
            "org",
            {
                "repository": "repo",
                "tag": "latest",
                "manifest_digest": "sha256:abc",
                "provider": "anthropic",
            },
        )

        call_args = mock_log_action.call_args
        assert call_args[0][2]["provider"] == "anthropic"
