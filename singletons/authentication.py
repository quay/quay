from data.users import UserAuthentication
from singletons.app import _app
from singletons.config import OVERRIDE_CONFIG_DIRECTORY, config_provider

authentication = UserAuthentication(_app, config_provider, OVERRIDE_CONFIG_DIRECTORY)
