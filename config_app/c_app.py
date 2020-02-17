import os
import logging

from flask import Flask

from data import database, model
from util.config.superusermanager import SuperUserManager
from util.ipresolver import NoopIPResolver

from config_app._init_config import ROOT_DIR, IS_KUBERNETES
from config_app.config_util.config import get_config_provider
from util.security.instancekeys import InstanceKeys

app = Flask(__name__)

logger = logging.getLogger(__name__)

OVERRIDE_CONFIG_DIRECTORY = os.path.join(ROOT_DIR, "config_app/conf/stack")
INIT_SCRIPTS_LOCATION = "/conf/init/"

is_testing = "TEST" in os.environ
is_kubernetes = IS_KUBERNETES

logger.debug("Configuration is on a kubernetes deployment: %s" % IS_KUBERNETES)

config_provider = get_config_provider(
    OVERRIDE_CONFIG_DIRECTORY, "config.yaml", "config.py", testing=is_testing
)

if is_testing:
    from test.testconfig import TestConfig

    logger.debug("Loading test config.")
    app.config.from_object(TestConfig())
else:
    from config import DefaultConfig

    logger.debug("Loading default config.")
    app.config.from_object(DefaultConfig())
    app.teardown_request(database.close_db_filter)

# Load the override config via the provider.
config_provider.update_app_config(app.config)
superusers = SuperUserManager(app)
ip_resolver = NoopIPResolver()
instance_keys = InstanceKeys(app)

model.config.app_config = app.config
