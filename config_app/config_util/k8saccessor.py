import logging
import json
import base64
import datetime
import os

from requests import Request, Session
from collections import namedtuple
from util.config.validator import EXTRA_CA_DIRECTORY, EXTRA_CA_DIRECTORY_PREFIX

from config_app.config_util.k8sconfig import KubernetesConfig

logger = logging.getLogger(__name__)

QE_DEPLOYMENT_LABEL = "quay-enterprise-component"
QE_CONTAINER_NAME = "quay-enterprise-app"


# Tuple containing response of the deployment rollout status method.
# status is one of: 'failed' | 'progressing' | 'available'
# message is any string describing the state.
DeploymentRolloutStatus = namedtuple("DeploymentRolloutStatus", ["status", "message"])


class K8sApiException(Exception):
    pass


def _deployment_rollout_status_message(deployment, deployment_name):
    """
    Gets the friendly human readable message of the current state of the deployment rollout.

    :param deployment: python dict matching: https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.11/#deployment-v1-apps
    :param deployment_name: string
    :return: DeploymentRolloutStatus
    """
    # Logic for rollout status pulled from the `kubectl rollout status` command:
    # https://github.com/kubernetes/kubernetes/blob/d9ba19c751709c8608e09a0537eea98973f3a796/pkg/kubectl/rollout_status.go#L62
    if deployment["metadata"]["generation"] <= deployment["status"]["observedGeneration"]:
        for cond in deployment["status"]["conditions"]:
            if cond["type"] == "Progressing" and cond["reason"] == "ProgressDeadlineExceeded":
                return DeploymentRolloutStatus(
                    status="failed",
                    message="Deployment %s's rollout failed. Please try again later."
                    % deployment_name,
                )

        desired_replicas = deployment["spec"]["replicas"]
        current_replicas = deployment["status"].get("replicas", 0)
        if current_replicas == 0:
            return DeploymentRolloutStatus(
                status="available",
                message="Deployment %s updated (no replicas, so nothing to roll out)"
                % deployment_name,
            )

        # Some fields are optional in the spec, so if they're omitted, replace with defaults that won't indicate a wrong status
        available_replicas = deployment["status"].get("availableReplicas", 0)
        updated_replicas = deployment["status"].get("updatedReplicas", 0)

        if updated_replicas < desired_replicas:
            return DeploymentRolloutStatus(
                status="progressing",
                message="Waiting for rollout to finish: %d out of %d new replicas have been updated..."
                % (updated_replicas, desired_replicas),
            )

        if current_replicas > updated_replicas:
            return DeploymentRolloutStatus(
                status="progressing",
                message="Waiting for rollout to finish: %d old replicas are pending termination..."
                % (current_replicas - updated_replicas),
            )

        if available_replicas < updated_replicas:
            return DeploymentRolloutStatus(
                status="progressing",
                message="Waiting for rollout to finish: %d of %d updated replicas are available..."
                % (available_replicas, updated_replicas),
            )

        return DeploymentRolloutStatus(
            status="available", message="Deployment %s successfully rolled out." % deployment_name
        )

    return DeploymentRolloutStatus(
        status="progressing", message="Waiting for deployment spec to be updated..."
    )


