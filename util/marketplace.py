import json
import logging
import time
from datetime import datetime

import requests

from data.billing import RH_SKUS, get_plan_using_rh_sku
from data.model import entitlements, organization_skus

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20

MARKETPLACE_FILE = "/conf/stack/quay-marketplace-api.crt"
MARKETPLACE_SECRET = "/conf/stack/quay-marketplace-api.key"


class RedHatUserApi(object):
    def __init__(self, app_config):
        self.cert = (MARKETPLACE_FILE, MARKETPLACE_SECRET)
        self.user_endpoint = app_config.get("ENTITLEMENT_RECONCILIATION_USER_ENDPOINT")

    def get_account_number(self, user):
        email = user.email
        account_number = entitlements.get_ebs_account_number(user.id)
        if account_number is None:
            account_number = self.lookup_customer_id(email)
            if account_number:
                # store in database for next lookup
                entitlements.save_ebs_account_number(user, account_number)
        return account_number

    def lookup_customer_id(self, email):
        """
        Send request to internal api for customer id (ebs acc number)
        """
        request_body_dict = {
            "by": {"emailStartsWith": email},
            "include": {
                "accountRelationships": [
                    {
                        "allOf": [
                            "primary_email",
                            "is_supportable",
                            "account_details",
                        ],
                        "by": {"active": True},
                    }
                ]
            },
        }

        request_url = f"{self.user_endpoint}/v2/findUsers"
        r = requests.request(
            method="post",
            url=request_url,
            cert=self.cert,
            json=request_body_dict,
            verify=True,
            timeout=REQUEST_TIMEOUT,
        )

        info = json.loads(r.content)
        if not info:
            return None
        account_number = info[0]["accountRelationships"][0]["account"]["ebsAccountNumber"]
        return account_number


class RedHatSubscriptionApi(object):
    def __init__(self, app_config):
        self.cert = (MARKETPLACE_FILE, MARKETPLACE_SECRET)
        self.marketplace_endpoint = app_config.get(
            "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT"
        )

    def lookup_subscription(self, ebsAccountNumber, skuId):
        """
        Use internal marketplace API to find subscription for customerId and sku
        """
        logger.debug(
            "looking up subscription sku %s for account %s", str(skuId), str(ebsAccountNumber)
        )

        subscriptions_url = f"{self.marketplace_endpoint}/subscription/v5/search/criteria;sku={skuId};web_customer_id={ebsAccountNumber}"
        request_headers = {"Content-Type": "application/json"}

        # Using CustomerID to get active subscription for user
        r = requests.request(
            method="get",
            url=subscriptions_url,
            headers=request_headers,
            cert=self.cert,
            verify=True,
            timeout=REQUEST_TIMEOUT,
        )
        try:
            subscription = max(
                json.loads(r.content), key=lambda i: (i["effectiveEndDate"]), default=None
            )
        except json.decoder.JSONDecodeError:
            return None

        if subscription:
            end_date = subscription["effectiveEndDate"]
            now_ms = time.time() * 1000
            # Is subscription still valid?
            if now_ms < end_date:
                logger.debug("subscription found for %s", str(skuId))
                return subscription
        return None

    def extend_subscription(self, subscription_id, endDate):
        """
        Use internal marketplace API to extend a subscription to endDate
        """
        extend_url = f"{self.marketplace_endpoint}/subscription/v5/extendActiveSubscription/{subscription_id}/{endDate}"
        request_headers = {"Content-Type:": "application/json"}
        r = requests.request(
            method="get",
            url=extend_url,
            headers=request_headers,
            cert=self.cert,
            verify=True,
            timeout=REQUEST_TIMEOUT,
        )
        logger.debug("Extended subscription %i to %s", subscription_id, str(endDate))
        return r

    def create_entitlement(self, customerId, sku):
        """
        create subscription for user in internal marketplace
        """
        request_url = f"{self.marketplace_endpoint}/subscription/v5/createPerm"
        request_headers = {"Content-Type": "application/json"}

        logger.debug("Creating subscription for %s with sku %s", customerId, sku)

        request_body_dict = {
            "sku": sku,
            "qty": 1,
            "duration": {
                "hour": 0,
                "day": 0,
                "week": 0,
                "month": 1,
                "year": 0,
                "minute": 0,
                "second": 0,
                "zero": True,
                "millisecond": 0,
            },
            "webCustomerId": customerId,
        }
        logger.debug("Created entitlement")
        r = requests.request(
            method="post",
            url=request_url,
            cert=self.cert,
            headers=request_headers,
            json=request_body_dict,
            verify=True,
            timeout=REQUEST_TIMEOUT,
        )
        return r.status_code

    def get_subscription_sku(self, subscription_id):
        """
        Return the sku for a specific subscription
        """
        request_url = f"{self.marketplace_endpoint}/subscription/v5/products/subscription_id={subscription_id}"
        request_headers = {"Content-Type": "application/json"}

        try:
            r = requests.request(
                method="get",
                url=request_url,
                cert=self.cert,
                verify=True,
                timeout=REQUEST_TIMEOUT,
                headers=request_headers,
            )

            info = json.loads(r.content)

            SubscriptionSKU = info[0]["sku"]
            return SubscriptionSKU
        except requests.exceptions.SSLError:
            raise requests.exceptions.SSLError

    def get_list_of_subscriptions(
        self, account_number, filter_out_org_bindings=False, convert_to_stripe_plans=False
    ):
        """
        Returns a list of all active subscriptions a user has
        in RH marketplace
        """
        subscription_list = []
        for sku in RH_SKUS:
            user_subscription = self.lookup_subscription(account_number, sku)
            if user_subscription is not None:
                bound_to_org = organization_skus.subscription_bound_to_org(user_subscription["id"])

                if filter_out_org_bindings and bound_to_org[0]:
                    continue

                if convert_to_stripe_plans:
                    subscription_list.append(get_plan_using_rh_sku(sku))
                else:
                    # add in sku field for convenience
                    user_subscription["sku"] = sku
                    subscription_list.append(user_subscription)
        return subscription_list


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

