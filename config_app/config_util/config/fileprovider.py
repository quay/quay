import os
import logging

from config_app.config_util.config.baseprovider import export_yaml, CannotWriteConfigException
from config_app.config_util.config.basefileprovider import BaseFileProvider

logger = logging.getLogger(__name__)


def _ensure_parent_dir(filepath):
    """ Ensures that the parent directory of the given file path exists. """
    try:
        parentpath = os.path.abspath(os.path.join(filepath, os.pardir))
        if not os.path.isdir(parentpath):
            os.makedirs(parentpath)
    except IOError as ioe:
        raise CannotWriteConfigException(str(ioe))


class FileConfigProvider(BaseFileProvider):
    """ Implementation of the config provider that reads and writes the data
      from/to the file system. """

    def __init__(self, config_volume, yaml_filename, py_filename):
        super(FileConfigProvider, self).__init__(config_volume, yaml_filename, py_filename)

    @property
    def provider_id(self):
        return "file"

    def save_config(self, config_obj):
        export_yaml(config_obj, self.yaml_path)

    def write_volume_file(self, filename, contents):
        filepath = os.path.join(self.config_volume, filename)
        _ensure_parent_dir(filepath)

        try:
            with open(filepath, mode="w") as f:
                f.write(contents)
        except IOError as ioe:
            raise CannotWriteConfigException(str(ioe))

        return filepath

    def remove_volume_file(self, filename):
        filepath = os.path.join(self.config_volume, filename)
        os.remove(filepath)

    def save_volume_file(self, filename, flask_file):
        filepath = os.path.join(self.config_volume, filename)
        _ensure_parent_dir(filepath)

        # Write the file.
        try:
            flask_file.save(filepath)
        except IOError as ioe:
            raise CannotWriteConfigException(str(ioe))

        return filepath
