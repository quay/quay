import json
import unittest

import requests
from mock import patch

from app import app
from initdb import finished_database_for_testing, setup_database_for_testing
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

mocked_subscription_response = [
    {
        "id": 1,
        "masterEndSystemName": "SUBSCRIPTION",
        "createdEndSystemName": "SUBSCRIPTION",
        "createdDate": 1704721749000,
        "lastUpdateEndSystemName": "SUBSCRIPTION",
        "lastUpdateDate": 1704721749000,
        "installBaseStartDate": 1704672000000,
        "installBaseEndDate": 1707350399000,
        "webCustomerId": 12345,
        "quantity": 1,
        "effectiveStartDate": 1704672000000,
        "effectiveEndDate": 1707350399000,
    },
    {
        "id": 2,
        "masterEndSystemName": "SUBSCRIPTION",
        "createdEndSystemName": "SUBSCRIPTION",
        "createdDate": 1705494625000,
        "lastUpdateEndSystemName": "SUBSCRIPTION",
        "lastUpdateDate": 1705494625000,
        "installBaseStartDate": 1705467600000,
        "installBaseEndDate": 1708145999000,
        "webCustomerId": 12345,
        "quantity": 2,
        "effectiveStartDate": 1705467600000,
        "effectiveEndDate": 1708145999000,
    },
    {
        "id": 3,
        "masterEndSystemName": "SUBSCRIPTION",
        "createdEndSystemName": "SUBSCRIPTION",
        "createdDate": 1610888071,
        "lastUpdateEndSystemName": "SUBSCRIPTION",
        "lastUpdateDate": 1610888071,
        "installBaseStartDate": 1610888071,
        "installBaseEndDate": 1610888071,
        "webCustomerId": 12345,
        "quantity": 1,
        "effectiveStartDate": 1610888071,
        "effectiveEndDate": 1610888071,
    },
]


class TestMarketplace(unittest.TestCase):
    def setUp(self):
        setup_database_for_testing(self)

    def tearDown(self):
        finished_database_for_testing(self)

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
        assert customer_id == 000000000

        requests_mock.return_value.content = json.dumps(mocked_organization_only_response)
        customer_id = user_api.lookup_customer_id("example@example.com")
        assert customer_id is None

    @patch("requests.request")
    def test_subscription_lookup(self, requests_mock):
        subscription_api = RedHatSubscriptionApi(app_config)
        requests_mock.return_value.content = json.dumps(mocked_subscription_response)

        subscriptions = subscription_api.lookup_subscription(12345, "some_sku")
        assert len(subscriptions) == 2

    @patch("requests.request")
    def test_list_subscriptions(self, requests_mock):
        subscription_api = RedHatSubscriptionApi(app_config)
        requests_mock.return_value.content = json.dumps(mocked_subscription_response)

        subscriptions = subscription_api.get_list_of_subscriptions(
            12345, convert_to_stripe_plans=True
        )

        assert len(subscriptions) == 6
