import os
import logging

from util.config.provider.baseprovider import export_yaml, CannotWriteConfigException
from util.config.provider.basefileprovider import BaseFileProvider


logger = logging.getLogger(__name__)


def _ensure_parent_dir(filepath):
    """
    Ensures that the parent directory of the given file path exists.
    """
    try:
        parentpath = os.path.abspath(os.path.join(filepath, os.pardir))
        if not os.path.isdir(parentpath):
            os.makedirs(parentpath)
    except IOError as ioe:
        raise CannotWriteConfigException(str(ioe))


class FileConfigProvider(BaseFileProvider):
    """
    Implementation of the config provider that reads and writes the data from/to the file system.
    """

    def __init__(self, config_volume, yaml_filename, py_filename):
        super(FileConfigProvider, self).__init__(config_volume, yaml_filename, py_filename)

    @property
    def provider_id(self):
        return "file"

    def save_config(self, config_obj):
        export_yaml(config_obj, self.yaml_path)

    def remove_volume_file(self, relative_file_path):
        filepath = os.path.join(self.config_volume, relative_file_path)
        os.remove(filepath)

    def save_volume_file(self, flask_file, relative_file_path):
        filepath = os.path.join(self.config_volume, relative_file_path)
        _ensure_parent_dir(filepath)

        # Write the file.
        try:
            flask_file.save(filepath)
        except IOError as ioe:
            raise CannotWriteConfigException(str(ioe))

        return filepath