class KubernetesAccessorSingleton(object):
    """
    Singleton allowing access to kubernetes operations.
    """

    _instance = None

    def __init__(self, kube_config=None):
        self.kube_config = kube_config
        if kube_config is None:
            self.kube_config = KubernetesConfig.from_env()

        KubernetesAccessorSingleton._instance = self

    @classmethod
    def get_instance(cls, kube_config=None):
        """
        Singleton getter implementation, returns the instance if one exists, otherwise creates the
        instance and ties it to the class.

        :return: KubernetesAccessorSingleton
        """
        if cls._instance is None:
            return cls(kube_config)

        return cls._instance

    def save_secret_to_directory(self, dir_path):
        """
        Saves all files in the kubernetes secret to a local directory.

        Assumes the directory is empty.
        """
        secret = self._lookup_secret()

        secret_data = secret.get("data", {})

        # Make the `extra_ca_certs` dir to ensure we can populate extra certs
        extra_ca_dir_path = os.path.join(dir_path, EXTRA_CA_DIRECTORY)
        os.mkdir(extra_ca_dir_path)

        for secret_filename, data in secret_data.items():
            write_path = os.path.join(dir_path, secret_filename)

            if EXTRA_CA_DIRECTORY_PREFIX in secret_filename:
                write_path = os.path.join(
                    extra_ca_dir_path, secret_filename.replace(EXTRA_CA_DIRECTORY_PREFIX, "")
                )

            with open(write_path, "w") as f:
                f.write(base64.b64decode(data))

        return 200

    def save_file_as_secret(self, name, file_pointer):
        value = file_pointer.read()
        self._update_secret_file(name, value)

    def replace_qe_secret(self, new_secret_data):
        """
        Removes the old config and replaces it with the new_secret_data as one action.
        """
        # Check first that the namespace for Red Hat Quay exists. If it does not, report that
        # as an error, as it seems to be a common issue.
        namespace_url = "namespaces/%s" % (self.kube_config.qe_namespace)
        response = self._execute_k8s_api("GET", namespace_url)
        if response.status_code // 100 != 2:
            msg = (
                "A Kubernetes namespace with name `%s` must be created to save config"
                % self.kube_config.qe_namespace
            )
            raise Exception(msg)

        # Check if the secret exists. If not, then we create an empty secret and then update the file
        # inside.
        secret_url = "namespaces/%s/secrets/%s" % (
            self.kube_config.qe_namespace,
            self.kube_config.qe_config_secret,
        )
        secret = self._lookup_secret()
        if secret is None:
            self._assert_success(
                self._execute_k8s_api(
                    "POST",
                    secret_url,
                    {
                        "kind": "Secret",
                        "apiVersion": "v1",
                        "metadata": {"name": self.kube_config.qe_config_secret},
                        "data": {},
                    },
                )
            )

        # Update the secret to reflect the file change.
        secret["data"] = new_secret_data

        self._assert_success(self._execute_k8s_api("PUT", secret_url, secret))

    def get_deployment_rollout_status(self, deployment_name):
        """
        " Returns the status of a rollout of a given deployment.

        :return _DeploymentRolloutStatus
        """
        deployment_selector_url = "namespaces/%s/deployments/%s" % (
            self.kube_config.qe_namespace,
            deployment_name,
        )

        response = self._execute_k8s_api("GET", deployment_selector_url, api_prefix="apis/apps/v1")
        if response.status_code != 200:
            return DeploymentRolloutStatus(
                "failed", "Could not get deployment. Please check that the deployment exists"
            )

        deployment = json.loads(response.text)

        return _deployment_rollout_status_message(deployment, deployment_name)

    def get_qe_deployments(self):
        """
        " Returns all deployments matching the label selector provided in the KubeConfig.
        """
        deployment_selector_url = "namespaces/%s/deployments?labelSelector=%s%%3D%s" % (
            self.kube_config.qe_namespace,
            QE_DEPLOYMENT_LABEL,
            self.kube_config.qe_deployment_selector,
        )

        response = self._execute_k8s_api(
            "GET", deployment_selector_url, api_prefix="apis/extensions/v1beta1"
        )
        if response.status_code != 200:
            return None
        return json.loads(response.text)

    def cycle_qe_deployments(self, deployment_names):
        """
        " Triggers a rollout of all desired deployments in the qe namespace.
        """

        for name in deployment_names:
            logger.debug("Cycling deployment %s", name)
            deployment_url = "namespaces/%s/deployments/%s" % (self.kube_config.qe_namespace, name)

            # There is currently no command to simply rolling restart all the pods: https://github.com/kubernetes/kubernetes/issues/13488
            # Instead, we modify the template of the deployment with a dummy env variable to trigger a cycle of the pods
            # (based off this comment: https://github.com/kubernetes/kubernetes/issues/13488#issuecomment-240393845)
            self._assert_success(
                self._execute_k8s_api(
                    "PATCH",
                    deployment_url,
                    {
                        "spec": {
                            "template": {
                                "spec": {
                                    "containers": [
                                        {
                                            # Note: this name MUST match the deployment template's pod template
                                            # (e.g. <template>.spec.template.spec.containers[0] == 'quay-enterprise-app')
                                            "name": QE_CONTAINER_NAME,
                                            "env": [
                                                {
                                                    "name": "RESTART_TIME",
                                                    "value": str(datetime.datetime.now()),
                                                }
                                            ],
                                        }
                                    ]
                                }
                            }
                        }
                    },
                    api_prefix="apis/extensions/v1beta1",
                    content_type="application/strategic-merge-patch+json",
                )
            )

    def rollback_deployment(self, deployment_name):
        deployment_rollback_url = "namespaces/%s/deployments/%s/rollback" % (
            self.kube_config.qe_namespace,
            deployment_name,
        )

        self._assert_success(
            self._execute_k8s_api(
                "POST",
                deployment_rollback_url,
                {
                    "name": deployment_name,
                    "rollbackTo": {
                        # revision=0 makes the deployment rollout to the previous revision
                        "revision": 0
                    },
                },
                api_prefix="apis/extensions/v1beta1",
            ),
            201,
        )

    def _assert_success(self, response, expected_code=200):
        if response.status_code != expected_code:
            logger.error(
                "Kubernetes API call failed with response: %s => %s",
                response.status_code,
                response.text,
            )
            raise K8sApiException("Kubernetes API call failed: %s" % response.text)

    def _update_secret_file(self, relative_file_path, value=None):
        if "/" in relative_file_path:
            raise Exception("Expected path from get_volume_path, but found slashes")

        # Check first that the namespace for Red Hat Quay exists. If it does not, report that
        # as an error, as it seems to be a common issue.
        namespace_url = "namespaces/%s" % (self.kube_config.qe_namespace)
        response = self._execute_k8s_api("GET", namespace_url)
        if response.status_code // 100 != 2:
            msg = (
                "A Kubernetes namespace with name `%s` must be created to save config"
                % self.kube_config.qe_namespace
            )
            raise Exception(msg)

        # Check if the secret exists. If not, then we create an empty secret and then update the file
        # inside.
        secret_url = "namespaces/%s/secrets/%s" % (
            self.kube_config.qe_namespace,
            self.kube_config.qe_config_secret,
        )
        secret = self._lookup_secret()
        if secret is None:
            self._assert_success(
                self._execute_k8s_api(
                    "POST",
                    secret_url,
                    {
                        "kind": "Secret",
                        "apiVersion": "v1",
                        "metadata": {"name": self.kube_config.qe_config_secret},
                        "data": {},
                    },
                )
            )

        # Update the secret to reflect the file change.
        secret["data"] = secret.get("data", {})

        if value is not None:
            secret["data"][relative_file_path] = base64.b64encode(value)
        else:
            secret["data"].pop(relative_file_path)

        self._assert_success(self._execute_k8s_api("PUT", secret_url, secret))

    def _lookup_secret(self):
        secret_url = "namespaces/%s/secrets/%s" % (
            self.kube_config.qe_namespace,
            self.kube_config.qe_config_secret,
        )
        response = self._execute_k8s_api("GET", secret_url)
        if response.status_code != 200:
            return None
        return json.loads(response.text)

    def _execute_k8s_api(
        self, method, relative_url, data=None, api_prefix="api/v1", content_type="application/json"
    ):
        headers = {"Authorization": "Bearer " + self.kube_config.service_account_token}

        if data:
            headers["Content-Type"] = content_type

        data = json.dumps(data) if data else None
        session = Session()
        url = "https://%s/%s/%s" % (self.kube_config.api_host, api_prefix, relative_url)

        request = Request(method, url, data=data, headers=headers)
        return session.send(request.prepare(), verify=False, timeout=2)
