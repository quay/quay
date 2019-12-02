import os
import logging

from config_app.config_util.config.baseprovider import (
    BaseProvider,
    import_yaml,
    export_yaml,
    CannotWriteConfigException,
)

logger = logging.getLogger(__name__)


class BaseFileProvider(BaseProvider):
    """ Base implementation of the config provider that reads the data from the file system. """

    def __init__(self, config_volume, yaml_filename, py_filename):
        self.config_volume = config_volume
        self.yaml_filename = yaml_filename
        self.py_filename = py_filename

        self.yaml_path = os.path.join(config_volume, yaml_filename)
        self.py_path = os.path.join(config_volume, py_filename)

    def update_app_config(self, app_config):
        if os.path.exists(self.py_path):
            logger.debug("Applying config file: %s", self.py_path)
            app_config.from_pyfile(self.py_path)

        if os.path.exists(self.yaml_path):
            logger.debug("Applying config file: %s", self.yaml_path)
            import_yaml(app_config, self.yaml_path)

    def get_config(self):
        if not self.config_exists():
            return None

        config_obj = {}
        import_yaml(config_obj, self.yaml_path)
        return config_obj

    def config_exists(self):
        return self.volume_file_exists(self.yaml_filename)

    def volume_exists(self):
        return os.path.exists(self.config_volume)

    def volume_file_exists(self, filename):
        return os.path.exists(os.path.join(self.config_volume, filename))

    def get_volume_file(self, filename, mode="r"):
        return open(os.path.join(self.config_volume, filename), mode=mode)

    def get_volume_path(self, directory, filename):
        return os.path.join(directory, filename)

    def list_volume_directory(self, path):
        dirpath = os.path.join(self.config_volume, path)
        if not os.path.exists(dirpath):
            return None

        if not os.path.isdir(dirpath):
            return None

        return os.listdir(dirpath)

    def requires_restart(self, app_config):
        file_config = self.get_config()
        if not file_config:
            return False

        for key in file_config:
            if app_config.get(key) != file_config[key]:
                return True

        return False
