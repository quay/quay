import base64
import binascii
import json
import logging
import os
import tempfile

from requests import Request, Session

from _init import IS_KUBERNETES

logger = logging.getLogger(__name__)

DEFAULT_BOOTSTRAP_TOKEN_PATH = "/var/lib/quay/quay-machine-token.json"

KUBERNETES_API_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
_port = os.environ.get("KUBERNETES_SERVICE_PORT")
if _port:
    KUBERNETES_API_HOST += ":" + _port


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
        with open(path) as f:
            return _access_token_from_json(f.read())
    except FileNotFoundError:
        return None


def write_token_file(path, access_token):
    """Write {"access_token": "..."} to path with 0600 permissions.

    Creates parent directories if they don't exist. Uses atomic rename
    to prevent partial writes.

    Raises OSError on failure.
    """
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent, suffix=".tmp")
        content = json.dumps({"access_token": access_token})
        os.write(fd, content.encode("utf-8"))
        os.fchmod(fd, 0o600)
        os.close(fd)
        fd = None
        os.rename(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_path is not None and os.path.exists(tmp_path):
            os.unlink(tmp_path)


class KubernetesTokenProvider:
    """Reads and writes bootstrap token data in a Kubernetes Secret."""

    SA_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    SA_NAMESPACE_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
    SA_CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

    def __init__(self, secret_name, key_name, namespace=None, api_host=None, sa_token_path=None):
        sa_token_path = sa_token_path or self.SA_TOKEN_PATH
        if not os.path.exists(sa_token_path):
            raise OSError("Cannot load Kubernetes service account token")
        if not os.path.exists(self.SA_CA_CERT_PATH):
            raise OSError("Cannot load Kubernetes service account CA certificate")

        with open(sa_token_path, "r") as f:
            self._service_token = f.read()

        self._api_host = api_host or KUBERNETES_API_HOST
        self._secret_name = secret_name
        self._key_name = key_name

        if namespace is not None:
            self._namespace = namespace
        else:
            with open(self.SA_NAMESPACE_PATH, "r") as f:
                self._namespace = f.read().strip()

    def read_token(self):
        """Read {"access_token": "..."} from the Secret, returning None if absent/malformed."""
        try:
            secret_url = "namespaces/%s/secrets/%s" % (self._namespace, self._secret_name)
            response = self._execute_k8s_api("GET", secret_url)
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                raise OSError(
                    "Failed to read K8s Secret '%s' (HTTP %d)"
                    % (self._secret_name, response.status_code)
                )

            secret = json.loads(response.text)
            encoded_token = secret.get("data", {}).get(self._key_name)
            if not encoded_token:
                return None

            token_json = base64.b64decode(encoded_token).decode("utf-8")
            return _access_token_from_json(token_json)
        except (binascii.Error, UnicodeDecodeError, ValueError, TypeError):
            return None
        except OSError:
            raise
        except Exception as exc:
            raise OSError("K8s API call failed: %s" % exc) from exc

    def write_token(self, access_token):
        """Write {"access_token": "..."} to the Secret under key_name.

        Raises OSError on failure.
        """
        try:
            secret_url = "namespaces/%s/secrets/%s" % (self._namespace, self._secret_name)
            response = self._execute_k8s_api("GET", secret_url)
            if response.status_code != 200:
                raise OSError(
                    "Bootstrap token K8s Secret '%s' not found (HTTP %d)"
                    % (self._secret_name, response.status_code)
                )

            secret = json.loads(response.text)
            secret.setdefault("data", {})
            token_json = json.dumps({"access_token": access_token})
            secret["data"][self._key_name] = base64.b64encode(token_json.encode("utf-8")).decode(
                "ascii"
            )

            response = self._execute_k8s_api("PUT", secret_url, secret)
            if response.status_code != 200:
                raise OSError(
                    "Failed to update K8s Secret '%s' (HTTP %d)"
                    % (self._secret_name, response.status_code)
                )
        except OSError:
            raise
        except Exception as exc:
            raise OSError("K8s API call failed: %s" % exc) from exc

    def _execute_k8s_api(self, method, relative_url, data=None):
        headers = {"Authorization": "Bearer " + self._service_token}
        if data:
            headers["Content-Type"] = "application/json"

        data = json.dumps(data) if data else None
        session = Session()
        url = "https://%s/api/v1/%s" % (self._api_host, relative_url)
        request = Request(method, url, data=data, headers=headers)
        return session.send(request.prepare(), verify=self.SA_CA_CERT_PATH, timeout=2)


def read_bootstrap_token(app_config):
    """Read token from filesystem or K8s Secret, returning None if absent/malformed."""
    k8s_secret = app_config.get("PROGRAMMATIC_TOKEN_K8S_SECRET")

    if IS_KUBERNETES and k8s_secret:
        k8s_key = app_config.get("PROGRAMMATIC_TOKEN_K8S_KEY", "token.json")
        k8s_ns = app_config.get("PROGRAMMATIC_TOKEN_K8S_NAMESPACE")
        provider = KubernetesTokenProvider(k8s_secret, k8s_key, namespace=k8s_ns)
        return provider.read_token()

    token_path = app_config.get(
        "PROGRAMMATIC_TOKEN_PATH",
        DEFAULT_BOOTSTRAP_TOKEN_PATH,
    )
    return read_token_file(token_path)


def write_bootstrap_token(app_config, access_token):
    """Write token to filesystem or to K8s Secret.

    In K8s mode with PROGRAMMATIC_TOKEN_K8S_SECRET configured, writes
    only to the K8s Secret via the API. The Operator mounts that Secret
    into the pod at PROGRAMMATIC_TOKEN_PATH, so Kubernetes handles
    filesystem exposure. No local file write is attempted (the mounted
    volume is read-only).

    Outside K8s (or without PROGRAMMATIC_TOKEN_K8S_SECRET), writes
    directly to the local filesystem.

    Raises OSError on failure so callers can roll back the DB token.
    """
    k8s_secret = app_config.get("PROGRAMMATIC_TOKEN_K8S_SECRET")

    if IS_KUBERNETES and k8s_secret:
        k8s_key = app_config.get("PROGRAMMATIC_TOKEN_K8S_KEY", "token.json")
        k8s_ns = app_config.get("PROGRAMMATIC_TOKEN_K8S_NAMESPACE")
        provider = KubernetesTokenProvider(k8s_secret, k8s_key, namespace=k8s_ns)
        provider.write_token(access_token)
        return

    token_path = app_config.get(
        "PROGRAMMATIC_TOKEN_PATH",
        DEFAULT_BOOTSTRAP_TOKEN_PATH,
    )
    write_token_file(token_path, access_token)
