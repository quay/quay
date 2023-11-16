import random
import string
from unittest.mock import patch

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


def test_create_for_stripe_user(initialized_db):

    test_user = model.user.create_user("stripe_user", "password", "stripe_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    with patch.object(marketplace_subscriptions, "create_entitlement") as mock:
        worker._perform_reconciliation(marketplace_users, marketplace_subscriptions)

    # expect that entitlment is created with account number
    mock.assert_called_with(11111, "FakeSKU")
