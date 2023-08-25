import os
import ssl
import tempfile
from ssl import SSLError
from tempfile import NamedTemporaryFile
from test.fixtures import *
from unittest.mock import MagicMock, call

import pytest
from dateutil.parser import parse
from mock import Mock, patch

from data.logs_model import configure

from ..logs_producer.splunk_logs_producer import SplunkLogsProducer
from .test_elasticsearch import logs_model, mock_db_model

FAKE_SPLUNK_HOST = "fakesplunk"
FAKE_SPLUNK_PORT = 443
FAKE_SPLUNK_TOKEN = None
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
def test_splunk_logs_producers(
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
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect"):
        with patch("ssl.SSLContext.load_verify_locations"):
            configure(splunk_logs_model_config)
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
                mock_send.assert_not_called()
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
                expected_call_args = [
                    call(
                        '{"account": "devtable", "datetime": "2019-01-01 03:30:00", "ip": "192.168.1.1", '
                        '"kind": "push_repo", "metadata_json": {"key": "value"}, "performer": "fake_username", '
                        '"repository": null}'
                    )
                ]
                mock_send.assert_has_calls(expected_call_args)


def test_submit_called_with_multiple_none_args(
    logs_model,
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect"):
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
            expected_call_args = [
                call(
                    '{"account": null, "datetime": "2019-01-01 03:30:00", "ip": "192.168.1.1", "kind": null, '
                    '"metadata_json": {}, "performer": null, "repository": null}'
                )
            ]
            mock_send.assert_has_calls(expected_call_args)


def test_submit_skip_ssl_verify_false(
    logs_model,
    splunk_logs_model_config,
    mock_db_model,
    initialized_db,
    cert_file_path,
):
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect"):
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
            expected_call_args = [
                call(
                    '{"account": "devtable", "datetime": "2019-01-01 03:30:00", "ip": "192.168.1.1", "kind": null, '
                    '"metadata_json": {}, "performer": null, "repository": "simple"}'
                )
            ]
            mock_send.assert_has_calls(expected_call_args)


def test_connect_with_invalid_certfile_path(
    logs_model, splunk_logs_model_config, mock_db_model, initialized_db
):
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect"):
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
    with patch(
        "data.logs_model.logs_producer.splunk_logs_producer.SplunkLogsProducer.send"
    ) as mock_send, patch("splunklib.client.connect"):
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
