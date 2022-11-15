import os
import logging
import json
import base64
import time

from UnleashClient import UnleashClient

from io import StringIO
from requests import Request, Session

from util.config.provider.baseprovider import CannotWriteConfigException, get_yaml
from util.config.provider.basefileprovider import BaseFileProvider


logger = logging.getLogger(__name__)

UNLEASH_URL = os.environ.get("UNLEASH_URL", "")
UNLEASH_APP_NAME = os.environ.get("UNLEASH_APP_NAME", "quay")
UNLEASH_ENVIRONMENT = os.environ.get("UNLEASH_ENVIRONMENT", "dev")
UNLEASH_API_TOKEN = os.environ.get("UNLEASH_API_TOKEN", "")
UNLEASH_REFRESH_INTERVAL = os.environ.get("UNLEASH_REFRESH_INTERVAL", 60)

unleash_args = {
    "url": UNLEASH_URL,
    "app_name": UNLEASH_APP_NAME,
    "environment": UNLEASH_ENVIRONMENT,
    "custom_headers": {"Authorization": UNLEASH_API_TOKEN},
    "refresh_interval": UNLEASH_REFRESH_INTERVAL,
}


class UnleashConfigProvider(BaseFileProvider):
    """
    Implementation of the config provider that reads and writes configuration data from an Unleash server
    """

    def __init__(
        self,
        unleash_url,
        unleash_environment,
        unleash_api_token,
    ):
        custom_headers = {"Authorization": unleash_api_token}
        self.unleash_client = UnleashClient(
            url=unleash_url, environment=unleash_environment, custom_headers=custom_headers
        )
        self.unleash_client.initialize_client()

    @property
    def provider_id(self):
        return "unleash"

    def update_app_config(self, app_config):
        features = self._get_unleash_features()
        for feature in features:
            self.update_config_value(feature, app_config)

    def _get_unleash_features():
        return {}

    def update_config_value(feature, app_config):
        pass

    def save_config(self, config_obj):
        pass
