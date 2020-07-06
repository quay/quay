import os
import logging
import json
import base64
import time

from io import StringIO
from requests import Request, Session

from util.config.provider.baseprovider import CannotWriteConfigException, get_yaml
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

    def get_volume_path(self, directory, filename):
        # NOTE: Overridden to ensure we don't have subdirectories, which aren't supported
        # in Kubernetes secrets.
        return "_".join([directory.rstrip("/"), filename])

    def volume_exists(self):
        secret = self._lookup_secret()
        return secret is not None

    def volume_file_exists(self, relative_file_path):
        if "/" in relative_file_path:
            raise Exception("Expected path from get_volume_path, but found slashes")

        # NOTE: Overridden because we don't have subdirectories, which aren't supported
        # in Kubernetes secrets.
        secret = self._lookup_secret()
        if not secret or not secret.get("data"):
            return False
        return relative_file_path in secret["data"]

    def list_volume_directory(self, path):
        # NOTE: Overridden because we don't have subdirectories, which aren't supported
        # in Kubernetes secrets.
        secret = self._lookup_secret()

        if not secret:
            return []

        paths = []
        for filename in secret.get("data", {}):
            if filename.startswith(path):
                paths.append(filename[len(path) + 1 :])
        return paths

    def save_config(self, config_obj):
        self._update_secret_file(self.yaml_filename, get_yaml(config_obj))

    def remove_volume_file(self, relative_file_path):
        try:
            self._update_secret_file(relative_file_path, None)
        except IOError as ioe:
            raise CannotWriteConfigException(str(ioe))

    def save_volume_file(self, flask_file, relative_file_path):
        # Write the file to a temp location.
        buf = StringIO()
        try:
            try:
                flask_file.save(buf)
            except IOError as ioe:
                raise CannotWriteConfigException(str(ioe))

            self._update_secret_file(relative_file_path, buf.getvalue())
        finally:
            buf.close()

    def _assert_success(self, response):
        if response.status_code != 200:
            logger.error(
                "Kubernetes API call failed with response: %s => %s",
                response.status_code,
                response.text,
            )
            raise CannotWriteConfigException("Kubernetes API call failed: %s" % response.text)

    def _update_secret_file(self, relative_file_path, value=None):
        if "/" in relative_file_path:
            raise Exception("Expected path from get_volume_path, but found slashes")

        # Check first that the namespace for Red Hat Quay exists. If it does not, report that
        # as an error, as it seems to be a common issue.
        namespace_url = "namespaces/%s" % (QE_NAMESPACE)
        response = self._execute_k8s_api("GET", namespace_url)
        if response.status_code // 100 != 2:
            msg = (
                "A Kubernetes namespace with name `%s` must be created to save config"
                % QE_NAMESPACE
            )
            raise CannotWriteConfigException(msg)

        # Check if the secret exists. If not, then we create an empty secret and then update the file
        # inside.
        secret_url = "namespaces/%s/secrets/%s" % (QE_NAMESPACE, QE_CONFIG_SECRET)
        secret = self._lookup_secret()
        if secret is None:
            self._assert_success(
                self._execute_k8s_api(
                    "POST",
                    secret_url,
                    {
                        "kind": "Secret",
                        "apiVersion": "v1",
                        "metadata": {"name": QE_CONFIG_SECRET},
                        "data": {},
                    },
                )
            )

        # Update the secret to reflect the file change.
        secret["data"] = secret.get("data", {})

        if value is not None:
            secret["data"][relative_file_path] = base64.b64encode(value.encode("ascii")).decode(
                "ascii"
            )
        else:
            secret["data"].pop(relative_file_path)

        self._assert_success(self._execute_k8s_api("PUT", secret_url, secret))

        # Wait until the local mounted copy of the secret has been updated, as
        # this is an eventual consistency operation, but the caller expects immediate
        # consistency.
        while True:
            matching_files = set()
            for secret_filename, encoded_value in secret["data"].items():
                expected_value = base64.b64decode(encoded_value).decode("utf-8")
                try:
                    with self.get_volume_file(secret_filename) as f:
                        contents = f.read()

                    if contents == expected_value:
                        matching_files.add(secret_filename)
                except IOError:
                    continue

            if matching_files == set(secret["data"].keys()):
                break

            # Sleep for a second and then try again.
            time.sleep(1)

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
