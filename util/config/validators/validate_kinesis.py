import boto3

from data.logs_model.elastic_logs import INDEX_NAME_PREFIX
from util.config.validators import BaseValidator, ConfigValidationException


class KinesisValidator(BaseValidator):
    name = "kinesis"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        logs_model = config.get("LOGS_MODEL", "database")
        if logs_model != "elasticsearch":
            raise ConfigValidationException("LOGS_MODEL not set to Elasticsearch")

        logs_model_config = config.get("LOGS_MODEL_CONFIG", {})
        producer = logs_model_config.get("producer", {})
        if not producer or producer != "kinesis_stream":
            raise ConfigValidationException("Producer not set to 'kinesis_stream'")

        kinesis_stream_config = logs_model_config.get("kinesis_stream_config", {})
        if not kinesis_stream_config:
            raise ConfigValidationException("No kinesis_stream_config defined'")

        stream_name = kinesis_stream_config.get("stream_name")
        aws_access_key = kinesis_stream_config.get("aws_access_key")
        aws_secret_key = kinesis_stream_config.get("aws_secret_key")
        aws_region = kinesis_stream_config.get("aws_region")

        producer = boto3.client(
            "kinesis",
            use_ssl=True,
            region_name=aws_region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )

        try:
            producer.describe_stream(StreamName=stream_name)
        except (
            producer.exceptions.ClientError,
            producer.exceptions.ResourceNotFoundException,
        ) as e:
            raise ConfigValidationException("Unable to connect to Kinesis with config: %s", e)
        except Exception:
            raise ConfigValidationException("Unable to connect to Kinesis")
