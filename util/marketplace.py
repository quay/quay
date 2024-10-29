import json
import logging
import time

import requests

from data.billing import RECONCILER_SKUS, RH_SKUS, get_plan_using_rh_sku
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
        account_numbers = self.lookup_customer_id(email)
        return account_numbers

    def lookup_customer_id(self, email):
        """
        Send request to internal api for customer id (web customer id)
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
        try:
            r = requests.request(
                method="post",
                url=request_url,
                cert=self.cert,
                json=request_body_dict,
                verify=True,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ReadTimeout:
            logger.info("request to %s timed out", self.user_endpoint)
            return None

        info = json.loads(r.content)
        if not info:
            logger.debug("request to %s did not return any data", self.user_endpoint)
            return None

        customer_ids = []
        for account in info:
            customer_id = account["accountRelationships"][0]["account"].get("id")
            # convert str response from api to int value
            if customer_id.isdigit():
                customer_id = int(customer_id)
            customer_ids.append(customer_id)
        return customer_ids


class RedHatSubscriptionApi(object):
    def __init__(self, app_config):
        self.cert = (MARKETPLACE_FILE, MARKETPLACE_SECRET)
        self.marketplace_endpoint = app_config.get(
            "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT"
        )

    def lookup_subscription(self, webCustomerId, skuId):
        """
        Use internal marketplace API to find subscription for customerId and sku
        """
        logger.debug(
            "looking up subscription sku %s for account %s", str(skuId), str(webCustomerId)
        )

        subscriptions_url = f"{self.marketplace_endpoint}/subscription/v5/search/criteria;sku={skuId};web_customer_id={webCustomerId}"
        request_headers = {"Content-Type": "application/json"}

        # Using CustomerID to get active subscription for user
        try:
            r = requests.request(
                method="get",
                url=subscriptions_url,
                headers=request_headers,
                cert=self.cert,
                verify=True,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ReadTimeout:
            logger.info("request to %s timed out", self.marketplace_endpoint)
            return None

        try:
            subscriptions = json.loads(r.content)
        except json.decoder.JSONDecodeError:
            return None

        valid_subscriptions = []
        if subscriptions:
            for subscription in subscriptions:
                end_date = subscription["effectiveEndDate"]
                now_ms = time.time() * 1000
                # Is subscription still valid?
                if now_ms < end_date:
                    logger.debug("subscription found for %s", str(skuId))
                    valid_subscriptions.append(subscription)
            return valid_subscriptions
        return None

    def extend_subscription(self, subscription_id, endDate):
        """
        Use internal marketplace API to extend a subscription to endDate
        """
        extend_url = f"{self.marketplace_endpoint}/subscription/v5/extendActiveSubscription/{subscription_id}/{endDate}"
        request_headers = {"Content-Type:": "application/json"}
        try:
            r = requests.request(
                method="get",
                url=extend_url,
                headers=request_headers,
                cert=self.cert,
                verify=True,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ReadTimeout:
            logger.info("request to %s timed out", self.marketplace_endpoint)
            return None

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
        try:
            r = requests.request(
                method="post",
                url=request_url,
                cert=self.cert,
                headers=request_headers,
                json=request_body_dict,
                verify=True,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.ReadTimeout:
            logger.info("request to %s timed out", self.marketplace_endpoint)
            return 408

        return r.status_code

    def get_subscription_details(self, subscription_id):
        """
        Return the sku and expiration date for a specific subscription
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

            subscription_sku = info[0]["sku"]
            expiration_date = info[1]["activeEndDate"]
            terminated_date = info[0]["terminatedDate"]
            return {
                "sku": subscription_sku,
                "expiration_date": expiration_date,
                "terminated_date": terminated_date,
            }
        except requests.exceptions.SSLError:
            raise requests.exceptions.SSLError
        except requests.exceptions.ReadTimeout:
            logger.info("request to %s timed out", self.marketplace_endpoint)
            return None

    def get_list_of_subscriptions(
        self, account_number, filter_out_org_bindings=False, convert_to_stripe_plans=False
    ):
        """
        Returns a list of all active subscriptions a user has
        in RH marketplace
        """
        subscription_list = []
        for sku in RH_SKUS:
            subscriptions = self.lookup_subscription(account_number, sku)
            if subscriptions:
                for user_subscription in subscriptions:
                    if user_subscription is not None:
                        if (
                            user_subscription["masterEndSystemName"] == "SUBSCRIPTION"
                            and sku in RECONCILER_SKUS
                        ):
                            continue

                        bound_to_org = organization_skus.subscription_bound_to_org(
                            user_subscription["id"]
                        )

                        if filter_out_org_bindings and bound_to_org[0]:
                            continue

                        if convert_to_stripe_plans:
                            quantity = user_subscription["quantity"]
                            for i in range(quantity):
                                subscription_list.append(get_plan_using_rh_sku(sku))
                        else:
                            # add in sku field for convenience
                            user_subscription["sku"] = sku
                            subscription_list.append(user_subscription)
        return subscription_list


# Mocked classes for unit tests


