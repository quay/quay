import os
import logging

from data.registry_model.registry_oci_model import oci_model

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
