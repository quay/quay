import requests
from elasticsearch_dsl.connections import connections

from data.logs_model.elastic_logs import INDEX_NAME_PREFIX
from util.config.validators import BaseValidator, ConfigValidationException


class ElasticsearchValidator(BaseValidator):
    name = "elasticsearch"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        logs_model = config.get("LOGS_MODEL", "database")
        if logs_model != "elasticsearch":
            raise ConfigValidationException("LOGS_MODEL not set to Elasticsearch")

        logs_model_config = config.get("LOGS_MODEL_CONFIG", {})
        elasticsearch_config = logs_model_config.get("elasticsearch_config", {})
        if not elasticsearch_config:
            raise ConfigValidationException("Missing Elasticsearch config")

        if not "host" in elasticsearch_config:
            raise ConfigValidationException("Missing Elasticsearch hostname")

        host = elasticsearch_config["host"]
        port = str(elasticsearch_config["port"])
        index_prefix = elasticsearch_config.get("index_prefix") or INDEX_NAME_PREFIX
        auth = (elasticsearch_config.get("access_key"), elasticsearch_config.get("secret_key"))

        resp = requests.get("https://" + host + ":" + port + "/" + index_prefix + "*", auth=auth)
        if resp.status_code != 200:
            raise ConfigValidationException(
                "Unable to connect to Elasticsearch with config: %s", resp.status_code
            )
