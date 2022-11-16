import os
import logging
import threading
import time

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
            cache_directory="/quay-registry",  # TODO make generic
        )
        self.unleash_client.initialize_client()
        self.features = self._get_unleash_features()
        self.feature_names = self._get_unleash_feature_names()
        self.poll_interval = 15  # TODO make it configurable
        # start the polling thread
        # th = threading.Thread(target=self._poll_changes)
        # th.start()

    @property
    def provider_id(self):
        return "unleash"

    def update_app_config(self, app_config):
        print("Called update_app_config", app_config)
        super(UnleashConfigProvider, self).update_app_config(app_config)

        print("FEATURE_UI_V2 before", app_config["FEATURE_UI_V2"])

        self.features = self._get_unleash_features()
        for feature, value in self.features.items():
            self._update_config_value(feature, value, app_config)

        print("FEATURE_UI_V2 after", app_config["FEATURE_UI_V2"])

    def _get_unleash_features(self):
        (result, _) = get_feature_toggles(
            UNLEASH_URL,
            UNLEASH_APP_NAME,
            self.unleash_instance_id,
            self.custom_headers,
            self.custom_options,
        )

        print("====================##====================")
        print(result)
        print("-------------------##---------------------")

        # Iterate through raw features and return a dict of enabled features
        features = {}
        for feature in result.get("features"):
            name = feature.get("name")
            is_enabled = feature.get("enabled")
            if name:
                features[name] = is_enabled
        return features

    def _update_config_value(self, config_key, config_value, app_config):
        # TODO: nested configs
        # TODO: non-boolean configs
        print("Updating config value")
        app_config[config_key] = config_value

    def save_config(self, config_object):
        print("Called save_config", config_object)
        super(UnleashConfigProvider, self).save_config(config_object)

    def remove_volume_file(self, relative_file_path):
        print("remove_volume_file", relative_file_path)
        super(UnleashConfigProvider, self).remove_volume_file(relative_file_path)

    def save_volume_file(self, flask_file, relative_file_path):
        print("save_volume_file", flask_file, relative_file_path)
        super(UnleashConfigProvider, self).save_volume_file(flask_file, relative_file_path)

    def _poll_changes(self):
        while True:
            time.sleep(self.poll_interval)
            try:
                print("polling for config changes in unleash")
                if self._is_config_changed():
                    self._restart_process()
            except Exception as e:
                logger.error(e)

    def _is_config_changed(self):
        return False

    def _restart_process(self):
        pass
