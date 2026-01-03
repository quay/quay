"""
Kubernetes/OpenShift service account utilities.

Provides centralized constants and helpers for working with in-cluster
service account credentials.
"""

import os

# Kubernetes service account paths (mounted in-cluster)
SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SERVICE_ACCOUNT_CA_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


def get_ssl_verification() -> str | bool:
    """
    Get SSL verification setting for in-cluster Kubernetes API calls.

    When running inside a Kubernetes/OpenShift cluster, the API server uses
    a self-signed certificate. This function returns the path to the CA
    certificate if available, allowing proper SSL verification.

    Returns:
        str or bool: Path to CA certificate if it exists, otherwise True
                     (which uses system CA certificates).
    """
    if os.path.exists(SERVICE_ACCOUNT_CA_PATH):
        return SERVICE_ACCOUNT_CA_PATH
    return True
