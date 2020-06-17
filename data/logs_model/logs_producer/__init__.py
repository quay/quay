import logging


logger = logging.getLogger(__name__)


class LogSendException(Exception):
    """
    A generic error when sending the logs to its destination.

    e.g. Kinesis, Kafka, Elasticsearch, ...
    """

    pass


class LogProducerProxy(object):
    def __init__(self):
        self._model = None

    def initialize(self, model):
        self._model = model
        logger.debug("Using producer `%s`", self._model)

    def __getattr__(self, attr):
        if not self._model:
            raise AttributeError("LogsModelProxy is not initialized")
        return getattr(self._model, attr)
