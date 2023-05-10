import json
import logging
import requests

from data.billing import RH_SKUS, get_plan, get_plan_using_rh_sku
from datetime import datetime

from data.model import entitlements

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20

MARKETPLACE_FILE = "/conf/stack/quay-marketplace-api.crt"
MARKETPLACE_SECRET = "/conf/stack/quay-marketplace-api.key"


class RHUserAPI:
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


class RHMarketplaceAPI:
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

        return subscription

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

    def find_stripe_subscription(self, account_number):
        """
        Returns the stripe plan for a given account number
        """
        for sku in RH_SKUS:
            user_subscription = self.lookup_subscription(account_number, sku)
            if user_subscription is not None:
                return get_plan_using_rh_sku(sku)

        return None
