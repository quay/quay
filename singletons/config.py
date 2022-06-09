import json
import logging
import os
from functools import partial

from _init import OVERRIDE_CONFIG_DIRECTORY, IS_TESTING, IS_KUBERNETES
from singletons.app import _app as app
from util import get_app_url
from util.config.configutil import generate_secret_key
from util.config.provider import get_config_provider


OVERRIDE_CONFIG_KEY = "QUAY_OVERRIDE_CONFIG"

logger = logging.getLogger(__name__)

config_provider = get_config_provider(
    OVERRIDE_CONFIG_DIRECTORY,
    "config.yaml",
    "config.py",
    testing=IS_TESTING,
    kubernetes=IS_KUBERNETES,
)

if IS_TESTING:
    from test.testconfig import TestConfig

    logger.debug("Loading test config.")
    app.config.from_object(TestConfig())
else:
    from config import DefaultConfig

    logger.debug("Loading default config.")
    app.config.from_object(DefaultConfig())

# Load the override config via the provider.
config_provider.update_app_config(app.config)

# Update any configuration found in the override environment variable.
environ_config = json.loads(os.environ.get(OVERRIDE_CONFIG_KEY, "{}"))
app.config.update(environ_config)

# Allow user to define a custom storage preference for the local instance.
_distributed_storage_preference = os.environ.get("QUAY_DISTRIBUTED_STORAGE_PREFERENCE", "").split()
if _distributed_storage_preference:
    app.config["DISTRIBUTED_STORAGE_PREFERENCE"] = _distributed_storage_preference

# Generate a secret key if none was specified.
if app.config["SECRET_KEY"] is None:
    logger.debug("Generating in-memory secret key")
    app.config["SECRET_KEY"] = generate_secret_key()

# If the "preferred" scheme is https, then http is not allowed. Therefore, ensure we have a secure
# session cookie.
if app.config["PREFERRED_URL_SCHEME"] == "https" and not app.config.get(
    "FORCE_NONSECURE_SESSION_COOKIE", False
):
    app.config["SESSION_COOKIE_SECURE"] = True

logger.debug("Loaded config", extra={"config": app.config})

get_app_url = partial(get_app_url, app.config)

app_config = app.config
