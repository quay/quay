import json
import os
import ssl
import tempfile
from datetime import datetime
from math import exp
from ssl import SSLError
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, call

import pytest
from dateutil.parser import parse
from mock import Mock, patch

from ..logs_producer.splunk_logs_producer import SplunkLogsProducer
from .test_elasticsearch import logs_model, mock_db_model
from data.logs_model import configure
from data.logs_model.logs_producer import LogSendException
from data.model import config as _config
from test.fixtures import *

FAKE_SPLUNK_HOST = "fakesplunk"
FAKE_SPLUNK_PORT = 443
FAKE_SPLUNK_TOKEN = None
FAKE_SPLUNK_HEC_TOKEN = "fake_hec"
FAKE_INDEX_PREFIX = "test_index_prefix"
FAKE_NAMESPACES = {
    "user1": Mock(
        id=1,
        organization="user1.organization",
        username="user1.username",
        email="user1.email",
        robot="user1.robot",
    )
}
FAKE_REPOSITORIES = {
    "user1/repo1": Mock(id=1, namespace_user=FAKE_NAMESPACES["user1"]),
}

FAKE_PERFORMER = {
    "user1": Mock(
        username="fake_username",
        email="fake_email@123",
        id=1,
    )
}

FAKE_REPO = {
    "name": "fake_repo",
}


@pytest.fixture(scope="function")
def app_config():
    with patch.dict(_config.app_config, {}, clear=True):
        yield _config.app_config


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
                "ssl_ca_path": "fake/cert/path.pem",
            },
        },
    }
    return conf


@pytest.fixture()
def splunk_hec_logs_model_config():
    conf = {
        "LOGS_MODEL": "splunk",
        "LOGS_MODEL_CONFIG": {
            "producer": "splunk_hec",
            "splunk_hec_config": {
                "host": FAKE_SPLUNK_HOST,
                "port": FAKE_SPLUNK_PORT,
                "hec_token": FAKE_SPLUNK_HEC_TOKEN,
                "url_scheme": "https",
                "verify_ssl": True,
                "ssl_ca_path": "fake/cert/path.pem",
                "index": FAKE_INDEX_PREFIX,
                "splunk_host": "fake_splunk_host",
                "splunk_sourcetype": "fake_sourcetype",
            },
        },
    }
    return conf


@pytest.fixture(scope="session")
def cert_file_path():
    # Create a temporary file with a valid certificate
    with tempfile.NamedTemporaryFile(delete=False) as certfile:
        certfile.write(b"valid certificate")
        cert_path = certfile.name

    yield cert_path

    # Clean up the temporary file
    os.unlink(cert_path)


