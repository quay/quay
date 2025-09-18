"""
Utilities for creating AWS clients with OpenShift STS support.
"""
import logging
import os
from typing import Any, Callable, Dict, Optional

import boto3
from boto3.session import Session
from botocore.client import BaseClient
from botocore.credentials import DeferredRefreshableCredentials

logger = logging.getLogger(__name__)


def create_aws_client(
    service_name: str,
    region: Optional[str] = None,
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    session_token: Optional[str] = None,
    role_arn: Optional[str] = None,
    web_identity_token_file: Optional[str] = None,
    role_session_name: Optional[str] = None,
    **client_kwargs: Any,
) -> BaseClient:
    """
    Create an AWS client with IAM keys or STS.

    This function provides a unified way to create AWS clients that can use either:
    1. Traditional IAM user credentials (access_key/secret_key)
    2. OpenShift STS with ISRA (role_arn)

    Args:
        service_name: AWS service name (e.g., 's3', 'kinesis', 'cloudwatch')
        region: AWS region
        access_key: AWS access key ID (for traditional auth)
        secret_key: AWS secret access key (for traditional auth)
        session_token: AWS session token (for traditional auth)
        role_arn: IAM role ARN for STS authentication
        web_identity_token_file: Path to service account token file
        role_session_name: Session name for STS role assumption
        **client_kwargs: Additional arguments passed to boto3.client()

    Returns:
        boto3 client instance

    Raises:
        RuntimeError: If STS authentication fails
        ValueError: If required parameters are missing
    """
    # Default values for OpenShift STS
    if web_identity_token_file is None:
        web_identity_token_file = "/var/run/secrets/openshift/serviceaccount/token"
    if role_session_name is None:
        role_session_name = f"quay-{service_name}-sts"

    # If STS role ARN is provided, use OpenShift STS authentication
    if role_arn:
        return _create_sts_client(
            service_name=service_name,
            region=region,
            role_arn=role_arn,
            web_identity_token_file=web_identity_token_file,
            role_session_name=role_session_name,
            **client_kwargs,
        )

    # Otherwise, use traditional credential-based authentication
    if not (access_key and secret_key):
        raise ValueError("access_key and secret_key are required when not using STS authentication")

    kwargs: dict[str, str] = {}
    if region:
        kwargs["region_name"] = region
    kwargs["aws_access_key_id"] = access_key
    kwargs["aws_secret_access_key"] = secret_key
    if session_token:
        kwargs["aws_session_token"] = session_token
    kwargs.update(client_kwargs)
    return boto3.client(service_name, **kwargs)  # type: ignore[arg-type]


def _create_sts_client(
    service_name: str,
    region: Optional[str],
    role_arn: str,
    web_identity_token_file: str,
    role_session_name: str,
    **client_kwargs: Any,
) -> BaseClient:
    """
    Create an AWS client using OpenShift STS authentication.
    """
    if not os.path.exists(web_identity_token_file):
        raise RuntimeError(f"Web identity token file not found: {web_identity_token_file}")

    session = Session()

    sts_client = session.client("sts", region_name=region) if region else session.client("sts")

    with open(web_identity_token_file, "r") as token_file:
        web_identity_token = token_file.read().strip()

    response = sts_client.assume_role_with_web_identity(
        RoleArn=role_arn,
        RoleSessionName=role_session_name,
        WebIdentityToken=web_identity_token,
    )

    temp_credentials = response["Credentials"]

    if region:
        return boto3.client(
            service_name,
            aws_access_key_id=temp_credentials["AccessKeyId"],
            aws_secret_access_key=temp_credentials["SecretAccessKey"],
            aws_session_token=temp_credentials["SessionToken"],
            region_name=region,
            **client_kwargs,
        )
    else:
        return boto3.client(
            service_name,
            aws_access_key_id=temp_credentials["AccessKeyId"],
            aws_secret_access_key=temp_credentials["SecretAccessKey"],
            aws_session_token=temp_credentials["SessionToken"],
            **client_kwargs,
        )
