import logging

from flask import request, make_response

from config_app.config_util.config import get_config_as_kube_secret
from data.database import configure

from config_app.c_app import app, config_provider
from config_app.config_endpoints.api import (
    resource,
    ApiResource,
    nickname,
    kubernetes_only,
    validate_json_request,
)
from config_app.config_util.k8saccessor import KubernetesAccessorSingleton, K8sApiException

logger = logging.getLogger(__name__)


@resource("/v1/kubernetes/deployments/")
class SuperUserKubernetesDeployment(ApiResource):
    """ Resource for the getting the status of Red Hat Quay deployments and cycling them """

    schemas = {
        "ValidateDeploymentNames": {
            "type": "object",
            "description": "Validates deployment names for cycling",
            "required": ["deploymentNames"],
            "properties": {
                "deploymentNames": {
                    "type": "array",
                    "description": "The names of the deployments to cycle",
                },
            },
        }
    }

    @kubernetes_only
    @nickname("scGetNumDeployments")
    def get(self):
        return KubernetesAccessorSingleton.get_instance().get_qe_deployments()

    @kubernetes_only
    @validate_json_request("ValidateDeploymentNames")
    @nickname("scCycleQEDeployments")
    def put(self):
        deployment_names = request.get_json()["deploymentNames"]
        return KubernetesAccessorSingleton.get_instance().cycle_qe_deployments(deployment_names)


@resource("/v1/kubernetes/deployment/<deployment>/status")
class QEDeploymentRolloutStatus(ApiResource):
    @kubernetes_only
    @nickname("scGetDeploymentRolloutStatus")
    def get(self, deployment):
        deployment_rollout_status = KubernetesAccessorSingleton.get_instance().get_deployment_rollout_status(
            deployment
        )
        return {
            "status": deployment_rollout_status.status,
            "message": deployment_rollout_status.message,
        }


@resource("/v1/kubernetes/deployments/rollback")
class QEDeploymentRollback(ApiResource):
    """ Resource for rolling back deployments """

    schemas = {
        "ValidateDeploymentNames": {
            "type": "object",
            "description": "Validates deployment names for rolling back",
            "required": ["deploymentNames"],
            "properties": {
                "deploymentNames": {
                    "type": "array",
                    "description": "The names of the deployments to rollback",
                },
            },
        }
    }

    @kubernetes_only
    @nickname("scRollbackDeployments")
    @validate_json_request("ValidateDeploymentNames")
    def post(self):
        """
    Returns the config to its original state and rolls back deployments
    :return:
    """
        deployment_names = request.get_json()["deploymentNames"]

        # To roll back a deployment, we must do 2 things:
        # 1. Roll back the config secret to its old value (discarding changes we made in this session)
        # 2. Trigger a rollback to the previous revision, so that the pods will be restarted with
        # the old config
        old_secret = get_config_as_kube_secret(config_provider.get_old_config_dir())
        kube_accessor = KubernetesAccessorSingleton.get_instance()
        kube_accessor.replace_qe_secret(old_secret)

        try:
            for name in deployment_names:
                kube_accessor.rollback_deployment(name)
        except K8sApiException as e:
            logger.exception("Failed to rollback deployment.")
            return make_response(e.message, 503)

        return make_response("Ok", 204)


@resource("/v1/kubernetes/config")
class SuperUserKubernetesConfiguration(ApiResource):
    """ Resource for saving the config files to kubernetes secrets. """

    @kubernetes_only
    @nickname("scDeployConfiguration")
    def post(self):
        try:
            new_secret = get_config_as_kube_secret(config_provider.get_config_dir_path())
            KubernetesAccessorSingleton.get_instance().replace_qe_secret(new_secret)
        except K8sApiException as e:
            logger.exception("Failed to deploy qe config secret to kubernetes.")
            return make_response(e.message, 503)

        return make_response("Ok", 201)


@resource("/v1/kubernetes/config/populate")
class KubernetesConfigurationPopulator(ApiResource):
    """ Resource for populating the local configuration from the cluster's kubernetes secrets. """

    @kubernetes_only
    @nickname("scKubePopulateConfig")
    def post(self):
        # Get a clean transient directory to write the config into
        config_provider.new_config_dir()

        kube_accessor = KubernetesAccessorSingleton.get_instance()
        kube_accessor.save_secret_to_directory(config_provider.get_config_dir_path())
        config_provider.create_copy_of_config_dir()

        # We update the db configuration to connect to their specified one
        # (Note, even if this DB isn't valid, it won't affect much in the config app, since we'll report an error,
        # and all of the options create a new clean dir, so we'll never pollute configs)
        combined = dict(**app.config)
        combined.update(config_provider.get_config())
        configure(combined)

        return 200