@pytest.mark.parametrize(
    """
    unlogged_ok, unlogged_pulls_ok, kind_name, namespace_name, performer, ip,
    metadata, repository, repository_name, timestamp, throws, send_exception
    """,
    [
        # logs a push_repo action
        pytest.param(
            False,
            False,
            "push_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            False,
            None,
        ),
        # doesn't raise a failed push_repo action
        pytest.param(
            True,
            False,
            "push_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            False,
            LogSendException("Failed to send log data"),
        ),
        # doesn't raise a failed pull_repo action
        pytest.param(
            False,
            True,
            "pull_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            False,
            LogSendException("Failed to send log data"),
        ),
        # raise a failed pull_repo action
        pytest.param(
            False,
            False,
            "pull_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            True,
            LogSendException("Failed to send log data"),
        ),
        # raises ValueError when repository_name is not None and repository is not None
        pytest.param(
            False,
            False,
            "pull_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            FAKE_REPOSITORIES["user1/repo1"],
            "repo1",
            parse("2019-01-01T03:30"),
            True,
            None,
        ),
        # raises exception when no namespace is given
        pytest.param(
            False,
            False,
            "pull_repo",
            None,
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            FAKE_REPOSITORIES["user1/repo1"],
            "user1/repo1",
            parse("2019-01-01T03:30"),
            True,
            None,
        ),
    ],
)
def test_splunk_logs_producers(
    unlogged_ok,
    unlogged_pulls_ok,
    kind_name,
    namespace_name,
    performer,
    ip,
    metadata,
    repository,
    repository_name,
    timestamp,
    throws,
    send_exception,
    logs_model,
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
    app_config,
):
    app_config["ALLOW_PULLS_WITHOUT_STRICT_LOGGING"] = unlogged_pulls_ok
    app_config["ALLOW_WITHOUT_STRICT_LOGGING"] = unlogged_ok

    with (
        patch(
            "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
        ) as mock_send,
        patch("splunklib.client.connect"),
    ):
        with patch("ssl.SSLContext.load_verify_locations"):
            configure(splunk_logs_model_config)

            if send_exception:
                mock_send.side_effect = send_exception

            if throws:
                if not send_exception:
                    with pytest.raises(
                        ValueError,
                        match=r"Incorrect argument provided when logging action logs, "
                        r"namespace name should not be empty",
                    ):
                        logs_model.log_action(
                            kind_name,
                            namespace_name,
                            performer,
                            ip,
                            metadata,
                            repository,
                            repository_name,
                            timestamp,
                        )
                    mock_send.assert_not_called()
                else:
                    with pytest.raises(LogSendException):
                        logs_model.log_action(
                            kind_name,
                            namespace_name,
                            performer,
                            ip,
                            metadata,
                            repository,
                            repository_name,
                            timestamp,
                        )
            else:
                logs_model.log_action(
                    kind_name,
                    namespace_name,
                    performer,
                    ip,
                    metadata,
                    repository,
                    repository_name,
                    timestamp,
                )

                expected_event = {
                    "account": "devtable",
                    "datetime": datetime(2019, 1, 1, 3, 30),
                    "ip": "192.168.1.1",
                    "kind": kind_name,
                    "metadata_json": {"key": "value"},
                    "performer": "fake_username",
                    "repository": None,
                }

                expected_call_args = [call(expected_event)]
                mock_send.assert_has_calls(expected_call_args)


