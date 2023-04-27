import random
import string
from datetime import datetime
from dateutil.relativedelta import relativedelta
from test.fixtures import *
from unittest.mock import MagicMock
from unittest.mock import patch

from data import model
from workers.reconciliationworker import ReconciliationWorker

TEST_USER = {
    "account_number": 12345,
    "email": "test_user@test.com",
    "username": "test_user",
    "password": "password",
}
FREE_USER = {
    "account_number": 23456,
    "email": "free_user@test.com",
    "username": "free_user",
    "password": "password",
}


class FakeUserApi:
    def lookup_customer_id(self, email):
        if email == TEST_USER["email"]:
            return TEST_USER["account_number"]
        if email == FREE_USER["email"]:
            return FREE_USER["account_number"]
        return None


class FakeMarketplaceApi:
    def __init__(self):
        self.subscription_extended = False
        self.subscription_created = False

    def lookup_subscription(self, customerId, sku_id):
        return None

    def create_entitlement(self, customerId, skuId):
        pass


internal_user_api = FakeUserApi()
internal_marketplace_api = FakeMarketplaceApi()
worker = ReconciliationWorker()


def test_create_for_stripe_user(initialized_db):

    test_user = model.user.create_user(
        TEST_USER["username"], TEST_USER["password"], TEST_USER["email"]
    )
    test_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    test_user.save()
    with patch.object(internal_marketplace_api, "create_entitlement") as mock:
        worker._perform_reconciliation(
            user_api=internal_user_api, marketplace_api=internal_marketplace_api
        )

    mock.assert_called()


def test_skip_free_user(initialized_db):

    free_user = model.user.create_user(
        FREE_USER["username"], FREE_USER["password"], FREE_USER["email"]
    )
    free_user.save()

    with patch.object(internal_marketplace_api, "create_entitlement") as mock:
        worker._perform_reconciliation(
            user_api=internal_user_api, marketplace_api=internal_marketplace_api
        )

    mock.assert_not_called()
