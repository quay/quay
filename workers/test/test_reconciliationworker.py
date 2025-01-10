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

    mock.assert_not_called()


def test_reconcile_org_user(initialized_db):
    user = model.user.get_user("devtable")

    org_user = model.organization.create_organization("org_user", "org_user@test.com", user)
    org_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    org_user.save()
    with patch.object(marketplace_users, "lookup_customer_id") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    mock.assert_called_with(org_user.email)


def test_exception_handling(initialized_db):
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.InvalidRequestException
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.APIConnectionError
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
    model.entitlements.save_web_customer_id(test_user, 12345)

    worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    new_id = model.entitlements.get_web_customer_ids(test_user.id)
    assert new_id != [12345]
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
