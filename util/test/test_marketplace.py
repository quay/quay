import json

import requests
from mock import patch

from util.marketplace import RedHatSubscriptionApi, RedHatUserApi

app_config = {
    "ENTITLEMENT_RECONCILIATION_USER_ENDPOINT": "https://example.com",
    "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT": "https://example.com",
}

mocked_user_service_response = [
    {
        "id": "12345678",
        "accountRelationships": [
            {
                "emails": [{"address": "example@example.com", "status": "enabled"}],
                "accountId": "fakeid",
                "startDate": "2022-09-19T04:18:19.228Z",
                "id": "fakeid",
                "account": {
                    "id": "222222222",
                    "cdhPartyNumber": "11111111",
                    "ebsAccountNumber": "102030",
                    "name": "Red Hat",
                    "displayName": "Red Hat",
                    "status": "enabled",
                    "type": "organization",
                },
            }
        ],
    },
    {
        "id": "87654321",
        "accountRelationships": [
            {
                "emails": [{"address": "example@example.com", "status": "enabled"}],
                "accountId": "fakeid",
                "startDate": "2022-09-20T14:31:09.974Z",
                "id": "fakeid",
                "account": {
                    "id": "000000000",
                    "cdhPartyNumber": "0000000",
                    "ebsAccountNumber": "1234567",
                    "name": "Test User",
                    "status": "enabled",
                    "type": "person",
                },
            }
        ],
    },
]

mocked_organization_only_response = [
    {
        "id": "12345678",
        "accountRelationships": [
            {
                "emails": [{"address": "example@example.com", "status": "enabled"}],
                "accountId": "fakeid",
                "startDate": "2022-09-19T04:18:19.228Z",
                "id": "fakeid",
                "account": {
                    "id": "222222222",
                    "cdhPartyNumber": "11111111",
                    "ebsAccountNumber": "102030",
                    "name": "Red Hat",
                    "displayName": "Red Hat",
                    "status": "enabled",
                    "type": "organization",
                },
            }
        ],
    },
    {
        "id": "87654321",
        "accountRelationships": [
            {
                "emails": [{"address": "example@example.com", "status": "enabled"}],
                "accountId": "fakeid",
                "startDate": "2022-09-20T14:31:09.974Z",
                "id": "fakeid",
                "account": {
                    "id": "fakeid",
                    "cdhPartyNumber": "0000000",
                    "ebsAccountNumber": "1234567",
                    "name": "Test Org",
                    "status": "enabled",
                    "type": "organization",
                },
            }
        ],
    },
]


class TestMarketplace:
    @patch("requests.request")
    def test_timeout_exception(self, requests_mock):
        requests_mock.side_effect = requests.exceptions.ReadTimeout()
        user_api = RedHatUserApi(app_config)
        subscription_api = RedHatSubscriptionApi(app_config)

        customer_id = user_api.lookup_customer_id("example@example.com")
        assert customer_id is None
        subscription_response = subscription_api.lookup_subscription(123456, "sku")
        assert subscription_response is None
        subscription_sku = subscription_api.get_subscription_sku(123456)
        assert subscription_sku is None
        extended_subscription = subscription_api.extend_subscription(12345, 102623)
        assert extended_subscription is None
        create_subscription_response = subscription_api.create_entitlement(12345, "sku")
        assert create_subscription_response == 408

    @patch("requests.request")
    def test_user_lookup(self, requests_mock):
        user_api = RedHatUserApi(app_config)
        requests_mock.return_value.content = json.dumps(mocked_user_service_response)

        customer_id = user_api.lookup_customer_id("example@example.com")
        assert customer_id == "000000000"

        requests_mock.return_value.content = json.dumps(mocked_organization_only_response)
        customer_id = user_api.lookup_customer_id("example@example.com")
        assert customer_id is None
