import json
import io

from util.config.provider.baseprovider import BaseProvider

REAL_FILES = ["test/data/test.pem"]


class TestConfigProvider(BaseProvider):
    """
    Implementation of the config provider for testing.

    Everything is kept in-memory instead on the real file system.
    """

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

    def config_exists(self):
        return "config.yaml" in self.files

    def volume_file_exists(self, filename):
        if filename in REAL_FILES:
            return True

        return filename in self.files

    def get_volume_file(self, filename, mode="r"):
        if filename in REAL_FILES:
            return open(filename, mode=mode)

        return io.BytesIO(self.files[filename])

    def reset_for_test(self):
        self._config["SUPER_USERS"] = ["devtable"]
        self.files = {}