DEV_ACCOUNT_NUMBER = 76543


class FakeUserApi(object):
    """
    Fake class used for tests
    """

    def lookup_customer_id(self, email):
        if email == TEST_USER["email"]:
            return TEST_USER["account_number"]
        if email == FREE_USER["email"]:
            return FREE_USER["account_number"]
        return None

    def get_account_number(self, user):
        if user.username == "devtable":
            return DEV_ACCOUNT_NUMBER
        return self.lookup_customer_id(user.email)


class FakeSubscriptionApi(object):
    """
    Fake class used for tests
    """

    def __init__(self):
        self.subscription_extended = False
        self.subscription_created = False

    def lookup_subscription(self, customer_id, sku_id):
        return None

    def create_entitlement(self, customer_id, sku_id):
        self.subscription_created = True

    def extend_subscription(self, subscription_id, end_date):
        self.subscription_extended = True

    def get_subscription_sku(self, subscription_id):
        if id == 12345:
            return "FakeSku"
        else:
            return None

    def get_list_of_subscriptions(
        self, account_number, filter_out_org_bindings=False, convert_to_stripe_plans=False
    ):
        if account_number == DEV_ACCOUNT_NUMBER:
            return [
                {
                    "id": 12345,
                    "sku": "FakeSku",
                    "privateRepos": 0,
                }
            ]
        return []


class MarketplaceUserApi(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        marketplace_enabled = app.config.get("FEATURE_RH_MARKETPLACE", False)

        marketplace_user_api = FakeUserApi()

        if marketplace_enabled and not app.config.get("TESTING"):
            marketplace_user_api = RedHatUserApi(app.config)

        app.extensions = getattr(app, "extensions", {})
        app.extensions["marketplace_user_api"] = marketplace_user_api
        return marketplace_user_api

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class MarketplaceSubscriptionApi(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        marketplace_enabled = app.config.get("FEATURE_RH_MARKETPLACE", False)

        marketplace_subscription_api = FakeSubscriptionApi()

        if marketplace_enabled and not app.config.get("TESTING"):
            marketplace_subscription_api = RedHatSubscriptionApi(app.config)

        app.extensions = getattr(app, "extensions", {})
        app.extensions["marketplace_subscription_api"] = marketplace_subscription_api
        return marketplace_subscription_api

    def __getattr__(self, name):
        return getattr(self.state, name, None)
