"""
Tests for AI billing integration.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestIsManagedMode:
    """Tests for is_managed_mode function."""

    def test_managed_mode_when_config_set(self):
        """Test that managed mode is detected when config is set."""
        with patch("util.ai.billing.app") as mock_app:
            mock_app.config.get.return_value = "managed"

            from util.ai.billing import is_managed_mode

            assert is_managed_mode() is True

    def test_byok_mode_when_config_set(self):
        """Test that BYOK mode is detected when config is set."""
        with patch("util.ai.billing.app") as mock_app:
            mock_app.config.get.return_value = "byok"

            from util.ai.billing import is_managed_mode

            assert is_managed_mode() is False

    def test_byok_mode_is_default(self):
        """Test that BYOK mode is the default when config not set."""
        with patch("util.ai.billing.app") as mock_app:
            mock_app.config.get.return_value = "byok"  # default value

            from util.ai.billing import is_managed_mode

            assert is_managed_mode() is False

    def test_managed_mode_case_insensitive(self):
        """Test that managed mode check is case insensitive."""
        with patch("util.ai.billing.app") as mock_app:
            mock_app.config.get.return_value = "MANAGED"

            from util.ai.billing import is_managed_mode

            assert is_managed_mode() is True


class TestOrgHasAiSubscription:
    """Tests for org_has_ai_subscription function."""

    def test_returns_false_for_none_user(self):
        """Test that None user returns False."""
        from util.ai.billing import org_has_ai_subscription

        assert org_has_ai_subscription(None) is False

    def test_returns_true_with_stripe_subscription(self):
        """Test that user with Stripe subscription returns True."""
        mock_user = MagicMock()
        mock_user.stripe_id = "cus_123"

        mock_customer = MagicMock()
        mock_customer.subscription = MagicMock()

        with patch("app.billing") as mock_billing:
            mock_billing.Customer.retrieve.return_value = mock_customer

            from util.ai.billing import org_has_ai_subscription

            assert org_has_ai_subscription(mock_user) is True

    def test_returns_false_without_stripe_id(self):
        """Test that user without stripe_id returns False."""
        mock_user = MagicMock()
        mock_user.stripe_id = None
        mock_user.organization = False

        from util.ai.billing import org_has_ai_subscription

        assert org_has_ai_subscription(mock_user) is False

    def test_returns_false_when_no_subscription(self):
        """Test that user with stripe_id but no subscription returns False."""
        mock_user = MagicMock()
        mock_user.stripe_id = "cus_123"
        mock_user.organization = False

        mock_customer = MagicMock()
        mock_customer.subscription = None

        with patch("app.billing") as mock_billing:
            mock_billing.Customer.retrieve.return_value = mock_customer

            from util.ai.billing import org_has_ai_subscription

            assert org_has_ai_subscription(mock_user) is False

    def test_handles_stripe_error_gracefully(self):
        """Test that Stripe errors are handled gracefully."""
        mock_user = MagicMock()
        mock_user.stripe_id = "cus_123"
        mock_user.organization = False

        with patch("app.billing") as mock_billing:
            mock_billing.Customer.retrieve.side_effect = Exception("Stripe error")

            from util.ai.billing import org_has_ai_subscription

            # Should return False on error, not raise
            assert org_has_ai_subscription(mock_user) is False

    def test_checks_rh_marketplace_for_org(self):
        """Test that RH Marketplace is checked for organizations."""
        mock_user = MagicMock()
        mock_user.stripe_id = None
        mock_user.organization = True
        mock_user.id = 123

        mock_query = MagicMock()
        mock_query.count.return_value = 1

        with patch("features.RH_MARKETPLACE", True):
            with patch("data.model.organization_skus") as mock_org_skus:
                mock_org_skus.get_org_subscriptions.return_value = mock_query

                from util.ai.billing import org_has_ai_subscription

                assert org_has_ai_subscription(mock_user) is True


class TestCheckAiSubscriptionRequired:
    """Tests for check_ai_subscription_required function."""

    def test_byok_mode_always_allowed(self):
        """Test that BYOK mode always allows without subscription."""
        mock_user = MagicMock()
        mock_user.stripe_id = None

        with patch("util.ai.billing.is_managed_mode") as mock_mode:
            mock_mode.return_value = False

            from util.ai.billing import check_ai_subscription_required

            allowed, error = check_ai_subscription_required(mock_user)
            assert allowed is True
            assert error is None

    def test_managed_mode_requires_subscription(self):
        """Test that managed mode requires subscription."""
        mock_user = MagicMock()
        mock_user.stripe_id = None
        mock_user.organization = False

        with patch("util.ai.billing.is_managed_mode") as mock_mode:
            mock_mode.return_value = True

            from util.ai.billing import check_ai_subscription_required

            allowed, error = check_ai_subscription_required(mock_user)
            assert allowed is False
            assert "paid subscription" in error.lower()

    def test_managed_mode_with_subscription_allowed(self):
        """Test that managed mode with subscription is allowed."""
        mock_user = MagicMock()
        mock_user.stripe_id = "cus_123"

        mock_customer = MagicMock()
        mock_customer.subscription = MagicMock()

        with patch("util.ai.billing.is_managed_mode") as mock_mode:
            mock_mode.return_value = True

            with patch("app.billing") as mock_billing:
                mock_billing.Customer.retrieve.return_value = mock_customer

                from util.ai.billing import check_ai_subscription_required

                allowed, error = check_ai_subscription_required(mock_user)
                assert allowed is True
                assert error is None


class TestProviderFactoryCreateManaged:
    """Tests for ProviderFactory.create_managed method."""

    def test_create_managed_provider(self):
        """Test creating a managed provider from config."""
        managed_config = {
            "PROVIDER": "google",
            "API_KEY": "test-key",
            "MODEL": "gemini-pro",
            "MAX_TOKENS": 500,
            "TEMPERATURE": 0.7,
        }

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = managed_config

            from util.ai.providers import ProviderFactory

            provider = ProviderFactory.create_managed()
            assert provider is not None
            assert provider.model == "gemini-pro"

    def test_create_managed_with_custom_endpoint(self):
        """Test creating a managed provider with custom endpoint."""
        managed_config = {
            "PROVIDER": "custom",
            "API_KEY": "test-key",
            "MODEL": "llama3",
            "ENDPOINT": "http://internal-ollama:11434/v1",
        }

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = managed_config

            from util.ai.providers import ProviderFactory

            provider = ProviderFactory.create_managed()
            assert provider is not None
            assert provider.model == "llama3"
            assert provider.endpoint == "http://internal-ollama:11434/v1"

    def test_create_managed_raises_without_config(self):
        """Test that create_managed raises when not configured."""
        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = {}

            from util.ai.providers import ProviderConfigError, ProviderFactory

            with pytest.raises(ProviderConfigError) as exc_info:
                ProviderFactory.create_managed()

            assert "not configured" in str(exc_info.value).lower()

    def test_create_managed_raises_without_provider(self):
        """Test that create_managed raises when provider not specified."""
        managed_config = {
            "API_KEY": "test-key",
            "MODEL": "some-model",
        }

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = managed_config

            from util.ai.providers import ProviderConfigError, ProviderFactory

            with pytest.raises(ProviderConfigError) as exc_info:
                ProviderFactory.create_managed()

            assert "PROVIDER is required" in str(exc_info.value)
