import os
import logging
from UnleashClient import UnleashClient
from UnleashClient.api.features import get_feature_toggles

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
        self.unleash_instance_id = "unleash-python-client"
        self.app_name = UNLEASH_APP_NAME
        self.custom_options = {}

        self.custom_headers = {"Authorization": UNLEASH_API_TOKEN}
        self.unleash_client = UnleashClient(
            url=UNLEASH_URL,
            instance_id=self.unleash_instance_id,
            app_name=UNLEASH_APP_NAME,
            environment=UNLEASH_ENVIRONMENT,
            custom_headers=self.custom_headers,
        )
        self.unleash_client.initialize_client()

        self.features = None

    @property
    def provider_id(self):
        return "unleash"

    def update_app_config(self, app_config):
        self.features = self._get_unleash_features()
        for feature, value in self.features.items():
            self._update_config_value(feature, value, app_config)

    def _get_unleash_features(self):
        (result, _) = get_feature_toggles(
            UNLEASH_URL,
            UNLEASH_APP_NAME,
            self.unleash_instance_id,
            self.custom_headers,
            self.custom_options,
        )

        print("==========================================")
        logger.info(result)
        print("------------------------------------------")

        # Iterate through raw features and return a dict of enabled features
        features = {}
        for feature in result["features"]:
            name = feature["name"]
            is_enabled = feature["enabled"]
            features[name] = is_enabled
        return features

    def _update_config_value(self, config_key, config_value, app_config):
        # TODO: nested configs
        # TODO: non-boolean configs
        app_config[config_key] = config_value

    def save_config(self, config_object):
        pass

    def remove_volume_file(self, relative_file_path):
        pass

    def save_volume_file(self, flask_file, relative_file_path):
        pass
