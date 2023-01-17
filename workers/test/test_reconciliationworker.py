import random
import string
from datetime import datetime
from dateutil.relativedelta import relativedelta
from test.fixtures import *
from unittest.mock import MagicMock
from unittest.mock import patch

from data import model
from data.database import RedHatSubscriptions
from workers.reconciliationworker import ReconciliationWorker

USER_WITH_NO_PLAN = {
    "customer_id": 0,
    "email": "userwithnoplan@test.com",
    "username": "noplan",
    "password": "password",
}
USER_TO_SAVE = {
    "customer_id": 1,
    "subscription_id": 1,
    "email": "usertocreate@test.com",
    "username": "tocreate",
    "password": "password",
    "sku": "MW00584MO",
}

USER_WITH_STRIPE = {
    "customer_id": 2,
    "subscription_id": 2,
    "email": "userwithstripe@test.com",
    "username": "withstripe",
    "password": "password",
    "sku": "some_other_sku",
}

USER_TO_EXTEND = {
    "customer_id": 3,
    "subscription_id": 3,
    "email": "usertoextend@test.com",
    "username": "toextend",
    "password": "password",
    "sku": "MW00584MO",
}


class FakeUserApi:
    def lookup_customer_id(self, email):
        if email == USER_WITH_NO_PLAN["email"]:
            return USER_WITH_NO_PLAN["customer_id"]
        if email == USER_TO_SAVE["email"]:
            return USER_TO_SAVE["customer_id"]
        if email == USER_WITH_STRIPE["email"]:
            return USER_WITH_STRIPE["customer_id"]
        if email == USER_TO_EXTEND["email"]:
            return USER_TO_EXTEND["customer_id"]
        return None


class FakeMarketplaceApi:
    def __init__(self):
        self.subscription_extended = False
        self.subscription_created = False

    def lookup_subscription(self, customerId, sku_id):
        if customerId == USER_WITH_NO_PLAN["customer_id"]:
            return None
        if customerId == USER_TO_SAVE["customer_id"] and sku_id == USER_TO_SAVE["sku"]:
            response_dict = {
                "id": USER_TO_SAVE["subscription_id"],
                "effectiveEndDate": int(round(datetime.now().timestamp() * 1000)),
            }
            return response_dict
        if (
            customerId == USER_WITH_STRIPE["customer_id"]
            and sku_id == USER_TO_SAVE["sku"]
            and self.subscription_created
        ):
            response_dict = {
                "id": USER_WITH_STRIPE["subscription_id"],
                "effectiveEndDate": int(round(datetime.now().timestamp() * 1000)),
            }
            return response_dict
        if customerId == USER_TO_EXTEND["customer_id"] and sku_id == USER_TO_EXTEND["sku"]:
            response_dict = {
                "id": USER_TO_EXTEND["subscription_id"],
                "effectiveEndDate": int(round(datetime.now().timestamp() * 1000)),
            }
            return response_dict
        return None

    def extend_subscription(self, customerId, endDate):
        pass

    def create_entitlement(self, customerId, skuId):
        pass


internal_user_api = FakeUserApi()
internal_marketplace_api = FakeMarketplaceApi()
# internal_marketplace_api.create_entitlement = MagicMock()

worker = ReconciliationWorker()


def test_perform_reconciliation(initialized_db):

    free_user = model.user.create_user(
        USER_WITH_NO_PLAN["username"], USER_WITH_NO_PLAN["password"], USER_WITH_NO_PLAN["email"]
    )

    model.user.create_user(
        USER_TO_SAVE["username"], USER_TO_SAVE["password"], USER_TO_SAVE["email"]
    )

    worker._perform_reconciliation(
        user_api=internal_user_api, marketplace_api=internal_marketplace_api
    )

    assert model.entitlements.get_subscription_by_id(USER_TO_SAVE["subscription_id"]) is not None
    assert model.entitlements.get_subscription_by_user(free_user.id) is None


def test_create_for_stripe(initialized_db):
    stripe_user = model.user.create_user(
        USER_WITH_STRIPE["username"], USER_WITH_STRIPE["password"], USER_WITH_STRIPE["email"]
    )
    stripe_user.stripe_id = "cus_" + "".join(random.choices(string.ascii_lowercase, k=14))
    stripe_user.save()

    with patch.object(internal_marketplace_api, "create_entitlement") as mock:
        worker._perform_reconciliation(
            user_api=internal_user_api, marketplace_api=internal_marketplace_api
        )
        # verify that a subscription was created for stripe user
        mock.assert_called()


def test_extend_existing_subscription(initialized_db):
    user_to_extend = model.user.create_user(
        USER_TO_EXTEND["username"], USER_TO_EXTEND["password"], USER_TO_EXTEND["email"]
    )
    endDate = datetime.now() - relativedelta(months=1)
    model.entitlements.save_subscription(
        user_to_extend.id,
        USER_TO_EXTEND["subscription_id"],
        USER_TO_EXTEND["customer_id"],
        endDate,
        USER_TO_EXTEND["sku"],
    )

    worker._perform_reconciliation(
        user_api=internal_user_api, marketplace_api=internal_marketplace_api
    )

    extended_date = RedHatSubscriptions.get(
        RedHatSubscriptions.subscription_id == USER_TO_EXTEND["subscription_id"]
    ).subscription_end_date

    assert extended_date > endDate
