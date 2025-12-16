"""
Tests for OrganizationAISettings model operations.
"""
from datetime import datetime, timedelta

import pytest
from mock import patch

from data import model
from data.database import OrganizationAISettings
from data.model import InvalidOrganizationException
from data.model.organization import get_organization
from data.model.organization_ai import (
    create_or_update_org_ai_settings,
    delete_org_ai_settings,
    get_org_ai_settings,
    is_description_generator_enabled,
    mark_credentials_verified,
    set_org_ai_credentials,
    toggle_description_generator,
)
from test.fixtures import *


class TestOrganizationAISettingsCRUD:
    """Tests for basic CRUD operations on OrganizationAISettings."""

    def test_create_org_ai_settings(self, initialized_db):
        """Test creating new AI settings for an organization."""
        org = get_organization("buynlarge")

        settings = create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=True,
        )

        assert settings is not None
        assert settings.organization == org
        assert settings.description_generator_enabled is True
        assert settings.provider is None
        assert settings.credentials_verified is False

    def test_update_org_ai_settings(self, initialized_db):
        """Test updating existing AI settings."""
        org = get_organization("buynlarge")

        # Create initial settings
        settings = create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=False,
        )
        assert settings.description_generator_enabled is False

        # Update settings
        updated = create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=True,
            provider="anthropic",
            model="claude-3-haiku",
        )

        assert updated.id == settings.id  # Same record updated
        assert updated.description_generator_enabled is True
        assert updated.provider == "anthropic"
        assert updated.model == "claude-3-haiku"

    def test_get_org_ai_settings_returns_none_for_unconfigured(self, initialized_db):
        """Test that get returns None for orgs without AI settings."""
        org = get_organization("sellnsmall")

        settings = get_org_ai_settings(org.username)

        assert settings is None

    def test_get_org_ai_settings_returns_settings(self, initialized_db):
        """Test retrieving existing AI settings."""
        org = get_organization("buynlarge")

        # Create settings first
        create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=True,
            provider="openai",
        )

        # Retrieve them
        settings = get_org_ai_settings(org.username)

        assert settings is not None
        assert settings.provider == "openai"

    def test_delete_org_ai_settings(self, initialized_db):
        """Test deleting AI settings."""
        org = get_organization("buynlarge")

        # Create settings
        create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=True,
        )
        assert get_org_ai_settings(org.username) is not None

        # Delete settings
        result = delete_org_ai_settings(org.username)

        assert result is True
        assert get_org_ai_settings(org.username) is None

    def test_delete_org_ai_settings_nonexistent(self, initialized_db):
        """Test deleting non-existent settings returns False."""
        org = get_organization("sellnsmall")

        result = delete_org_ai_settings(org.username)

        assert result is False

    def test_settings_isolated_per_org(self, initialized_db):
        """Test that AI settings are isolated between organizations."""
        org1 = get_organization("buynlarge")
        org2 = get_organization("sellnsmall")

        # Create settings for org1
        create_or_update_org_ai_settings(
            org1.username,
            description_generator_enabled=True,
            provider="anthropic",
        )

        # Create settings for org2
        create_or_update_org_ai_settings(
            org2.username,
            description_generator_enabled=False,
            provider="openai",
        )

        # Verify isolation
        settings1 = get_org_ai_settings(org1.username)
        settings2 = get_org_ai_settings(org2.username)

        assert settings1.provider == "anthropic"
        assert settings1.description_generator_enabled is True
        assert settings2.provider == "openai"
        assert settings2.description_generator_enabled is False


class TestAPIKeyEncryption:
    """Tests for API key encryption and storage."""

    def test_api_key_stored_encrypted(self, initialized_db):
        """Test that API keys are stored encrypted in the database."""
        org = get_organization("buynlarge")
        api_key = "sk-test-key-12345"

        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key=api_key,
            model="claude-3-haiku",
        )

        # Get raw database record
        settings = OrganizationAISettings.get(OrganizationAISettings.organization == org)

        # The raw value should not be the plaintext key
        # EncryptedTextField stores versioned encrypted data
        assert settings.api_key_encrypted is not None
        raw_value = settings.api_key_encrypted
        # Check it's not plaintext (encrypted values start with version prefix)
        assert api_key not in str(raw_value) or "$$" in str(raw_value)

    def test_api_key_decryption(self, initialized_db):
        """Test that API keys can be decrypted when retrieved."""
        org = get_organization("buynlarge")
        api_key = "sk-test-key-67890"

        set_org_ai_credentials(
            org.username,
            provider="openai",
            api_key=api_key,
            model="gpt-4",
        )

        settings = get_org_ai_settings(org.username)

        # The decrypted value should match (use .matches() for encrypted fields)
        assert settings.api_key_encrypted.matches(api_key)

    def test_api_key_updated_on_change(self, initialized_db):
        """Test that API key is properly updated when changed."""
        org = get_organization("buynlarge")

        # Set initial key
        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="old-key",
            model="claude-3-haiku",
        )

        # Update with new key
        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="new-key",
            model="claude-3-haiku",
        )

        settings = get_org_ai_settings(org.username)
        assert settings.api_key_encrypted.matches("new-key")


