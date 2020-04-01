import pytest

from data.k8s_model import k8s_model
from data.k8s_model.datatypes import KubernetesClusterAccess

from test.fixtures import *


registered_clusters = [
    KubernetesClusterAccess("MyCluster", "", "", None),
]


@pytest.mark.parametrize(
    "access_info",
    [
        (
            {
                "display_name": "MyCluster",
                "auth_token": "",
                "api_endpoint": "",
                "console_endpoint": None,
            }
        ),
    ],
)
def test_register_cluster(access_info, initialized_db):
    for access in registered_clusters:
        k8s_model.register_cluster(access)

    k8s_model.register_cluster(KubernetesClusterAccess(**access_info))


@pytest.mark.parametrize("access_uuid", [(""),])
def test_deregister_cluster(access_uuid, initialized_db):
    for access in registered_clusters:
        k8s_model.register_cluster(access)

    k8s_model.deregister_cluster(access_uuid)
