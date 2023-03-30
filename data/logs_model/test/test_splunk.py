from unittest.mock import MagicMock

import pytest
from dateutil.parser import parse
from mock import patch, Mock

from .test_elasticsearch import logs_model, mock_db_model
from data.logs_model import configure
from test.fixtures import *
from data.model.repository import create_repository

FAKE_SPLUNK_HOST = "fakesplunk"
FAKE_SPLUNK_PORT = 443
FAKE_SPLUNK_TOKEN = None
FAKE_INDEX_PREFIX = "test_index_prefix"


@pytest.fixture()
def splunk_logs_model_config():
    conf = {
        "LOGS_MODEL": "splunk",
        "LOGS_MODEL_CONFIG": {
            "producer": "splunk",
            "splunk_config": {
                "host": FAKE_SPLUNK_HOST,
                "port": FAKE_SPLUNK_PORT,
                "bearer_token": FAKE_SPLUNK_TOKEN,
                "url_scheme": "https",
                "verify_ssl": True,
                "index_prefix": FAKE_INDEX_PREFIX,
            },
        },
    }
    return conf


def test_splunk_logs_producers(logs_model, splunk_logs_model_config, mock_db_model, initialized_db):

    producer_config = splunk_logs_model_config
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect", MagicMock()):
        repo = create_repository("devtable", "somenewrepo", None, repo_kind="image")
        configure(producer_config)
        logs_model.log_action(
            "pull_repo",
            "devtable",
            Mock(id=1),
            "192.168.1.1",
            {"key": "value"},
            repo,
            None,
            parse("2019-01-01T03:30"),
        )

        mock_send.assert_called_once()
