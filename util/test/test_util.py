import os
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest
from botocore.client import BaseClient

from util import slash_join
from util.aws_sts import _create_sts_client, create_aws_client


@pytest.mark.parametrize(
    "pieces, expected",
    [
        (
            ["https://github.com", "/coreos-inc/" "quay/pull/1092/files"],
            "https://github.com/coreos-inc/quay/pull/1092/files",
        ),
        (
            ["https://", "github.com/", "/coreos-inc", "/quay/pull/1092/files/"],
            "https://github.com/coreos-inc/quay/pull/1092/files",
        ),
        (["https://somegithub.com/", "/api/v3/"], "https://somegithub.com/api/v3"),
        (["https://github.somedomain.com/", "/api/v3/"], "https://github.somedomain.com/api/v3"),
    ],
)
def test_slash_join(pieces, expected):
    joined_url = slash_join(*pieces)
    assert joined_url == expected


class TestCreateAwsClient:
    """Test cases for create_aws_client function."""

    @patch("util.aws_sts.boto3.client")
    def test_create_aws_client_with_iam_key(self, mock_boto3_client):
        mock_client = MagicMock(spec=BaseClient)
        mock_boto3_client.return_value = mock_client

        result = create_aws_client(
            service_name="s3",
            region="us-east-1",
            access_key="test_access_key",
            secret_key="test_secret_key",
        )

        assert result == mock_client
        mock_boto3_client.assert_called_once_with(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
        )

    @patch("util.aws_sts.boto3.client")
    def test_create_aws_client_with_session_token(self, mock_boto3_client):
        mock_client = MagicMock(spec=BaseClient)
        mock_boto3_client.return_value = mock_client

        result = create_aws_client(
            service_name="kinesis",
            region="us-west-2",
            access_key="test_access_key",
            secret_key="test_secret_key",
            session_token="test_session_token",
        )

        assert result == mock_client
        mock_boto3_client.assert_called_once_with(
            "kinesis",
            region_name="us-west-2",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
            aws_session_token="test_session_token",
        )

    @patch("util.aws_sts.boto3.client")
    def test_create_aws_client_without_region(self, mock_boto3_client):
        mock_client = MagicMock(spec=BaseClient)
        mock_boto3_client.return_value = mock_client

        result = create_aws_client(
            service_name="cloudwatch",
            access_key="test_access_key",
            secret_key="test_secret_key",
        )

        assert result == mock_client
        mock_boto3_client.assert_called_once_with(
            "cloudwatch",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_key",
        )

    def test_create_aws_client_missing_credentials_raises_error(self):
        with pytest.raises(ValueError, match="access_key and secret_key are required"):
            create_aws_client(service_name="s3")

        with pytest.raises(ValueError, match="access_key and secret_key are required"):
            create_aws_client(service_name="s3", access_key="test_key")

        with pytest.raises(ValueError, match="access_key and secret_key are required"):
            create_aws_client(service_name="s3", secret_key="test_secret")

    @patch("util.aws_sts._create_sts_client")
    def test_create_aws_client_with_sts_role_arn(self, mock_create_sts_client):
        mock_client = MagicMock(spec=BaseClient)
        mock_create_sts_client.return_value = mock_client

        result = create_aws_client(
            service_name="s3",
            region="us-east-1",
            sts_role_arn="arn:aws:iam::123456789012:role/test-role",
        )

        assert result == mock_client
        mock_create_sts_client.assert_called_once_with(
            service_name="s3",
            region="us-east-1",
            sts_role_arn="arn:aws:iam::123456789012:role/test-role",
            web_identity_token_file="/var/run/secrets/openshift/serviceaccount/token",
            role_session_name="quay-s3-sts",
        )


class TestCreateStsClient:
    """Test cases for _create_sts_client function."""

    @patch("util.aws_sts.boto3.client")
    @patch("util.aws_sts.Session")
    @patch("builtins.open", new_callable=mock_open, read_data="test-token-content")
    @patch("util.aws_sts.os.path.exists", return_value=True)
    def test_create_sts_client_with_region(
        self, mock_exists, mock_file, mock_session, mock_boto3_client
    ):
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client

        mock_sts_client.assume_role_with_web_identity.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }

        mock_service_client = MagicMock(spec=BaseClient)
        mock_boto3_client.return_value = mock_service_client

        result = _create_sts_client(
            service_name="s3",
            region="us-east-1",
            sts_role_arn="arn:aws:iam::123456789012:role/test-role",
            web_identity_token_file="/test/token/file",
            role_session_name="test-session",
        )

        assert result == mock_service_client
        mock_exists.assert_called_once_with("/test/token/file")
        mock_file.assert_called_once_with("/test/token/file", "r")
        mock_session_instance.client.assert_called_once_with("sts", region_name="us-east-1")
        mock_sts_client.assume_role_with_web_identity.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/test-role",
            RoleSessionName="test-session",
            WebIdentityToken="test-token-content",
        )
        mock_boto3_client.assert_called_once_with(
            "s3",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            aws_session_token="test-session-token",
            region_name="us-east-1",
        )

    @patch("util.aws_sts.boto3.client")
    @patch("util.aws_sts.Session")
    @patch("builtins.open", new_callable=mock_open, read_data="test-token-content")
    @patch("util.aws_sts.os.path.exists", return_value=True)
    def test_create_sts_client_without_region(
        self, mock_exists, mock_file, mock_session, mock_boto3_client
    ):
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        mock_sts_client = MagicMock()
        mock_session_instance.client.return_value = mock_sts_client

        mock_sts_client.assume_role_with_web_identity.return_value = {
            "Credentials": {
                "AccessKeyId": "test-access-key",
                "SecretAccessKey": "test-secret-key",
                "SessionToken": "test-session-token",
            }
        }

        mock_service_client = MagicMock(spec=BaseClient)
        mock_boto3_client.return_value = mock_service_client

        result = _create_sts_client(
            service_name="kinesis",
            region=None,
            sts_role_arn="arn:aws:iam::123456789012:role/test-role",
            web_identity_token_file="/test/token/file",
            role_session_name="test-session",
        )

        assert result == mock_service_client
        mock_exists.assert_called_once_with("/test/token/file")
        mock_file.assert_called_once_with("/test/token/file", "r")
        mock_session_instance.client.assert_called_once_with("sts")
        mock_sts_client.assume_role_with_web_identity.assert_called_once_with(
            RoleArn="arn:aws:iam::123456789012:role/test-role",
            RoleSessionName="test-session",
            WebIdentityToken="test-token-content",
        )
        mock_boto3_client.assert_called_once_with(
            "kinesis",
            aws_access_key_id="test-access-key",
            aws_secret_access_key="test-secret-key",
            aws_session_token="test-session-token",
        )
