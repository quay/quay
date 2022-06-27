import logging

from data.registry_model.registry_oci_model import oci_model
from singletons.config import app_config

logger = logging.getLogger(__name__)


class RegistryModelProxy(object):
    def __init__(self):
        self._model = oci_model

    def __getattr__(self, attr):
        return getattr(self._model, attr)

    def set_id_hash_salt(self, hash_salt):
        self._model.set_id_hash_salt(hash_salt)


registry_model = RegistryModelProxy()
logger.info("===============================")
logger.info("Using registry model `%s`", registry_model._model)
logger.info("===============================")

# NOTE: We re-use the page token key here as this is just to obfuscate IDs for V1, and
# does not need to actually be secure.
registry_model.set_id_hash_salt(app_config.get("PAGE_TOKEN_KEY"))
