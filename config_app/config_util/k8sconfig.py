import os

SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

DEFAULT_QE_NAMESPACE = "quay-enterprise"
DEFAULT_QE_CONFIG_SECRET = "quay-enterprise-config-secret"

# The name of the quay enterprise deployment (not config app) that is used to query & rollout
DEFAULT_QE_DEPLOYMENT_SELECTOR = "app"


def get_k8s_namespace():
    return os.environ.get("QE_K8S_NAMESPACE", DEFAULT_QE_NAMESPACE)


class KubernetesConfig(object):
    def __init__(
        self,
        api_host="",
        service_account_token=SERVICE_ACCOUNT_TOKEN_PATH,
        qe_namespace=DEFAULT_QE_NAMESPACE,
        qe_config_secret=DEFAULT_QE_CONFIG_SECRET,
        qe_deployment_selector=DEFAULT_QE_DEPLOYMENT_SELECTOR,
    ):
        self.api_host = api_host
        self.qe_namespace = qe_namespace
        self.qe_config_secret = qe_config_secret
        self.qe_deployment_selector = qe_deployment_selector
        self.service_account_token = service_account_token

    @classmethod
    def from_env(cls):
        # Load the service account token from the local store.
        if not os.path.exists(SERVICE_ACCOUNT_TOKEN_PATH):
            raise Exception("Cannot load Kubernetes service account token")

        with open(SERVICE_ACCOUNT_TOKEN_PATH, "r") as f:
            service_token = f.read()

        api_host = os.environ.get("KUBERNETES_SERVICE_HOST", "")
        port = os.environ.get("KUBERNETES_SERVICE_PORT")
        if port:
            api_host += ":" + port

        qe_namespace = get_k8s_namespace()
        qe_config_secret = os.environ.get("QE_K8S_CONFIG_SECRET", DEFAULT_QE_CONFIG_SECRET)
        qe_deployment_selector = os.environ.get(
            "QE_DEPLOYMENT_SELECTOR", DEFAULT_QE_DEPLOYMENT_SELECTOR
        )

        return cls(
            api_host=api_host,
            service_account_token=service_token,
            qe_namespace=qe_namespace,
            qe_config_secret=qe_config_secret,
            qe_deployment_selector=qe_deployment_selector,
        )
