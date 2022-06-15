import os
import logging
import json

from requests import Request, Session

from util.config.provider.basefileprovider import BaseFileProvider

logger = logging.getLogger(__name__)

KUBERNETES_API_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
port = os.environ.get("KUBERNETES_SERVICE_PORT")
if port:
    KUBERNETES_API_HOST += ":" + port

SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

QE_NAMESPACE = os.environ.get("QE_K8S_NAMESPACE", "quay-enterprise")
QE_CONFIG_SECRET = os.environ.get("QE_K8S_CONFIG_SECRET", "quay-enterprise-config-secret")


class KubernetesConfigProvider(BaseFileProvider):
    """
    Implementation of the config provider that reads and writes configuration data from a Kubernetes
    Secret.
    """

    def __init__(
        self,
        config_volume,
        yaml_filename,
        py_filename,
        api_host=None,
        service_account_token_path=None,
    ):
        super(KubernetesConfigProvider, self).__init__(config_volume, yaml_filename, py_filename)
        service_account_token_path = service_account_token_path or SERVICE_ACCOUNT_TOKEN_PATH
        api_host = api_host or KUBERNETES_API_HOST

        # Load the service account token from the local store.
        if not os.path.exists(service_account_token_path):
            raise Exception("Cannot load Kubernetes service account token")

        with open(service_account_token_path, "r") as f:
            self._service_token = f.read()

        self._api_host = api_host

    @property
    def provider_id(self):
        return "k8s"

    def volume_file_exists(self, relative_file_path):
        if "/" in relative_file_path:
            raise Exception("Expected path from get_volume_path, but found slashes")

        # NOTE: Overridden because we don't have subdirectories, which aren't supported
        # in Kubernetes secrets.
        secret = self._lookup_secret()
        if not secret or not secret.get("data"):
            return False
        return relative_file_path in secret["data"]

    def _lookup_secret(self):
        secret_url = "namespaces/%s/secrets/%s" % (QE_NAMESPACE, QE_CONFIG_SECRET)
        response = self._execute_k8s_api("GET", secret_url)
        if response.status_code != 200:
            return None
        return json.loads(response.text)

    def _execute_k8s_api(self, method, relative_url, data=None):
        headers = {"Authorization": "Bearer " + self._service_token}

        if data:
            headers["Content-Type"] = "application/json"

        data = json.dumps(data) if data else None
        session = Session()
        url = "https://%s/api/v1/%s" % (self._api_host, relative_url)

        request = Request(method, url, data=data, headers=headers)
        return session.send(request.prepare(), verify=False, timeout=2)
