import logging

from elasticsearch.exceptions import ElasticsearchException

from data.logs_model.logs_producer.interface import LogProducerInterface
from data.logs_model.logs_producer import LogSendException


logger = logging.getLogger(__name__)


class ElasticsearchLogsProducer(LogProducerInterface):
    """
    Log producer writing log entries to Elasticsearch.

    This implementation writes directly to Elasticsearch without a streaming/queueing service.
    """

    def send(self, logentry):
        try:
            logentry.save()
        except ElasticsearchException as ex:
            logger.exception("ElasticsearchLogsProducer error sending log to Elasticsearch: %s", ex)
            raise LogSendException(
                "ElasticsearchLogsProducer error sending log to Elasticsearch: %s" % ex
            )
        except Exception as e:
            logger.exception(
                "ElasticsearchLogsProducer exception sending log to Elasticsearch: %s", e
            )
            raise LogSendException(
                "ElasticsearchLogsProducer exception sending log to Elasticsearch: %s" % e
            )
