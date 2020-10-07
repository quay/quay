import logging
import yaml

from abc import ABCMeta, abstractmethod
from six import add_metaclass

from jsonschema import validate, ValidationError

from util.config.schema import CONFIG_SCHEMA

logger = logging.getLogger(__name__)


class CannotWriteConfigException(Exception):
    """
    Exception raised when the config cannot be written.
    """

    pass


class SetupIncompleteException(Exception):
    """
    Exception raised when attempting to verify config that has not yet been setup.
    """

    pass


def import_yaml(config_obj, config_file):
    with open(config_file) as f:
        c = yaml.safe_load(f)
        if not c:
            logger.debug("Empty YAML config file")
            return

        if isinstance(c, str):
            raise Exception("Invalid YAML config file: " + str(c))

        for key in c.keys():
            if key.isupper():
                config_obj[key] = c[key]

    # if config_obj.get("SETUP_COMPLETE", True):
    #     try:
    #         validate(config_obj, CONFIG_SCHEMA)
    #     except ValidationError:
    #         # Todo: Change this into a real error
    #         logger.exception("Could not validate config schema")
    # else:
    #     logger.debug("Skipping config schema validation because setup is not complete")

    return config_obj


def get_yaml(config_obj):
    return yaml.safe_dump(config_obj, allow_unicode=True)


def export_yaml(config_obj, config_file):
    try:
        with open(config_file, "w") as f:
            f.write(get_yaml(config_obj))
    except IOError as ioe:
        raise CannotWriteConfigException(str(ioe))


@add_metaclass(ABCMeta)
class BaseProvider(object):
    """
    A configuration provider helps to load, save, and handle config override in the application.
    """

    @property
    def provider_id(self):
        raise NotImplementedError

    @abstractmethod
    def update_app_config(self, app_config):
        """
        Updates the given application config object with the loaded override config.
        """

    @abstractmethod
    def get_config(self):
        """
        Returns the contents of the config override file, or None if none.
        """

    @abstractmethod
    def save_config(self, config_object):
        """
        Updates the contents of the config override file to those given.
        """

    @abstractmethod
    def config_exists(self):
        """
        Returns true if a config override file exists in the config volume.
        """

    @abstractmethod
    def volume_exists(self):
        """
        Returns whether the config override volume exists.
        """

    @abstractmethod
    def volume_file_exists(self, relative_file_path):
        """
        Returns whether the file with the given relative path exists under the config override
        volume.
        """

    @abstractmethod
    def get_volume_file(self, relative_file_path, mode="r"):
        """
        Returns a Python file referring to the given path under the config override volume.
        """

    @abstractmethod
    def remove_volume_file(self, relative_file_path):
        """
        Removes the config override volume file with the given path.
        """

    @abstractmethod
    def list_volume_directory(self, path):
        """
        Returns a list of strings representing the names of the files found in the config override
        directory under the given path.

        If the path doesn't exist, returns None.
        """

    @abstractmethod
    def save_volume_file(self, flask_file, relative_file_path):
        """
        Saves the given flask file to the config override volume, with the given relative path.
        """

    @abstractmethod
    def get_volume_path(self, directory, filename):
        """
        Helper for constructing relative file paths, which may differ between providers.

        For example, kubernetes can't have subfolders in configmaps
        """

    @abstractmethod
    def get_config_root(self):
        """
        Returns the config root directory.
        """
