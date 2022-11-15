from util.config.provider.fileprovider import FileConfigProvider
from util.config.provider.testprovider import TestConfigProvider
from util.config.provider.k8sprovider import KubernetesConfigProvider
from util.config.provider.unleashprovider import UnleashConfigProvider


def get_config_provider(
    config_volume, yaml_filename, py_filename, testing=False, kubernetes=False, unleash=False
):
    """
    Loads and returns the config provider for the current environment.
    """
    if testing:
        return TestConfigProvider()

    if unleash:
        return UnleashConfigProvider(config_volume, yaml_filename, py_filename)

    if kubernetes:
        return KubernetesConfigProvider(config_volume, yaml_filename, py_filename)

    return FileConfigProvider(config_volume, yaml_filename, py_filename)
