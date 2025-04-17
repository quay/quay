import random
import string
from unittest.mock import patch

from app import billing as stripe
from app import marketplace_subscriptions, marketplace_users
from data import model
from test.fixtures import *
from workers.reconciliationworker import ReconciliationWorker

worker = ReconciliationWorker()


def test_skip_free_user(initialized_db):

    free_user = model.user.create_user("free_user", "password", "free_user@test.com")
    free_user.save()

    with patch.object(marketplace_subscriptions, "create_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # adding the free tier
    mock.assert_called_with(23456, "MW04192")


def test_remove_free_tier(initialized_db):
    # if a user has a sku and also has a free tier, the free tier should be removed
    paid_user = model.user.create_user("paid_user", "password", "paid@test.com")
    paid_user.save()
    marketplace_subscriptions.create_entitlement(12345, "MW04192")
    with patch.object(marketplace_subscriptions, "remove_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
    mock.assert_called_with(56781234)  # fake "free" tier subscription id mocked in marketplace.py


def test_reconcile_org_user(initialized_db):
    user = model.user.get_user("devtable")

    org_user = model.organization.create_organization("org_user", "org_user@test.com", user)
    org_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    org_user.save()
    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    mock.assert_called_with(org_user.email)


def test_exception_handling(initialized_db, caplog):
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.InvalidRequestError
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.APIConnectionError
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)


def test_attribute_error(initialized_db, caplog):
    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:

        class MockCustomer:
            @property
            def subscription(self):
                raise AttributeError

        mock.return_value = MockCustomer()
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)


def test_create_for_stripe_user(initialized_db):

    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    with patch.object(marketplace_subscriptions, "create_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # expect that entitlment is created with account number
    mock.assert_called_with(11111, "FakeSKU")
    # expect that entitlment is created with customer id number
    mock.assert_called_with(model.entitlements.get_web_customer_ids(test_user.id)[0], "FakeSKU")


def test_reconcile_different_ids(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    model.entitlements.save_web_customer_id(test_user, 55555)

    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    new_id = model.entitlements.get_web_customer_ids(test_user.id)
    assert new_id != [55555]
    assert new_id == marketplace_users.lookup_customer_id(test_user.email)

    # make sure it will remove account numbers from db that do not belong
    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        mock.return_value = None
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
    assert model.entitlements.get_web_customer_ids(test_user.id) is None


def test_update_same_id(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    model.entitlements.save_web_customer_id(test_user, 11111)

    with patch.object(model.entitlements, "update_web_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    mock.assert_not_called()


def test_empty_email(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", "", email_required=False)
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    assert "" not in mock.call_args_list


def test_null_email(initialized_db):
    test_user = model.user.create_user("stripe_user", "password", None, email_required=False)
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()

    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    assert None not in mock.call_args_list
