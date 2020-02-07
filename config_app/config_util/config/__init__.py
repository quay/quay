import base64
import os

from config_app.config_util.config.fileprovider import FileConfigProvider
from config_app.config_util.config.testprovider import TestConfigProvider
from config_app.config_util.config.TransientDirectoryProvider import TransientDirectoryProvider
from util.config.validator import EXTRA_CA_DIRECTORY, EXTRA_CA_DIRECTORY_PREFIX


def get_config_provider(config_volume, yaml_filename, py_filename, testing=False):
    """
    Loads and returns the config provider for the current environment.
    """

    if testing:
        return TestConfigProvider()

    return TransientDirectoryProvider(config_volume, yaml_filename, py_filename)


def get_config_as_kube_secret(config_path):
    data = {}

    # Kubernetes secrets don't have sub-directories, so for the extra_ca_certs dir
    # we have to put the extra certs in with a prefix, and then one of our init scripts
    # (02_get_kube_certs.sh) will expand the prefixed certs into the equivalent directory
    # so that they'll be installed correctly on startup by the certs_install script
    certs_dir = os.path.join(config_path, EXTRA_CA_DIRECTORY)
    if os.path.exists(certs_dir):
        for extra_cert in os.listdir(certs_dir):
            file_path = os.path.join(certs_dir, extra_cert)
            with open(file_path, "rb") as f:
                data[EXTRA_CA_DIRECTORY_PREFIX + extra_cert] = base64.b64encode(f.read()).decode()

    for name in os.listdir(config_path):
        file_path = os.path.join(config_path, name)
        if not os.path.isdir(file_path):
            with open(file_path, "rb") as f:
                data[name] = base64.b64encode(f.read()).decode()

    return data
