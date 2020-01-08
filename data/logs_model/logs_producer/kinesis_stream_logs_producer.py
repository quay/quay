import logging
import hashlib
import random

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config

from data.logs_model.logs_producer.interface import LogProducerInterface
from data.logs_model.logs_producer.util import logs_json_serializer
from data.logs_model.logs_producer import LogSendException


logger = logging.getLogger(__name__)

KINESIS_PARTITION_KEY_PREFIX = "logentry_partition_key_"
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 5
MAX_RETRY_ATTEMPTS = 5
DEFAULT_MAX_POOL_CONNECTIONS = 10


def _partition_key(number_of_shards=None):
    """
    Generate a partition key for AWS Kinesis stream.

    If the number of shards is specified, generate keys where the size of the key space is the
    number of shards.
    """
    key = None
    if number_of_shards is not None:
        shard_number = random.randrange(0, number_of_shards)
        key = hashlib.sha1(
            (KINESIS_PARTITION_KEY_PREFIX + str(shard_number)).encode("utf-8")
        ).hexdigest()
    else:
        key = hashlib.sha1(
            (KINESIS_PARTITION_KEY_PREFIX + str(random.getrandbits(256))).encode("utf-8")
        ).hexdigest()

    return key


class KinesisStreamLogsProducer(LogProducerInterface):
    """
    Log producer writing log entries to an Amazon Kinesis Data Stream.
    """

    def __init__(
        self,
        stream_name,
        aws_region,
        aws_access_key=None,
        aws_secret_key=None,
        connect_timeout=None,
        read_timeout=None,
        max_retries=None,
        max_pool_connections=None,
    ):
        self._stream_name = stream_name
        self._aws_region = aws_region
        self._aws_access_key = aws_access_key
        self._aws_secret_key = aws_secret_key
        self._connect_timeout = connect_timeout or DEFAULT_CONNECT_TIMEOUT
        self._read_timeout = read_timeout or DEFAULT_READ_TIMEOUT
        self._max_retries = max_retries or MAX_RETRY_ATTEMPTS
        self._max_pool_connections = max_pool_connections or DEFAULT_MAX_POOL_CONNECTIONS

        client_config = Config(
            connect_timeout=self._connect_timeout,
            read_timeout=self._read_timeout,
            retries={"max_attempts": self._max_retries},
            max_pool_connections=self._max_pool_connections,
        )
        self._producer = boto3.client(
            "kinesis",
            use_ssl=True,
            region_name=self._aws_region,
            aws_access_key_id=self._aws_access_key,
            aws_secret_access_key=self._aws_secret_key,
            config=client_config,
        )

    def send(self, logentry):
        try:
            data = logs_json_serializer(logentry)
            self._producer.put_record(
                StreamName=self._stream_name, Data=data, PartitionKey=_partition_key()
            )
        except ClientError as ce:
            logger.exception(
                "KinesisStreamLogsProducer client error sending log to Kinesis: %s", ce
            )
            raise LogSendException(
                "KinesisStreamLogsProducer client error sending log to Kinesis: %s" % ce
            )
        except Exception as e:
            logger.exception("KinesisStreamLogsProducer exception sending log to Kinesis: %s", e)
            raise LogSendException(
                "KinesisStreamLogsProducer exception sending log to Kinesis: %s" % e
            )
