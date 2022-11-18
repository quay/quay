import json
import os
import signal
import logging
import time
import subprocess
from flask_login import current_user

from gevent import Greenlet

import typing as t


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
        th = Greenlet.spawn(run=self._poll_changes)

    @property
    def provider_id(self):
        return "unleash"

    def update_app_config(self, app_config):
        print("Called update_app_config", app_config)
        super(UnleashConfigProvider, self).update_app_config(app_config)

        self.unleash_features = self._get_unleash_features()
        for feature in self.unleash_features.values():
            self._update_config_value(feature, app_config)

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
        if value is not None:
            app_config[config_key] = value

    def _get_feature_value(self, feature):
        is_enabled = feature.get("enabled")
        has_variants = len(feature.get("variants")) > 0

        if not has_variants:
            # boolean value
            return is_enabled

        if is_enabled and has_variants:
            # TODO: handle multiple variants
            # String or JSON
            variant = feature.get("variants")[0].get("payload")
            variant_type = variant.get("type")
            variant_value = variant.get("value")
            if variant_type == "json":
                variant_value = json.loads(variant_value)
            return variant_value
        else:
            # has variants but is disabled
            return None

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
        print("======================================")
        print("Restarting supervisord...")
        print("---------------------------------------------------")

        supervisord_pid = subprocess.getoutput("supervisorctl -c conf/supervisord.conf pid")
        print("SUPERVISORD_PID = ", supervisord_pid)
        os.kill(int(supervisord_pid), signal.SIGHUP)


class UnleashConfig(dict):
    def __init__(self, flask_config, unleash_client):
        super().__init__()
        self.flask_config = flask_config
        self.unleash_client = unleash_client
        for key in flask_config:
            super().__setitem__(key, flask_config[key])

    def from_envvar(self, variable_name: str, silent: bool = False) -> bool:
        return self.flask_config.from_envvar(variable_name, silent)

    def from_prefixed_env(
        self, prefix: str = "FLASK", *, loads: t.Callable[[str], t.Any] = json.loads
    ) -> bool:
        return self.flask_config.from_prefixed_env(prefix, loads)

    def from_pyfile(self, filename: str, silent: bool = False) -> bool:
        return self.flask_config.from_pyfile(filename, silent)

    def from_object(self, obj: t.Union[object, str]) -> None:
        return self.flask_config.from_object(obj)

    def from_file(
        self,
        filename: str,
        load: t.Callable[[t.IO[t.Any]], t.Mapping],
        silent: bool = False,
    ) -> bool:
        return self.flask_config.from_file(filename, load, silent)

    def from_mapping(
        self, mapping: t.Optional[t.Mapping[str, t.Any]] = None, **kwargs: t.Any
    ) -> bool:
        return self.flask_config.from_mapping(mapping)

    def get_namespace(
        self, namespace: str, lowercase: bool = True, trim_namespace: bool = True
    ) -> t.Dict[str, t.Any]:
        return self.flask_config.get_namespace(namespace, lowercase, trim_namespace)

    def __getitem__(self, key):
        return self.flask_config[key]

    def get(self, key, default_value=None):
        print(f"GET CONFIG {key}")
        print("Current User", current_user)
        return self.flask_config.get(key, default_value)

    def __setitem__(self, key, value):
        self.flask_config[key] = value

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {dict.__repr__(self)}>"
