import logging

from kafka.errors import KafkaError, KafkaTimeoutError
from kafka import KafkaProducer

from data.logs_model.shared import epoch_ms
from data.logs_model.logs_producer.interface import LogProducerInterface
from data.logs_model.logs_producer.util import logs_json_serializer
from data.logs_model.logs_producer import LogSendException


logger = logging.getLogger(__name__)

DEFAULT_MAX_BLOCK_SECONDS = 5


class KafkaLogsProducer(LogProducerInterface):
    """
    Log producer writing log entries to a Kafka stream.
    """

    def __init__(self, bootstrap_servers=None, topic=None, client_id=None, max_block_seconds=None):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self.max_block_ms = (max_block_seconds or DEFAULT_MAX_BLOCK_SECONDS) * 1000

        self._producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            max_block_ms=self.max_block_ms,
            value_serializer=logs_json_serializer,
        )

    def send(self, logentry):
        try:
            # send() has a (max_block_ms) timeout and get() has a (max_block_ms) timeout
            # for an upper bound of 2x(max_block_ms) before guaranteed delivery
            future = self._producer.send(
                self.topic, logentry.to_dict(), timestamp_ms=epoch_ms(logentry.datetime)
            )
            record_metadata = future.get(timeout=self.max_block_ms)
            assert future.succeeded
        except KafkaTimeoutError as kte:
            logger.exception("KafkaLogsProducer timeout sending log to Kafka: %s", kte)
            raise LogSendException("KafkaLogsProducer timeout sending log to Kafka: %s" % kte)
        except KafkaError as ke:
            logger.exception("KafkaLogsProducer error sending log to Kafka: %s", ke)
            raise LogSendException("KafkaLogsProducer error sending log to Kafka: %s" % ke)
        except Exception as e:
            logger.exception("KafkaLogsProducer exception sending log to Kafka: %s", e)
            raise LogSendException("KafkaLogsProducer exception sending log to Kafka: %s" % e)
