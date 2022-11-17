import json
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
        self.unleash_features = self._get_unleash_features()
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

        self.unleash_features = self._get_unleash_features()
        for feature in self.unleash_features.values():
            self._update_config_value(feature, app_config)

        print("FEATURE_UI_V2 after", app_config["FEATURE_UI_V2"])

    def _get_unleash_features(self):
        (result, _) = get_feature_toggles(
            UNLEASH_URL,
            UNLEASH_APP_NAME,
            self.unleash_instance_id,
            self.custom_headers,
            self.custom_options,
        )

        unleash_features = {}
        for feature in result.get("features"):
            name = feature.get("name")
            unleash_features[name] = feature

        return unleash_features

    def _update_config_value(self, feature, app_config):
        config_key = feature.get("name")
        value = self._get_feature_value(feature)

        print("-----------------##----------------------")
        print("Updating config ", config_key, value)
        print("-----------------##----------------------")

        app_config[config_key] = value

    def _get_feature_value(self, feature):
        is_enabled = feature.get("enabled")
        config_value = is_enabled
        if feature.get("variants"):
            # TODO: handle multiple variants
            variant = feature.get("variants")[0].get("payload")
            variant_type = variant.get("type")
            variant_value = variant.get("value")
            if variant_type == "json":
                variant_value = json.loads(variant_value)
            config_value = variant_value
        return config_value

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
        new_features = self._get_unleash_features()
        for old_feature_name in self.unleash_features:
            # Removed a feature
            if old_feature_name not in new_features:
                return True

        for feature_name in new_features:
            # Added a feature
            if feature_name not in self.unleash_features:
                return True

        # look for changes in value
        for feature_name in new_features:
            # TODO multiple variants
            new_value = self._get_feature_value(new_features[feature_name])
            old_value = self._get_feature_value(self.unleash_features[feature_name])
            # TODO nested
            # Updated feature
            if new_value != old_value:
                return True

        return False

    def _restart_process(self):
        pass
