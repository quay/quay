import base64
import json
from unittest.mock import MagicMock, patch

from flask import url_for

from data import model
from data.model.organization import (
    create_organization,
    get_contact_email,
    set_contact_email,
)
from data.model.user import get_user
from endpoints.test.shared import conduct_call, gen_basic_auth
from test.fixtures import *


class TestStripeWebhookContactEmail:
    """Tests for Stripe webhook handlers with organization contact email support."""

    def _post_stripe_event(self, client, event_type, data, customer_id="cust_test"):
        payload = {
            "type": event_type,
            "data": {"object": {"customer": customer_id, **data}},
        }
        return client.post(
            "/webhooks/stripe",
            data=json.dumps(payload),
            content_type="application/json",
        )

    @patch("endpoints.webhooks.stripe")
    def test_charge_succeeded_org_with_contact_email(self, mock_stripe, app, client):
        admin = get_user("devtable")
        org = create_organization("chargeorg1", None, admin, contact_email="billing@example.com")
        org.invoice_email = True
        org.invoice_email_address = None
        org.stripe_id = "cust_charge1"
        org.save()

        mock_invoice = MagicMock()
        mock_stripe.Invoice.retrieve.return_value = mock_invoice

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch(
                "endpoints.webhooks.renderInvoiceToHtml", return_value="<html>invoice</html>"
            ):
                with patch("endpoints.webhooks.send_invoice_email") as mock_send:
                    resp = self._post_stripe_event(
                        client,
                        "charge.succeeded",
                        {"invoice": "inv_123"},
                        customer_id="cust_charge1",
                    )

        assert resp.status_code == 200
        mock_send.assert_called_once_with("billing@example.com", "<html>invoice</html>")

    @patch("endpoints.webhooks.stripe")
    def test_charge_succeeded_org_no_contact_email_falls_back_to_admins(
        self, mock_stripe, app, client
    ):
        admin = get_user("devtable")
        org = create_organization("chargeorg2", None, admin)
        org.invoice_email = True
        org.invoice_email_address = None
        org.stripe_id = "cust_charge2"
        org.save()

        mock_invoice = MagicMock()
        mock_stripe.Invoice.retrieve.return_value = mock_invoice

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch(
                "endpoints.webhooks.renderInvoiceToHtml", return_value="<html>invoice</html>"
            ):
                with patch("endpoints.webhooks.send_invoice_email") as mock_send:
                    resp = self._post_stripe_event(
                        client,
                        "charge.succeeded",
                        {"invoice": "inv_456"},
                        customer_id="cust_charge2",
                    )

        assert resp.status_code == 200
        assert mock_send.call_count >= 1
        sent_emails = [call.args[0] for call in mock_send.call_args_list]
        assert admin.email in sent_emails

    @patch("endpoints.webhooks.stripe")
    def test_charge_succeeded_personal_user(self, mock_stripe, app, client):
        user = get_user("devtable")
        user.invoice_email = True
        user.invoice_email_address = "personal@example.com"
        user.stripe_id = "cust_personal"
        user.save()

        mock_invoice = MagicMock()
        mock_stripe.Invoice.retrieve.return_value = mock_invoice

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=user
        ):
            with patch(
                "endpoints.webhooks.renderInvoiceToHtml", return_value="<html>invoice</html>"
            ):
                with patch("endpoints.webhooks.send_invoice_email") as mock_send:
                    resp = self._post_stripe_event(
                        client,
                        "charge.succeeded",
                        {"invoice": "inv_789"},
                        customer_id="cust_personal",
                    )

        assert resp.status_code == 200
        mock_send.assert_called_once_with("personal@example.com", "<html>invoice</html>")

    def test_subscription_created_org_with_contact_email(self, app, client):
        admin = get_user("devtable")
        org = create_organization("suborg1", None, admin, contact_email="sub@example.com")
        org.stripe_id = "cust_sub1"
        org.save()

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch("endpoints.webhooks.send_subscription_change") as mock_send:
                resp = self._post_stripe_event(
                    client,
                    "customer.subscription.created",
                    {"plan": {"id": "plan_basic"}},
                    customer_id="cust_sub1",
                )

        assert resp.status_code == 200
        mock_send.assert_called_once()
        assert mock_send.call_args[0][2] == "sub@example.com"

    def test_subscription_created_org_no_contact_email_falls_back_to_admin(self, app, client):
        admin = get_user("devtable")
        org = create_organization("suborg2", None, admin)
        org.stripe_id = "cust_sub2"
        org.save()

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch("endpoints.webhooks.send_subscription_change") as mock_send:
                resp = self._post_stripe_event(
                    client,
                    "customer.subscription.created",
                    {"plan": {"id": "plan_basic"}},
                    customer_id="cust_sub2",
                )

        assert resp.status_code == 200
        mock_send.assert_called_once()
        assert mock_send.call_args[0][2] == admin.email

    def test_payment_failed_org_with_contact_email(self, app, client):
        admin = get_user("devtable")
        org = create_organization("payorg1", None, admin, contact_email="pay@example.com")
        org.stripe_id = "cust_pay1"
        org.save()

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch("endpoints.webhooks.send_payment_failed") as mock_send:
                resp = self._post_stripe_event(
                    client,
                    "invoice.payment_failed",
                    {},
                    customer_id="cust_pay1",
                )

        assert resp.status_code == 200
        mock_send.assert_called_once_with("pay@example.com", org.username)

    def test_payment_failed_org_no_contact_email_falls_back_to_admins(self, app, client):
        admin = get_user("devtable")
        org = create_organization("payorg2", None, admin)
        org.stripe_id = "cust_pay2"
        org.save()

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=org
        ):
            with patch("endpoints.webhooks.send_payment_failed") as mock_send:
                resp = self._post_stripe_event(
                    client,
                    "invoice.payment_failed",
                    {},
                    customer_id="cust_pay2",
                )

        assert resp.status_code == 200
        assert mock_send.call_count >= 1
        sent_emails = [call.args[0] for call in mock_send.call_args_list]
        assert admin.email in sent_emails

    def test_payment_failed_personal_user(self, app, client):
        user = get_user("devtable")

        with patch(
            "endpoints.webhooks.model.user.get_user_or_org_by_customer_id", return_value=user
        ):
            with patch("endpoints.webhooks.send_payment_failed") as mock_send:
                resp = self._post_stripe_event(
                    client,
                    "invoice.payment_failed",
                    {},
                    customer_id="cust_personal2",
                )

        assert resp.status_code == 200
        mock_send.assert_called_once_with(user.email, user.username)


def test_start_build_disabled_trigger(app, client):
    trigger = model.build.list_build_triggers("devtable", "building")[0]
    trigger.enabled = False
    trigger.save()

    params = {
        "trigger_uuid": trigger.uuid,
    }

    headers = {
        "Authorization": gen_basic_auth("devtable", "password"),
    }

    conduct_call(
        client,
        "webhooks.build_trigger_webhook",
        url_for,
        "POST",
        params,
        None,
        400,
        headers=headers,
    )
