import os
import logging
from UnleashClient import UnleashClient
from UnleashClient.api.features import get_features

from util.config.provider.basefileprovider import BaseFileProvider

logger = logging.getLogger(__name__)

UNLEASH_URL = os.environ.get("UNLEASH_URL", "")
UNLEASH_APP_NAME = os.environ.get("UNLEASH_APP_NAME", "quay")
UNLEASH_ENVIRONMENT = os.environ.get("UNLEASH_ENVIRONMENT", "development")
UNLEASH_API_TOKEN = os.environ.get("UNLEASH_API_TOKEN", "")
UNLEASH_REFRESH_INTERVAL = os.environ.get("UNLEASH_REFRESH_INTERVAL", 60)


class UnleashConfigProvider(BaseFileProvider):
    """
    Implementation of the config provider that reads and writes configuration data from an Unleash server
    Requires UNLEASH_URL environment variable to be set
    """

    def __init__(self, config_volume, yaml_filename, py_filename):
        super(UnleashConfigProvider, self).__init__(config_volume, yaml_filename, py_filename)

        custom_headers = {"Authorization": UNLEASH_API_TOKEN}
        self.unleash_client = UnleashClient(
            url=UNLEASH_URL,
            app_name=UNLEASH_APP_NAME,
            environment=UNLEASH_ENVIRONMENT,
            custom_headers=custom_headers,
        )
        self.unleash_client.initialize_client()

    @property
    def provider_id(self):
        return "unleash"

    def update_app_config(self, app_config):
        features = self._get_unleash_features()
        for feature in features:
            self.update_config_value(feature, app_config)

    def _get_unleash_features(self):
        unleash_features = get_features()
        logger.info(unleash_features)
        for feature_name in unleash_features:
            # update the config
            # this could possibliy have variants
            pass

    def update_config_value(self, feature, app_config):
        pass

    def save_config(self, config_obj):
        pass

    def remove_volume_file(self, relative_file_path):
        pass

    def save_volume_file(self, flask_file, relative_file_path):
        pass
