"""
Tests for billing API endpoints: duplicate-subscription guard and FakeStripe dev gate.
"""

from unittest.mock import MagicMock, patch

import pytest

import features
from endpoints.api.billing import OrganizationPlan, UserPlan
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401,F403


def _make_customer(has_subscription=False):
    cus = MagicMock()
    cus.id = "cus_test123"
    cus.subscription = MagicMock() if has_subscription else None
    return cus


# ---------------------------------------------------------------------------
# Duplicate-subscription guard: UserPlan.post should return 409 when the
# Stripe customer already has an active subscription.
# ---------------------------------------------------------------------------


class TestUserPlanDuplicateSubscriptionGuard:
    @pytest.fixture(autouse=True)
    def _setup(self, app):
        features.import_features({"FEATURE_BILLING": True})
        app.config["BILLING_TYPE"] = "Stripe"
        app.config["BILLING_DEV"] = False
        yield
        app.config.pop("BILLING_TYPE", None)
        app.config.pop("BILLING_DEV", None)

    def test_post_returns_409_when_subscription_exists(self, app):
        with client_with_identity("devtable", app) as client:
            with patch("endpoints.api.billing.billing") as mock_billing:
                mock_billing.Customer.retrieve.return_value = _make_customer(has_subscription=True)

                with patch("endpoints.api.billing.get_authenticated_user") as mock_user:
                    user = MagicMock()
                    user.stripe_id = "cus_test123"
                    mock_user.return_value = user

                    conduct_api_call(
                        client,
                        UserPlan,
                        "POST",
                        {},
                        body={
                            "plan": "bus-medium-2018",
                            "success_url": "http://localhost/success",
                            "cancel_url": "http://localhost/cancel",
                        },
                        expected_code=409,
                    )


# ---------------------------------------------------------------------------
# Duplicate-subscription guard: OrganizationPlan.post should return 409 when
# the Stripe customer already has an active subscription.
# ---------------------------------------------------------------------------


class TestOrganizationPlanDuplicateSubscriptionGuard:
    @pytest.fixture(autouse=True)
    def _setup(self, app):
        features.import_features({"FEATURE_BILLING": True})
        app.config["BILLING_TYPE"] = "Stripe"
        app.config["BILLING_DEV"] = False
        yield
        app.config.pop("BILLING_TYPE", None)
        app.config.pop("BILLING_DEV", None)

    def test_post_returns_409_when_subscription_exists(self, app):
        with client_with_identity("devtable", app) as client:
            with patch("endpoints.api.billing.billing") as mock_billing:
                mock_billing.Customer.retrieve.return_value = _make_customer(has_subscription=True)

                with patch("endpoints.api.billing.model") as mock_model:
                    org = MagicMock()
                    org.stripe_id = "cus_test123"
                    mock_model.organization.get_organization.return_value = org

                    conduct_api_call(
                        client,
                        OrganizationPlan,
                        "POST",
                        {"orgname": "buynlarge"},
                        body={
                            "plan": "bus-medium-2018",
                            "success_url": "http://localhost/success",
                            "cancel_url": "http://localhost/cancel",
                        },
                        expected_code=409,
                    )


# ---------------------------------------------------------------------------
# FakeStripe dev gate: UserPlan.post and OrganizationPlan.post must return 400
# when BILLING_TYPE=FakeStripe without BILLING_DEV=True.
# ---------------------------------------------------------------------------


class TestFakeStripeDevGate:
    @pytest.fixture(autouse=True)
    def _setup(self, app):
        features.import_features({"FEATURE_BILLING": True})
        app.config["BILLING_TYPE"] = "FakeStripe"
        app.config["BILLING_DEV"] = False
        yield
        app.config.pop("BILLING_TYPE", None)
        app.config.pop("BILLING_DEV", None)

    def test_user_plan_post_blocked_without_billing_dev(self, app):
        with client_with_identity("devtable", app) as client:
            conduct_api_call(
                client,
                UserPlan,
                "POST",
                {},
                body={
                    "plan": "bus-medium-2018",
                    "success_url": "http://localhost/success",
                    "cancel_url": "http://localhost/cancel",
                },
                expected_code=400,
            )

    def test_org_plan_post_blocked_without_billing_dev(self, app):
        with client_with_identity("devtable", app) as client:
            conduct_api_call(
                client,
                OrganizationPlan,
                "POST",
                {"orgname": "buynlarge"},
                body={
                    "plan": "bus-medium-2018",
                    "success_url": "http://localhost/success",
                    "cancel_url": "http://localhost/cancel",
                },
                expected_code=400,
            )
