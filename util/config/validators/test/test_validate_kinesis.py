import pytest
import boto3

from datetime import datetime
from mock import patch

from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_kinesis import KinesisValidator

from test.fixtures import *


_TEST_RESPONSE = {
    "StreamDescription": {
        "StreamName": "somestream",
        "StreamARN": "arn:aws:kinesis:us-east-1:123456:stream/somestream",
        "StreamStatus": "ACTIVE",
        "Shards": [
            {
                "ShardId": "shardId-000000000000",
                "HashKeyRange": {"StartingHashKey": "0", "EndingHashKey": "12345"},
                "SequenceNumberRange": {"StartingSequenceNumber": "6789"},
            }
        ],
        "HasMoreShards": False,
        "RetentionPeriodHours": 24,
        "StreamCreationTimestamp": datetime(2019, 4, 20, 0, 0, 0),
        "KeyId": "arn:aws:kms:us-east-1:123456:key/4e83c2dd-0527-4d9d-8867-c68f70b810ec",
    },
    "ResponseMetadata": {
        "RequestId": "2c2d861b-f50e-47e9-b35c-0b5a5cbe965b",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
            "x-amzn-requestid": "9e014edc-a3c1-44ba-94b9-747990c054f3",
            "x-amz-id-2": "someamazonis",
            "date": "Wed, 4 Mar 2020 16:34:22 GMT",
            "content-type": "application/x-amz-json-1.1",
            "content-length": "659",
        },
        "RetryAttempts": 0,
    },
}


@pytest.mark.parametrize(
    "unvalidated_config,expected",
    [
        ({}, ConfigValidationException),
        (
            {
                "LOGS_MODEL": "not-elasticsearch",
                "LOGS_MODEL_CONFIG": {
                    "elasticsearch_config": {},
                },
            },
            ConfigValidationException,
        ),
        (
            {
                "LOGS_MODEL": "elasticsearch",
                "LOGS_MODEL_CONFIG": {
                    "producer": "not_kinesis_stream",
                    "kinesis_stream_config": {},
                },
            },
            ConfigValidationException,
        ),
        (
            {
                "LOGS_MODEL": "elasticsearch",
                "LOGS_MODEL_CONFIG": {
                    "producer": "kinesis_stream",
                    "kinesis_stream_config": {
                        "aws_access_key": "some key",
                        "aws_secret_key": "some secret",
                        "aws_region": "some-region-1",
                    },
                },
            },
            None,
        ),
    ],
)
def test_validate_elasticsearch(unvalidated_config, expected):
    validator = KinesisValidator()
    unvalidated_config = ValidatorContext(unvalidated_config)

    with patch("botocore.client") as bc:
        bc.Kinesis.describe_stream.return_value = _TEST_RESPONSE

        if expected is not None:
            with pytest.raises(expected):
                validator.validate(unvalidated_config)
        else:
            validator.validate(unvalidated_config)
