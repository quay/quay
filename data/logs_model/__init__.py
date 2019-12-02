import logging

from data.logs_model.table_logs_model import TableLogsModel
from data.logs_model.document_logs_model import DocumentLogsModel
from data.logs_model.combined_model import CombinedLogsModel

logger = logging.getLogger(__name__)


def _transition_model(*args, **kwargs):
    return CombinedLogsModel(DocumentLogsModel(*args, **kwargs), TableLogsModel(*args, **kwargs),)


_LOG_MODELS = {
    "database": TableLogsModel,
    "transition_reads_both_writes_es": _transition_model,
    "elasticsearch": DocumentLogsModel,
}

_PULL_LOG_KINDS = {"pull_repo", "repo_verb"}


class LogsModelProxy(object):
    def __init__(self):
        self._model = None

    def initialize(self, model):
        self._model = model
        logger.info("===============================")
        logger.info("Using logs model `%s`", self._model)
        logger.info("===============================")

    def __getattr__(self, attr):
        if not self._model:
            raise AttributeError("LogsModelProxy is not initialized")
        return getattr(self._model, attr)


logs_model = LogsModelProxy()


def configure(app_config):
    logger.debug("Configuring log lodel")
    model_name = app_config.get("LOGS_MODEL", "database")
    model_config = app_config.get("LOGS_MODEL_CONFIG", {})

    def should_skip_logging(kind_name, namespace_name, is_free_namespace):
        if namespace_name and namespace_name in app_config.get("DISABLED_FOR_AUDIT_LOGS", {}):
            return True

        if kind_name in _PULL_LOG_KINDS:
            if namespace_name and namespace_name in app_config.get("DISABLED_FOR_PULL_LOGS", {}):
                return True

            if app_config.get("FEATURE_DISABLE_PULL_LOGS_FOR_FREE_NAMESPACES"):
                if is_free_namespace:
                    return True

        return False

    model_config["should_skip_logging"] = should_skip_logging
    logs_model.initialize(_LOG_MODELS[model_name](**model_config))