class TestCredentialsVerification:
    """Tests for credential verification status."""

    def test_mark_credentials_verified(self, initialized_db):
        """Test marking credentials as verified."""
        org = get_organization("buynlarge")

        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku",
        )

        # Initially not verified
        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is False

        # Mark as verified
        mark_credentials_verified(org.username, verified=True)

        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is True
        assert settings.credentials_verified_at is not None

    def test_mark_credentials_unverified(self, initialized_db):
        """Test marking credentials as unverified."""
        org = get_organization("buynlarge")

        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku",
        )
        mark_credentials_verified(org.username, verified=True)

        # Mark as unverified
        mark_credentials_verified(org.username, verified=False)

        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is False

    def test_mark_credentials_unverified_on_key_change(self, initialized_db):
        """Test that changing API key resets verification status."""
        org = get_organization("buynlarge")

        # Set credentials and verify
        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="original-key",
            model="claude-3-haiku",
        )
        mark_credentials_verified(org.username, verified=True)

        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is True

        # Change the API key
        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="new-key",
            model="claude-3-haiku",
        )

        # Verification should be reset
        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is False

    def test_mark_credentials_unverified_on_provider_change(self, initialized_db):
        """Test that changing provider resets verification status."""
        org = get_organization("buynlarge")

        # Set credentials and verify
        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku",
        )
        mark_credentials_verified(org.username, verified=True)

        # Change provider (keeps same key)
        set_org_ai_credentials(
            org.username,
            provider="openai",
            api_key="test-key",
            model="gpt-4",
        )

        settings = get_org_ai_settings(org.username)
        assert settings.credentials_verified is False


class TestFeatureToggles:
    """Tests for AI feature toggle operations."""

    def test_enable_ai_description_generator(self, initialized_db):
        """Test enabling the description generator feature."""
        org = get_organization("buynlarge")

        # Create settings with feature disabled
        create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=False,
        )

        # Enable the feature
        toggle_description_generator(org.username, enabled=True)

        assert is_description_generator_enabled(org.username) is True

    def test_disable_ai_description_generator(self, initialized_db):
        """Test disabling the description generator feature."""
        org = get_organization("buynlarge")

        # Create settings with feature enabled
        create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=True,
        )

        # Disable the feature
        toggle_description_generator(org.username, enabled=False)

        assert is_description_generator_enabled(org.username) is False

    def test_is_description_generator_enabled_no_settings(self, initialized_db):
        """Test checking feature status when no settings exist."""
        org = get_organization("sellnsmall")

        # No settings exist, should return False
        assert is_description_generator_enabled(org.username) is False

    def test_toggle_creates_settings_if_not_exist(self, initialized_db):
        """Test that toggling creates settings if they don't exist."""
        org = get_organization("sellnsmall")

        # No settings exist
        assert get_org_ai_settings(org.username) is None

        # Toggle should create settings
        toggle_description_generator(org.username, enabled=True)

        settings = get_org_ai_settings(org.username)
        assert settings is not None
        assert settings.description_generator_enabled is True


class TestCustomProviderEndpoint:
    """Tests for custom provider endpoint configuration."""

    def test_set_custom_provider_with_endpoint(self, initialized_db):
        """Test setting credentials for a custom provider with endpoint."""
        org = get_organization("buynlarge")

        set_org_ai_credentials(
            org.username,
            provider="custom",
            api_key="custom-key",
            model="llama3",
            endpoint="http://localhost:11434/v1",
        )

        settings = get_org_ai_settings(org.username)

        assert settings.provider == "custom"
        assert settings.endpoint == "http://localhost:11434/v1"
        assert settings.model == "llama3"

    def test_hosted_provider_no_endpoint(self, initialized_db):
        """Test that hosted providers don't require endpoint."""
        org = get_organization("buynlarge")

        set_org_ai_credentials(
            org.username,
            provider="anthropic",
            api_key="test-key",
            model="claude-3-haiku",
        )

        settings = get_org_ai_settings(org.username)

        assert settings.provider == "anthropic"
        assert settings.endpoint is None


class TestInvalidOrganization:
    """Tests for handling invalid organization names."""

    def test_get_settings_invalid_org(self, initialized_db):
        """Test getting settings for non-existent org returns None."""
        settings = get_org_ai_settings("nonexistent-org")

        assert settings is None

    def test_create_settings_invalid_org_raises(self, initialized_db):
        """Test creating settings for non-existent org raises exception."""
        with pytest.raises(InvalidOrganizationException):
            create_or_update_org_ai_settings(
                "nonexistent-org",
                description_generator_enabled=True,
            )

    def test_set_credentials_invalid_org_raises(self, initialized_db):
        """Test setting credentials for non-existent org raises exception."""
        with pytest.raises(InvalidOrganizationException):
            set_org_ai_credentials(
                "nonexistent-org",
                provider="anthropic",
                api_key="test",
                model="test",
            )
