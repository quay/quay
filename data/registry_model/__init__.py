import os
import logging

from data.registry_model.registry_pre_oci_model import pre_oci_model
from data.registry_model.registry_oci_model import oci_model
from data.registry_model.modelsplitter import SplitModel

logger = logging.getLogger(__name__)


class RegistryModelProxy(object):
    def __init__(self):
        self._model = oci_model if os.getenv("OCI_DATA_MODEL") == "true" else pre_oci_model

    def setup_split(self, oci_model_proportion, oci_whitelist, v22_whitelist, upgrade_mode):
        if os.getenv("OCI_DATA_MODEL") == "true":
            return

        if upgrade_mode == "complete":
            logger.info("===============================")
            logger.info("Full V2_2 + OCI model is enabled")
            logger.info("===============================")
            self._model = oci_model
            return

        logger.info("===============================")
        logger.info(
            "Split registry model: OCI %s proportion and whitelist `%s` and V22 whitelist `%s`",
            oci_model_proportion,
            oci_whitelist,
            v22_whitelist,
        )
        logger.info("===============================")
        self._model = SplitModel(
            oci_model_proportion, oci_whitelist, v22_whitelist, upgrade_mode == "post-oci-rollout"
        )

    def set_for_testing(self, use_oci_model):
        self._model = oci_model if use_oci_model else pre_oci_model
        logger.debug("Changed registry model to `%s` for testing", self._model)

    def __getattr__(self, attr):
        return getattr(self._model, attr)


registry_model = RegistryModelProxy()
logger.info("===============================")
logger.info("Using registry model `%s`", registry_model._model)
logger.info("===============================")
