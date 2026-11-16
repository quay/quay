"""
Tests for billing API endpoints: duplicate-subscription guard, FakeStripe dev gate,
and fake_checkout_session validation.
"""

from unittest.mock import MagicMock, patch

import pytest

import features
from endpoints.api.billing import OrganizationPlan, UserPlan, fake_checkout_session
from endpoints.api.test.shared import conduct_api_call
from endpoints.exception import InvalidRequest, NotFound
from endpoints.test.shared import client_with_identity
from test.fixtures import *  # noqa: F401,F403
from util import fake_checkout


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


# ---------------------------------------------------------------------------
# fake_checkout_session: tests for owner mismatch, performer mismatch, replay,
# and incompatible active subscription.
# ---------------------------------------------------------------------------

_SECRET = "test-secret-key"


def _make_session(owner_uuid, stripe_id, performer_uuid, plan="bus-medium-2018"):
    """Return a signed session token for the given parameters."""
    owner = MagicMock()
    owner.uuid = owner_uuid
    owner.stripe_id = stripe_id
    owner.organization = False
    owner.username = "testuser"
    performer = MagicMock()
    performer.uuid = performer_uuid
    return (
        fake_checkout.create_session(
            _SECRET,
            owner,
            performer,
            "subscription",
            plan,
            "http://localhost/success",
            "http://localhost/cancel",
        )["url"]
        .split("session=")[1]
        .split("&")[0]
    )


def _run(session_id, owner_uuid, stripe_id, performer_uuid, complete=False):
    """Call fake_checkout_session with mocked app config and authenticated user."""
    owner = MagicMock()
    owner.uuid = owner_uuid
    owner.stripe_id = stripe_id
    owner.organization = False

    performer = MagicMock()
    performer.uuid = performer_uuid

    with (
        patch("endpoints.api.billing.app") as mock_app,
        patch("endpoints.api.billing.get_authenticated_user", return_value=performer),
        patch("endpoints.api.billing.get_price", return_value=None),
    ):
        mock_app.config = {"BILLING_TYPE": "FakeStripe", "SECRET_KEY": _SECRET}
        return fake_checkout_session(owner, session_id, complete=complete)


class TestFakeCheckoutSessionValidation:
    def test_owner_uuid_mismatch_raises_not_found(self):
        token = _make_session("owner-uuid", "cus_abc", "performer-uuid")
        with pytest.raises(NotFound):
            _run(token, "WRONG-owner-uuid", "cus_abc", "performer-uuid")

    def test_customer_stripe_id_mismatch_raises_not_found(self):
        token = _make_session("owner-uuid", "cus_abc", "performer-uuid")
        with pytest.raises(NotFound):
            _run(token, "owner-uuid", "cus_WRONG", "performer-uuid")

    def test_performer_mismatch_raises_not_found(self):
        token = _make_session("owner-uuid", "cus_abc", "performer-uuid")
        with pytest.raises(NotFound):
            _run(token, "owner-uuid", "cus_abc", "WRONG-performer-uuid")

    def test_valid_session_returns_preview(self):
        token = _make_session("owner-uuid", "cus_abc", "performer-uuid")
        result = _run(token, "owner-uuid", "cus_abc", "performer-uuid")
        assert result["fake"] is True
        assert "mode" in result

    def test_replay_completed_session_is_idempotent(self):
        """Completing a session twice should not raise and not re-apply."""
        import uuid as _uuid

        from itsdangerous import URLSafeTimedSerializer

        session_id_val = str(_uuid.uuid4())
        s = URLSafeTimedSerializer(_SECRET, salt="quay-fake-checkout")
        token = s.dumps(
            {
                "id": session_id_val,
                "owner": "owner-uuid",
                "customer": "cus_abc",
                "performer": "performer-uuid",
                "mode": "subscription",
                "plan": None,
                "success_url": "http://localhost/success",
                "cancel_url": "http://localhost/cancel",
            }
        )

        fake_customer = MagicMock()
        fake_customer.get.return_value = {"completed_checkouts": [session_id_val]}
        fake_customer.default_card = None

        owner = MagicMock()
        owner.uuid = "owner-uuid"
        owner.stripe_id = "cus_abc"
        owner.organization = False

        performer = MagicMock()
        performer.uuid = "performer-uuid"

        with (
            patch("endpoints.api.billing.app") as mock_app,
            patch("endpoints.api.billing.get_authenticated_user", return_value=performer),
            patch("endpoints.api.billing.get_price", return_value=None),
            patch("endpoints.api.billing.FakeStripe") as mock_stripe,
        ):
            mock_app.config = {"BILLING_TYPE": "FakeStripe", "SECRET_KEY": _SECRET}
            mock_stripe.Customer.retrieve.return_value = fake_customer
            result = fake_checkout_session(owner, token, complete=True)
            assert result["fake"] is True
            # save_customer should NOT have been called because session was already completed
            mock_stripe.save_customer.assert_not_called()

    def test_different_active_subscription_raises_invalid_request(self):
        """Completing a plan checkout when a different plan is active raises InvalidRequest."""
        import uuid as _uuid

        from itsdangerous import URLSafeTimedSerializer

        s = URLSafeTimedSerializer(_SECRET, salt="quay-fake-checkout")
        token = s.dumps(
            {
                "id": str(_uuid.uuid4()),
                "owner": "owner-uuid",
                "customer": "cus_abc",
                "performer": "performer-uuid",
                "mode": "subscription",
                "plan": "bus-medium-2018",
                "success_url": "http://localhost/success",
                "cancel_url": "http://localhost/cancel",
            }
        )

        price = {"stripeId": "price_new_plan"}

        fake_customer = MagicMock()
        fake_customer.get.return_value = {"completed_checkouts": []}
        fake_customer.subscription.plan.id = "price_other_plan"

        owner = MagicMock()
        owner.uuid = "owner-uuid"
        owner.stripe_id = "cus_abc"
        owner.organization = False

        performer = MagicMock()
        performer.uuid = "performer-uuid"

        with (
            patch("endpoints.api.billing.app") as mock_app,
            patch("endpoints.api.billing.get_authenticated_user", return_value=performer),
            patch("endpoints.api.billing.get_price", return_value=price),
            patch("endpoints.api.billing.FakeStripe") as mock_stripe,
        ):
            mock_app.config = {"BILLING_TYPE": "FakeStripe", "SECRET_KEY": _SECRET}
            mock_stripe.Customer.retrieve.return_value = fake_customer
            with pytest.raises(InvalidRequest):
                fake_checkout_session(owner, token, complete=True)
