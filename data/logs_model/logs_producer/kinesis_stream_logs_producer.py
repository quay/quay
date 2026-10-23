import hashlib
import logging
import random

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from data.logs_model.logs_producer import LogSendException
from data.logs_model.logs_producer.interface import LogProducerInterface
from data.logs_model.logs_producer.util import logs_json_serializer

logger = logging.getLogger(__name__)

KINESIS_PARTITION_KEY_PREFIX = "logentry_partition_key_"
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_READ_TIMEOUT = 5
MAX_RETRY_ATTEMPTS = 5
DEFAULT_MAX_POOL_CONNECTIONS = 10

# Kinesis hash space: 0 to 2^128 - 1
KINESIS_HASH_SPACE = 2**128


def _partition_key():
    """
    Generate a random partition key for AWS Kinesis stream.
    """
    return hashlib.sha1(
        (KINESIS_PARTITION_KEY_PREFIX + str(random.getrandbits(256))).encode("utf-8")
    ).hexdigest()


def _explicit_hash_key(number_of_shards):
    """
    Generate an ExplicitHashKey that targets a random shard evenly.

    Divides the Kinesis hash space (0 to 2^128 - 1) into equal slices,
    one per shard, and returns a random point within a randomly chosen slice.
    This bypasses Kinesis's internal MD5 hashing and guarantees even distribution.
    """
    shard_number = random.randrange(0, number_of_shards)
    slice_size = KINESIS_HASH_SPACE // number_of_shards
    shard_start = slice_size * shard_number
    return str(shard_start + random.randrange(0, slice_size))


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
        self._number_of_shards = self._get_open_shard_count()

    def _get_open_shard_count(self):
        """
        Query Kinesis for the current number of open shards in the stream.
        """
        try:
            response = self._producer.describe_stream_summary(StreamName=self._stream_name)
            count = response["StreamDescriptionSummary"]["OpenShardCount"]
            logger.info("Kinesis stream %s has %d open shards", self._stream_name, count)
            return count
        except ClientError as ce:
            logger.exception(
                "Failed to get shard count for stream %s, falling back to random partition keys: %s",
                self._stream_name,
                ce,
            )
            return None

    def send(self, logentry):
        try:
            data = logs_json_serializer(logentry)
            put_kwargs = {
                "StreamName": self._stream_name,
                "Data": data,
                "PartitionKey": _partition_key(),
            }
            if self._number_of_shards is not None:
                put_kwargs["ExplicitHashKey"] = _explicit_hash_key(self._number_of_shards)
            self._producer.put_record(**put_kwargs)
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
