import json
import logging
import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 200

MARKETPLACE_FILE = "/conf/stack/auth/quay-marketplace-api-stage.crt"
MARKETPLACE_SECRET = "/conf/stack/auth/quay-marketplace-api-stage.key"


class UserAPI:
    def __init__(self, app_config=None):
        self.cert = (MARKETPLACE_FILE, MARKETPLACE_SECRET)
        self.user_endpoint = app_config.get("ENTITLEMENT_RECONCILIATION_USER_ENDPOINT")

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
            verify=False,
            timeout=REQUEST_TIMEOUT,
        )

        logger.debug(r.content)
        info = json.loads(r.content)
        if not info:
            return None
        # gathering customer id from response
        CustomerId = info[0]["accountRelationships"][0]["account"]["ebsAccountNumber"]
        return CustomerId


class MarketplaceAPI:
    def __init__(self, app_config):
        self.cert = (MARKETPLACE_FILE, MARKETPLACE_SECRET)
        self.marketplace_endpoint = app_config.get(
            "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT"
        )

    def lookup_subscription(self, ebsAccountNumber, skuId):
        """
        Use internal marketplace API to find subscription for customerId and sku
        """
        logger.debug("looking up subscription for %s", str(ebsAccountNumber))

        subscriptions_url = f"{self.marketplace_endpoint}/subscription/v5/search/criteria;sku={skuId};web_customer_id={ebsAccountNumber}"
        request_headers = {"Content-Type": "application/json"}

        # Using CustomerID to get active subscription for user
        r = requests.request(
            method="get",
            url=subscriptions_url,
            headers=request_headers,
            cert=self.cert,
            verify=False,
            timeout=REQUEST_TIMEOUT,
        )
        logger.debug(r.content)
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
            verify=False,
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

        # skus least to most expensive
        # MW00584MO 5 repos
        # MW00585MO 10 repos
        # MW00586MO 20 repos
        # MW00587MO 50 repos
        # MW00588MO 125 repos
        # MW00589MO 250 repos
        # MW00590MO 500 repos
        # MW00591MO 1000 repos
        # MW00592MO 2000 repos
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
            verify=False,
            timeout=REQUEST_TIMEOUT,
        )
        return r.status_code