@pytest.mark.parametrize(
    """
    kind_name, namespace_name,
    performer, ip, metadata, repository, repository_name, timestamp, throws
    """,
    [
        pytest.param(
            "push_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            False,
        ),
        # raises ValueError when repository_name is not None and repository is not None
        pytest.param(
            "pull_repo",
            "devtable",
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            FAKE_REPOSITORIES["user1/repo1"],
            "repo1",
            parse("2019-01-01T03:30"),
            True,
        ),
        # raises exception when no namespace is given
        pytest.param(
            "pull_repo",
            None,
            FAKE_PERFORMER["user1"],
            "192.168.1.1",
            {"key": "value"},
            FAKE_REPOSITORIES["user1/repo1"],
            "user1/repo1",
            parse("2019-01-01T03:30"),
            True,
        ),
    ],
)
def test_splunk_hec_logs_producer(
    kind_name,
    namespace_name,
    performer,
    ip,
    metadata,
    repository,
    repository_name,
    timestamp,
    throws,
    logs_model,
    splunk_hec_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None

    with patch("requests.post", return_value=mock_response) as mock_post:
        with patch("ssl.SSLContext.load_verify_locations"):

            configure(splunk_hec_logs_model_config)

            assert (
                logs_model._logs_producer.ssl_verify_context
                == splunk_hec_logs_model_config["LOGS_MODEL_CONFIG"]["splunk_hec_config"][
                    "ssl_ca_path"
                ]
            )

            if throws:
                with pytest.raises(
                    ValueError,
                    match=r"Incorrect argument provided when logging action logs, "
                    r"namespace name should not be empty",
                ):
                    logs_model.log_action(
                        kind_name,
                        namespace_name,
                        performer,
                        ip,
                        metadata,
                        repository,
                        repository_name,
                        timestamp,
                    )
                mock_post.assert_not_called()
            else:
                logs_model.log_action(
                    kind_name,
                    namespace_name,
                    performer,
                    ip,
                    metadata,
                    repository,
                    repository_name,
                    timestamp,
                )

                expected_event = {
                    "account": "devtable",
                    "datetime": datetime(2019, 1, 1, 3, 30),
                    "ip": "192.168.1.1",
                    "kind": "push_repo",
                    "metadata_json": {"key": "value"},
                    "performer": "fake_username",
                    "repository": None,
                }

                expected_call = {
                    "event": expected_event,
                    "sourcetype": splunk_hec_logs_model_config["LOGS_MODEL_CONFIG"][
                        "splunk_hec_config"
                    ]["splunk_sourcetype"],
                    "host": splunk_hec_logs_model_config["LOGS_MODEL_CONFIG"]["splunk_hec_config"][
                        "splunk_host"
                    ],
                    "index": splunk_hec_logs_model_config["LOGS_MODEL_CONFIG"]["splunk_hec_config"][
                        "index"
                    ],
                }

                expected_post_args = [
                    call(
                        logs_model._logs_producer.hec_url,
                        headers=logs_model._logs_producer.headers,
                        data=json.dumps(
                            expected_call, sort_keys=True, default=str, ensure_ascii=False
                        ).encode("utf-8"),
                        verify=splunk_hec_logs_model_config["LOGS_MODEL_CONFIG"][
                            "splunk_hec_config"
                        ]["ssl_ca_path"],
                    )
                ]
                mock_post.assert_has_calls(expected_post_args)


def test_submit_called_with_multiple_none_args(
    logs_model,
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    with (
        patch(
            "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
        ) as mock_send,
        patch("splunklib.client.connect"),
    ):
        with patch("ssl.SSLContext.load_verify_locations"):
            configure(splunk_logs_model_config)
            logs_model.log_action(
                None,
                None,
                None,
                "192.168.1.1",
                {},
                None,
                None,
                parse("2019-01-01T03:30"),
            )

            expected_event = {
                "account": None,
                "datetime": datetime(2019, 1, 1, 3, 30),
                "ip": "192.168.1.1",
                "kind": None,
                "metadata_json": {},
                "performer": None,
                "repository": None,
            }

            expected_call_args = [call(expected_event)]
            mock_send.assert_has_calls(expected_call_args)


def test_submit_skip_ssl_verify_false(
    logs_model,
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    with (
        patch(
            "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
        ) as mock_send,
        patch("splunklib.client.connect"),
    ):
        with patch("ssl.SSLContext.load_verify_locations"):
            conf = splunk_logs_model_config
            conf["LOGS_MODEL_CONFIG"]["splunk_config"]["verify_ssl"] = False
            configure(conf)
            logs_model.log_action(
                None,
                "devtable",
                None,
                "192.168.1.1",
                {},
                None,
                "simple",
                parse("2019-01-01T03:30"),
            )

            expected_event = {
                "account": "devtable",
                "datetime": datetime(2019, 1, 1, 3, 30),
                "ip": "192.168.1.1",
                "kind": None,
                "metadata_json": {},
                "performer": None,
                "repository": "simple",
            }

            expected_call_args = [call(expected_event)]
            mock_send.assert_has_calls(expected_call_args)


def test_connect_with_invalid_certfile_path(
    logs_model, splunk_logs_model_config, mock_db_model, initialized_db
):
    with (
        patch(
            "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
        ) as mock_send,
        patch("splunklib.client.connect"),
    ):
        with pytest.raises(
            Exception,
            match=r"Path to cert file is not valid \[Errno \d\] No such file or directory",
        ):
            configure(splunk_logs_model_config)
            logs_model.log_action(
                None,
                "devtable",
                Mock(id=1),
                "192.168.1.1",
                {"key": "value"},
                FAKE_REPOSITORIES["user1/repo1"],
                None,
                parse("2019-01-01T03:30"),
                False,
            )
            mock_send.assert_not_called()


def test_connect_with_invalid_ssl_cert(
    logs_model, splunk_logs_model_config, mock_db_model, initialized_db
):
    with (
        patch(
            "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
        ) as mock_send,
        patch("splunklib.client.connect"),
    ):
        with patch.object(
            ssl.SSLContext,
            "load_verify_locations",
            side_effect=Exception("SSL cert is not valid ('SSL certificate error',)"),
        ):
            with pytest.raises(
                Exception, match=r"SSL cert is not valid \(\'SSL certificate error\'\,\)"
            ):
                configure(splunk_logs_model_config)
                logs_model.log_action(
                    None,
                    "devtable",
                    Mock(id=1),
                    "192.168.1.1",
                    {"key": "value"},
                    FAKE_REPOSITORIES["user1/repo1"],
                    None,
                    parse("2019-01-01T03:30"),
                    False,
                )
                mock_send.assert_not_called()
