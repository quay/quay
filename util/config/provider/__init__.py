from util.config.provider.fileprovider import FileConfigProvider
from util.config.provider.testprovider import TestConfigProvider
from util.config.provider.k8sprovider import KubernetesConfigProvider


def get_config_provider(config_volume, yaml_filename, py_filename, testing=False, kubernetes=False):
    """
    Loads and returns the config provider for the current environment.
    """
    if testing:
        return TestConfigProvider()

    if kubernetes:
        return KubernetesConfigProvider(config_volume, yaml_filename, py_filename)

    return FileConfigProvider(config_volume, yaml_filename, py_filename)
