import logging
import pytest
from dateutil.parser import parse
from mock import patch, Mock

import botocore

from data.logs_model import configure

from .test_elasticsearch import (
    app_config,
    logs_model_config,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
)
from .mock_elasticsearch import *


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
        "aws_region": "fake_region",
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
    with patch("kafka.client_async.KafkaClient.check_version"), patch(
        "kafka.KafkaProducer.send"
    ) as mock_send, patch("kafka.KafkaProducer._max_usable_produce_magic"):
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
    with patch("botocore.endpoint.EndpointCreator.create_endpoint"), patch(
        "botocore.client.BaseClient._make_api_call"
    ) as mock_send:
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

        # Check that a PutRecord api call is made.
        # NOTE: The second arg of _make_api_call uses a randomized PartitionKey
        mock_send.assert_called_once_with("PutRecord", mock_send.call_args_list[0][0][1])