TEST_USER = {
    "account_number": 12345,
    "email": "subscriptions@devtable.com",
    "username": "subscription",
    "subscriptions": [
        {
            "id": 12345678,
            "masterEndSystemName": "Quay",
            "createdEndSystemName": "SUBSCRIPTION",
            "createdDate": 1675957362000,
            "lastUpdateEndSystemName": "SUBSCRIPTION",
            "lastUpdateDate": 1675957362000,
            "installBaseStartDate": 1707368400000,
            "installBaseEndDate": 1707368399000,
            "webCustomerId": 123456,
            "subscriptionNumber": "12399889",
            "quantity": 2,
            "effectiveStartDate": 1707368400000,
            "effectiveEndDate": 3813177600000,
        },
        {
            "id": 11223344,
            "masterEndSystemName": "Quay",
            "createdEndSystemName": "SUBSCRIPTION",
            "createdDate": 1675957362000,
            "lastUpdateEndSystemName": "SUBSCRIPTION",
            "lastUpdateDate": 1675957362000,
            "installBaseStartDate": 1707368400000,
            "installBaseEndDate": 1707368399000,
            "webCustomerId": 123456,
            "subscriptionNumber": "12399889",
            "quantity": 1,
            "effectiveStartDate": 1707368400000,
            "effectiveEndDate": 3813177600000,
        },
    ],
    "reconciled_subscription": {
        "id": 87654321,
        "masterEndSystemName": "SUBSCRIPTION",
        "createdEndSystemName": "SUBSCRIPTION",
        "createdDate": 1675957362000,
        "lastUpdateEndSystemName": "SUBSCRIPTION",
        "lastUpdateDate": 1675957362000,
        "installBaseStartDate": 1707368400000,
        "installBaseEndDate": 1707368399000,
        "webCustomerId": 123456,
        "subscriptionNumber": "12399889",
        "quantity": 1,
        "effectiveStartDate": 1707368400000,
        "effectiveEndDate": 3813177600000,
    },
    "terminated_subscription": {
        "id": 22222222,
        "masterEndSystemName": "SUBSCRIPTION",
        "createdEndSystemName": "SUBSCRIPTION",
        "createdDate": 1675957362000,
        "lastUpdateEndSystemName": "SUBSCRIPTION",
        "lastUpdateDate": 1675957362000,
        "installBaseStartDate": 1707368400000,
        "installBaseEndDate": 1707368399000,
        "webCustomerId": 123456,
        "subscriptionNumber": "12399889",
        "quantity": 1,
        "effectiveStartDate": 1707368400000,
        "effectiveEndDate": 3813177600000,
    },
}
STRIPE_USER = {"account_number": 11111, "email": "stripe_user@test.com", "username": "stripe_user"}
FREE_USER = {
    "account_number": 23456,
    "email": "free_user@test.com",
    "username": "free_user",
}


class FakeUserApi(RedHatUserApi):
    """
    Fake class used for tests
    """

    def lookup_customer_id(self, email):
        if email == TEST_USER["email"]:
            return [TEST_USER["account_number"]]
        if email == FREE_USER["email"]:
            return [FREE_USER["account_number"]]
        if email == STRIPE_USER["email"]:
            return [STRIPE_USER["account_number"]]
        return None


class FakeSubscriptionApi(RedHatSubscriptionApi):
    """
    Fake class used for tests
    """

    def __init__(self):
        self.subscription_extended = False
        self.subscription_created = False

    def lookup_subscription(self, customer_id, sku_id):
        if customer_id == TEST_USER["account_number"] and sku_id == "MW02701":
            return TEST_USER["subscriptions"]
        elif customer_id == TEST_USER["account_number"] and sku_id == "MW00584MO":
            return [TEST_USER["reconciled_subscription"]]
        return None

    def create_entitlement(self, customer_id, sku_id):
        self.subscription_created = True

    def extend_subscription(self, subscription_id, end_date):
        self.subscription_extended = True

    def get_subscription_details(self, subscription_id):
        valid_ids = [subscription["id"] for subscription in TEST_USER["subscriptions"]]
        if subscription_id in valid_ids:
            return {"sku": "MW02701", "expiration_date": 3813177600000, "terminated_date": None}
        elif subscription_id == 80808080:
            return {"sku": "MW02701", "expiration_date": 1645544830000, "terminated_date": None}
        elif subscription_id == 87654321:
            return {"sku": "MW00584MO", "expiration_date": 3813177600000, "terminated_date": None}
        elif subscription_id == 22222222:
            return {
                "sku": "MW00584MO",
                "expiration_date": 3813177600000,
                "terminated_date": 1645544830000,
            }
        else:
            return None


class MarketplaceUserApi(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        marketplace_enabled = app.config.get("FEATURE_RH_MARKETPLACE", False)
        reconciler_enabled = app.config.get("ENTITLEMENT_RECONCILIATION", False)

        use_rh_api = marketplace_enabled or reconciler_enabled

        marketplace_user_api = FakeUserApi(app.config)

        if use_rh_api and not app.config.get("TESTING"):
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
        reconciler_enabled = app.config.get("ENTITLEMENT_RECONCILIATION", False)
        marketplace_enabled = app.config.get("FEATURE_RH_MARKETPLACE", False)

        use_rh_api = marketplace_enabled or reconciler_enabled

        marketplace_subscription_api = FakeSubscriptionApi()

        if use_rh_api and not app.config.get("TESTING"):
            marketplace_subscription_api = RedHatSubscriptionApi(app.config)

        app.extensions = getattr(app, "extensions", {})
        app.extensions["marketplace_subscription_api"] = marketplace_subscription_api
        return marketplace_subscription_api

    def __getattr__(self, name):
        return getattr(self.state, name, None)
