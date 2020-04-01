from collections import namedtuple


KubernetesClusterAccess = namedtuple(
    "KubernetesClusterAccess", ["display_name", "auth_token", "api_endpoint", "console_endpoint"]
)
