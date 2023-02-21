import logging

from splunklib import client

from data.logs_model.logs_producer import LogSendException
from data.logs_model.logs_producer.interface import LogProducerInterface

logger = logging.getLogger(__name__)


class SplunkLogsProducer(LogProducerInterface):
    """
    Log producer for writing log entries to Splunk
    This implementation writes directly to Splunk without a streaming/queueing service.
    """

    def __init__(
        self,
        host,
        port,
        bearer_token,
        url_scheme="https",
        verify_ssl=True,
        index_prefix=None,
    ):
        try:
            service = client.connect(
                host=host, port=port, token=bearer_token, scheme=url_scheme, verify=verify_ssl
            )
        except Exception as ex:
            logger.exception("Failed to connect to Splunk instance %s", ex)
            raise ex
        try:
            self.index = service.indexes[index_prefix]
            logger.info("splunk index %s", self.index)
        except KeyError:
            self.index = service.indexes.create(index_prefix)

    def send(self, log):
        try:
            self.index.submit(log, sourcetype="access_combined", host="quay")
        except Exception as e:
            logger.exception("SplunkLogsProducer exception sending log to Splunk: %s", e)
            raise LogSendException("SplunkLogsProducer exception sending log to Splunk: %s" % e)
