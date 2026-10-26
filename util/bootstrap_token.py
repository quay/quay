import base64
import binascii
import json
import os
import tempfile
from urllib.parse import quote

import requests

from _init import IS_KUBERNETES

DEFAULT_BOOTSTRAP_TOKEN_PATH = "/var/lib/quay/quay-machine-token.json"
DEFAULT_KUBERNETES_TOKEN_KEY = "token.json"
MAX_BOOTSTRAP_TOKEN_FILE_BYTES = 4096
KUBERNETES_API_HOST = None


class KubernetesTokenProvider:
    SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    SA_NAMESPACE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    SA_CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    def __init__(self, app_config):
        self.secret_name = app_config["PROGRAMMATIC_TOKEN_K8S_SECRET"]
        self.key = app_config.get("PROGRAMMATIC_TOKEN_K8S_KEY", DEFAULT_KUBERNETES_TOKEN_KEY)
        self.service_account_token = self._read_required_file(
            self.SA_TOKEN_PATH, "service account token"
        )
        self.namespace = app_config.get(
            "PROGRAMMATIC_TOKEN_K8S_NAMESPACE"
        ) or self._read_required_file(self.SA_NAMESPACE_PATH, "service account namespace")
        self.ca_cert_path = self.SA_CA_CERT_PATH
        if not os.path.exists(self.ca_cert_path):
            raise OSError("Cannot load Kubernetes service account CA certificate")
        self.api_host = KUBERNETES_API_HOST or self._build_api_host()

    def read_token(self):
        secret = self._get_secret(missing_ok=True)
        if secret is None:
            return None

        data = secret.get("data")
        if not isinstance(data, dict):
            return None

        encoded_token = data.get(self.key)
        if not isinstance(encoded_token, str):
            return None

        try:
            token_json = base64.b64decode(encoded_token, validate=True).decode("utf-8")
        except (binascii.Error, ValueError, TypeError, UnicodeDecodeError):
            return None

        return _access_token_from_json(token_json)

    def write_token(self, access_token):
        secret = self._get_secret(missing_ok=False)
        data = secret.get("data")
        if data is None:
            data = {}
            secret["data"] = data
        elif not isinstance(data, dict):
            raise OSError("Kubernetes Secret data must be an object")

        token_json = json.dumps({"access_token": access_token})
        data[self.key] = base64.b64encode(token_json.encode("utf-8")).decode("ascii")

        response = self._request("PUT", secret)
        if response.status_code != 200:
            raise OSError("Kubernetes Secret update failed: %s" % response.text)

    def delete_token(self):
        secret = self._get_secret(missing_ok=True)
        if secret is None:
            return False

        data = secret.get("data")
        if data is None:
            return False
        if not isinstance(data, dict):
            raise OSError("Kubernetes Secret data must be an object")
        if self.key not in data:
            return False

        del data[self.key]
        response = self._request("PUT", secret)
        if response.status_code != 200:
            raise OSError("Kubernetes Secret update failed: %s" % response.text)
        return True

    def _get_secret(self, missing_ok):
        response = self._request("GET")
        if response.status_code == 404 and missing_ok:
            return None
        if response.status_code == 404:
            raise OSError("Kubernetes Secret not found: %s" % self.secret_name)
        if response.status_code != 200:
            raise OSError("Kubernetes Secret read failed: %s" % response.text)

        try:
            secret = response.json()
        except ValueError as exc:
            raise OSError("Kubernetes Secret response was not valid JSON") from exc

        if not isinstance(secret, dict):
            raise OSError("Kubernetes Secret response must be a JSON object")
        return secret

    def _request(self, method, secret=None):
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.service_account_token,
        }
        request_kwargs = {}
        if secret is not None:
            headers["Content-Type"] = "application/json"
            request_kwargs["json"] = secret

        url = "https://%s/api/v1/namespaces/%s/secrets/%s" % (
            self.api_host,
            quote(self.namespace, safe=""),
            quote(self.secret_name, safe=""),
        )
        try:
            return requests.request(
                method,
                url,
                headers=headers,
                verify=self.ca_cert_path,
                timeout=2,
                **request_kwargs,
            )
        except requests.RequestException as exc:
            raise OSError("Kubernetes API request failed") from exc

    @classmethod
    def _read_required_file(cls, path, description):
        try:
            with open(path, encoding="utf-8") as f:
                value = f.read().strip()
        except OSError as exc:
            raise OSError("Cannot load Kubernetes %s" % description) from exc

        if not value:
            raise OSError("Cannot load Kubernetes %s" % description)
        return value

    @classmethod
    def _build_api_host(cls):
        host = os.environ.get("KUBERNETES_SERVICE_HOST")
        port = os.environ.get("KUBERNETES_SERVICE_PORT")
        if not host:
            raise OSError("Cannot determine Kubernetes API host")

        if ":" in host and not host.startswith("["):
            host = "[%s]" % host
        if port:
            return "%s:%s" % (host, port)
        return host


