import logging

from data.k8s_model.interface import K8sClusterInterface
from data.k8s_model.datatypes import KubernetesClusterAccess as KubernetesClusterAccessDataType
from data.database import KubernetesClusterAccess


logger = logging.getLogger(__name__)


class K8sModelProxy(K8sClusterInterface):
    def configure(self):
        logger.info("===============================")
        logger.info("Using V1 Kubernetes model")
        logger.info("===============================")

        return self

    def register_cluster(self, access_info):
        assert isinstance(access_info, KubernetesClusterAccessDataType)

        KubernetesClusterAccess.create(
            display_name=access_info.display_name,
            auth_token=access_info.auth_token,
            api_endpoint=access_info.api_endpoint,
            console_endpoint=access_info.console_endpoint,
        )
        # TODO(alecmerdler): Verify API connection using credentials

    def deregister_cluster(self, access_uuid):
        assert isinstance(access_uuid, str)

        KubernetesClusterAccess.delete().where(
            KubernetesClusterAccess.uuid == access_uuid
        ).execute()


k8s_model = K8sModelProxy()
