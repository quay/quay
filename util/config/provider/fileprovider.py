import logging

from util.config.provider.basefileprovider import BaseFileProvider


logger = logging.getLogger(__name__)


class FileConfigProvider(BaseFileProvider):
    """
    Implementation of the config provider that reads and writes the data from/to the file system.
    """

    def __init__(self, config_volume, yaml_filename, py_filename):
        super(FileConfigProvider, self).__init__(config_volume, yaml_filename, py_filename)

    @property
    def provider_id(self):
        return "file"
