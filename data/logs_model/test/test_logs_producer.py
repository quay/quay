import logging

import botocore
import pytest
from botocore.exceptions import ClientError
from dateutil.parser import parse
from mock import Mock, patch

from .mock_elasticsearch import *
from .test_elasticsearch import (
    app_config,
    logs_model,
    logs_model_config,
    mock_db_model,
    mock_elasticsearch,
)
from data.logs_model import configure
from data.logs_model.logs_producer.kinesis_stream_logs_producer import (
    KINESIS_HASH_SPACE,
    _explicit_hash_key,
)

logger = logging.getLogger(__name__)

FAKE_KAFKA_BROKERS = ["fake_server1", "fake_server2"]
FAKE_KAFKA_TOPIC = "sometopic"
FAKE_MAX_BLOCK_SECONDS = 1


@pytest.fixture()
def kafka_logs_producer_config(app_config):
    producer_config = {}
    producer_config.update(app_config)

    kafka_config = {
        "bootstrap_servers": FAKE_KAFKA_BROKERS,
        "topic": FAKE_KAFKA_TOPIC,
        "max_block_seconds": FAKE_MAX_BLOCK_SECONDS,
    }

    producer_config["LOGS_MODEL_CONFIG"]["producer"] = "kafka"
    producer_config["LOGS_MODEL_CONFIG"]["kafka_config"] = kafka_config
    return producer_config


@pytest.fixture()
def kinesis_logs_producer_config(app_config):
    producer_config = {}
    producer_config.update(app_config)

    kinesis_stream_config = {
        "stream_name": "test-stream",
        "aws_region": "fake-region-1",
        "aws_access_key": "some_key",
        "aws_secret_key": "some_secret",
    }

    producer_config["LOGS_MODEL_CONFIG"]["producer"] = "kinesis_stream"
    producer_config["LOGS_MODEL_CONFIG"]["kinesis_stream_config"] = kinesis_stream_config
    return producer_config


def test_kafka_logs_producers(
    logs_model, mock_elasticsearch, mock_db_model, kafka_logs_producer_config
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)

    producer_config = kafka_logs_producer_config
    with (
        patch("kafka.client_async.KafkaClient.check_version"),
        patch("kafka.KafkaProducer.send") as mock_send,
        patch("kafka.KafkaProducer.max_usable_produce_magic"),
    ):
        configure(producer_config)
        logs_model.log_action(
            "pull_repo",
            "user1",
            Mock(id=1),
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
        )

        mock_send.assert_called_once()


def test_kinesis_logs_producers(
    logs_model, mock_elasticsearch, mock_db_model, kinesis_logs_producer_config
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)

    producer_config = kinesis_logs_producer_config
    describe_response = {
        "StreamDescriptionSummary": {"OpenShardCount": 4},
    }

    def mock_api_call(operation_name, kwargs):
        if operation_name == "DescribeStreamSummary":
            return describe_response
        return {}

    with (
        patch("botocore.endpoint.EndpointCreator.create_endpoint"),
        patch("botocore.client.BaseClient._make_api_call", side_effect=mock_api_call) as mock_send,
    ):
        configure(producer_config)
        logs_model.log_action(
            "pull_repo",
            "user1",
            Mock(id=1),
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
        )

        # Should have 2 calls: DescribeStreamSummary (init) + PutRecord (send)
        assert mock_send.call_count == 2
        assert mock_send.call_args_list[0][0][0] == "DescribeStreamSummary"
        assert mock_send.call_args_list[1][0][0] == "PutRecord"
        put_kwargs = mock_send.call_args_list[1][0][1]
        assert "ExplicitHashKey" in put_kwargs
        assert "PartitionKey" in put_kwargs


def test_kinesis_logs_producer_with_explicit_hash_key(
    logs_model, mock_elasticsearch, mock_db_model, kinesis_logs_producer_config
):
    """Test that ExplicitHashKey is used when shard count is auto-detected."""
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)

    producer_config = kinesis_logs_producer_config
    describe_response = {
        "StreamDescriptionSummary": {"OpenShardCount": 4},
    }

    def mock_api_call(operation_name, kwargs):
        if operation_name == "DescribeStreamSummary":
            return describe_response
        return {}

    with (
        patch("botocore.endpoint.EndpointCreator.create_endpoint"),
        patch("botocore.client.BaseClient._make_api_call", side_effect=mock_api_call) as mock_send,
    ):
        configure(producer_config)
        logs_model.log_action(
            "pull_repo",
            "user1",
            Mock(id=1),
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
        )

        # Should have 2 calls: DescribeStreamSummary (init) + PutRecord (send)
        assert mock_send.call_count == 2
        assert mock_send.call_args_list[0][0][0] == "DescribeStreamSummary"
        assert mock_send.call_args_list[1][0][0] == "PutRecord"
        put_kwargs = mock_send.call_args_list[1][0][1]
        assert "ExplicitHashKey" in put_kwargs


def test_explicit_hash_key_within_hash_space():
    """Test that _explicit_hash_key returns values within the Kinesis hash space."""
    for _ in range(100):
        key = int(_explicit_hash_key(128))
        assert 0 <= key < KINESIS_HASH_SPACE


def test_explicit_hash_key_distributes_across_shards():
    """Test that _explicit_hash_key distributes evenly across all shards."""
    number_of_shards = 4
    slice_size = KINESIS_HASH_SPACE // number_of_shards
    shard_hits = {i: 0 for i in range(number_of_shards)}

    for _ in range(1000):
        key = int(_explicit_hash_key(number_of_shards))
        shard = key // slice_size
        shard_hits[shard] += 1

    # Each shard should get roughly 250 hits out of 1000
    for shard, count in shard_hits.items():
        assert count > 100, f"Shard {shard} only got {count} hits, expected ~250"


def test_explicit_hash_key_single_shard():
    """Test that _explicit_hash_key with 1 shard always targets shard 0's range."""
    for _ in range(100):
        key = int(_explicit_hash_key(1))
        assert 0 <= key < KINESIS_HASH_SPACE


def test_kinesis_fallback_when_shard_count_unavailable(
    logs_model, mock_elasticsearch, mock_db_model, kinesis_logs_producer_config
):
    """Test that when describe_stream_summary fails, ExplicitHashKey is not set
    and the old _partition_key() logic is used as PartitionKey."""
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)

    producer_config = kinesis_logs_producer_config

    def mock_api_call(operation_name, kwargs):
        if operation_name == "DescribeStreamSummary":
            raise ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
                "DescribeStreamSummary",
            )
        return {}

    with (
        patch("botocore.endpoint.EndpointCreator.create_endpoint"),
        patch("botocore.client.BaseClient._make_api_call", side_effect=mock_api_call) as mock_send,
    ):
        configure(producer_config)
        logs_model.log_action(
            "pull_repo",
            "user1",
            Mock(id=1),
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
        )

        # Should have 2 calls: DescribeStreamSummary (failed) + PutRecord (send)
        assert mock_send.call_count == 2
        assert mock_send.call_args_list[0][0][0] == "DescribeStreamSummary"
        assert mock_send.call_args_list[1][0][0] == "PutRecord"
        put_kwargs = mock_send.call_args_list[1][0][1]
        assert "ExplicitHashKey" not in put_kwargs
        assert "PartitionKey" in put_kwargs
        # PartitionKey should be a 40-char SHA1 hex digest from _partition_key()
        assert len(put_kwargs["PartitionKey"]) == 40
