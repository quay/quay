import json
import io
import os
from datetime import datetime, timedelta

from util.config.provider.baseprovider import BaseProvider

REAL_FILES = ["test/data/signing-private.gpg", "test/data/signing-public.gpg", "test/data/test.pem"]


class TestConfigProvider(BaseProvider):
    """
    Implementation of the config provider for testing.

    Everything is kept in-memory instead on the real file system.
    """

    def get_config_root(self):
        raise Exception("Test Config does not have a config root")

    def __init__(self):
        self.clear()

    def clear(self):
        self.files = {}
        self._config = {}

    @property
    def provider_id(self):
        return "test"

    def update_app_config(self, app_config):
        self._config = app_config

    def get_config(self):
        if not "config.yaml" in self.files:
            return None

        return json.loads(self.files.get("config.yaml", "{}"))

    def save_config(self, config_obj):
        self.files["config.yaml"] = json.dumps(config_obj)

    def config_exists(self):
        return "config.yaml" in self.files

    def volume_exists(self):
        return True

    def volume_file_exists(self, filename):
        if filename in REAL_FILES:
            return True

        return filename in self.files

    def save_volume_file(self, flask_file, filename):
        self.files[filename] = flask_file.read()

    def get_volume_file(self, filename, mode="r"):
        if filename in REAL_FILES:
            return open(filename, mode=mode)

        return io.BytesIO(self.files[filename])

    def remove_volume_file(self, filename):
        self.files.pop(filename, None)

    def list_volume_directory(self, path):
        paths = []
        for filename in self.files:
            if filename.startswith(path):
                paths.append(filename[len(path) + 1 :])

        return paths

    def reset_for_test(self):
        self._config["SUPER_USERS"] = ["devtable"]
        self.files = {}

    def get_volume_path(self, directory, filename):
        return os.path.join(directory, filename)
