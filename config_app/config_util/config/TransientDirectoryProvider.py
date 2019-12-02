import os

from shutil import copytree
from backports.tempfile import TemporaryDirectory

from config_app.config_util.config.fileprovider import FileConfigProvider

OLD_CONFIG_SUBDIR = "old/"


class TransientDirectoryProvider(FileConfigProvider):
    """ Implementation of the config provider that reads and writes the data
      from/to the file system, only using temporary directories,
      deleting old dirs and creating new ones as requested.
  """

    def __init__(self, config_volume, yaml_filename, py_filename):
        # Create a temp directory that will be cleaned up when we change the config path
        # This should ensure we have no "pollution" of different configs:
        # no uploaded config should ever affect subsequent config modifications/creations
        temp_dir = TemporaryDirectory()
        self.temp_dir = temp_dir
        self.old_config_dir = None
        super(TransientDirectoryProvider, self).__init__(temp_dir.name, yaml_filename, py_filename)

    @property
    def provider_id(self):
        return "transient"

    def new_config_dir(self):
        """
    Update the path with a new temporary directory, deleting the old one in the process
    """
        self.temp_dir.cleanup()
        temp_dir = TemporaryDirectory()

        self.config_volume = temp_dir.name
        self.temp_dir = temp_dir
        self.yaml_path = os.path.join(temp_dir.name, self.yaml_filename)

    def create_copy_of_config_dir(self):
        """
    Create a directory to store loaded/populated configuration (for rollback if necessary)
    """
        if self.old_config_dir is not None:
            self.old_config_dir.cleanup()

        temp_dir = TemporaryDirectory()
        self.old_config_dir = temp_dir

        # Python 2.7's shutil.copy() doesn't allow for copying to existing directories,
        # so when copying/reading to the old saved config, we have to talk to a subdirectory,
        # and use the shutil.copytree() function
        copytree(self.config_volume, os.path.join(temp_dir.name, OLD_CONFIG_SUBDIR))

    def get_config_dir_path(self):
        return self.config_volume

    def get_old_config_dir(self):
        if self.old_config_dir is None:
            raise Exception("Cannot return a configuration that  was no old configuration")

        return os.path.join(self.old_config_dir.name, OLD_CONFIG_SUBDIR)
