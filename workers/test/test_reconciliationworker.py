import random
import string
from unittest.mock import patch

from app import billing as stripe
from data import model
from test.fixtures import *
from util.marketplace import FakeSubscriptionApi, FakeUserApi
from workers.reconciliationworker import ReconciliationWorker

user_api = FakeUserApi()
marketplace_api = FakeSubscriptionApi()
worker = ReconciliationWorker()


def test_create_for_stripe_user(initialized_db):

    test_user = model.user.create_user("test_user", "password", "test_user@test.com")
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    with patch.object(marketplace_api, "create_entitlement") as mock:
        worker._perform_reconciliation(user_api=user_api, marketplace_api=marketplace_api)

    mock.assert_called()


def test_skip_free_user(initialized_db):

    free_user = model.user.create_user("free_user", "password", "free_user@test.com")
    free_user.save()

    with patch.object(marketplace_api, "create_entitlement") as mock:
        worker._perform_reconciliation(user_api=user_api, marketplace_api=marketplace_api)

    mock.assert_not_called()


def test_exception_handling(initialized_db):
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.InvalidRequestException
        worker._perform_reconciliation(user_api=user_api, marketplace_api=marketplace_api)
    with patch("data.billing.FakeStripe.Customer.retrieve") as mock:
        mock.side_effect = stripe.error.APIConnectionError
        worker._perform_reconciliation(user_api=user_api, marketplace_api=marketplace_api)