def _use_kubernetes_secret_storage(app_config):
    return IS_KUBERNETES and bool(app_config.get("PROGRAMMATIC_TOKEN_K8S_SECRET"))


def _local_token_path(app_config):
    return app_config.get("BOOTSTRAP_TOKEN_PATH", DEFAULT_BOOTSTRAP_TOKEN_PATH)


def _access_token_from_json(token_json):
    try:
        data = json.loads(token_json)
    except (TypeError, ValueError):
        return None

    access_token = data.get("access_token") if isinstance(data, dict) else None
    return access_token if isinstance(access_token, str) and access_token else None


def read_token_file(path):
    """Read an access token from path, returning None if it is missing or malformed."""
    try:
        with open(path, encoding="utf-8") as f:
            token_json = f.read(MAX_BOOTSTRAP_TOKEN_FILE_BYTES + 1)
    except (OSError, UnicodeDecodeError):
        return None

    if len(token_json) > MAX_BOOTSTRAP_TOKEN_FILE_BYTES:
        return None

    return _access_token_from_json(token_json)


def delete_token_file(path):
    """Delete path if present, returning whether a file was removed.

    Missing files are expected in multi-node installations where bootstrap token
    files are node-local. Raises OSError for failures other than absence.
    """
    try:
        os.unlink(path)
    except FileNotFoundError:
        return False

    return True


def write_token_file(path, access_token):
    """Write {"access_token": "..."} to path with 0600 permissions.

    Creates parent directories if they don't exist and uses atomic replacement to
    prevent partial writes. Raises OSError on failure.
    """
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, mode=0o700, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent or None, suffix=".tmp")
        content = json.dumps({"access_token": access_token})
        os.write(fd, content.encode("utf-8"))
        os.fchmod(fd, 0o600)
        os.close(fd)
        fd = None
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def read_bootstrap_token(app_config):
    """Read the configured bootstrap token, returning None if absent or malformed."""
    if _use_kubernetes_secret_storage(app_config):
        return KubernetesTokenProvider(app_config).read_token()

    return read_token_file(_local_token_path(app_config))


def write_bootstrap_token(app_config, access_token):
    """Write the configured bootstrap token.

    Raises OSError on failure so callers can roll back database token state.
    """
    if _use_kubernetes_secret_storage(app_config):
        KubernetesTokenProvider(app_config).write_token(access_token)
        return

    write_token_file(_local_token_path(app_config), access_token)


def delete_bootstrap_token(app_config):
    """Delete the configured bootstrap token if present.

    Returns whether a token was removed. Missing files and missing Secret keys
    are not errors because token storage may be node-local or externally managed.
    """
    if _use_kubernetes_secret_storage(app_config):
        return KubernetesTokenProvider(app_config).delete_token()

    return delete_token_file(_local_token_path(app_config))
