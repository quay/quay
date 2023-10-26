import requests
from mock import patch

from util.marketplace import RedHatSubscriptionApi, RedHatUserApi

app_config = {
    "ENTITLEMENT_RECONCILIATION_USER_ENDPOINT": "example.com",
    "ENTITLEMENT_RECONCILIATION_MARKETPLACE_ENDPOINT": "example.com",
}


@patch("requests.request")
def test_timeout_exception(requests_mock):
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
