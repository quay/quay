import logging

from elasticsearch.exceptions import TransportError
from elastic_transport import ApiError

from data.logs_model.logs_producer import LogSendException
from data.logs_model.logs_producer.interface import LogProducerInterface

logger = logging.getLogger(__name__)


class ElasticsearchLogsProducer(LogProducerInterface):
    """
    Log producer writing log entries to Elasticsearch.

    This implementation writes directly to Elasticsearch without a streaming/queueing service.
    """

    def send(self, logentry):
        try:
            logentry.save()
        except TransportError as ex:
            logger.exception("ElasticsearchLogsProducer error sending log to Elasticsearch: %s", ex)
            raise LogSendException(
                "ElasticsearchLogsProducer error sending log to Elasticsearch: %s" % ex
            )
        except ApiError as ex:
            logger.exception(
                "ElasticsearchLogsProducer Elasticsearch error from an HTTP response: %s", ex
            )
            raise LogSendException(
                "ElasticsearchLogsProducer Elasticsearch error from an HTTP response: %s" % ex
            )
        except Exception as e:
            logger.exception(
                "ElasticsearchLogsProducer exception sending log to Elasticsearch: %s", e
            )
            raise LogSendException(
                "ElasticsearchLogsProducer exception sending log to Elasticsearch: %s" % e
            )
