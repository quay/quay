import pytest

from httmock import urlmatch, HTTMock, response

from config_app.config_util.k8saccessor import (
    KubernetesAccessorSingleton,
    _deployment_rollout_status_message,
)
from config_app.config_util.k8sconfig import KubernetesConfig


@pytest.mark.parametrize(
    "deployment_object, expected_status, expected_message",
    [
        (
            {
                "metadata": {"generation": 1},
                "status": {"observedGeneration": 0, "conditions": []},
                "spec": {"replicas": 0},
            },
            "progressing",
            "Waiting for deployment spec to be updated...",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {
                    "observedGeneration": 0,
                    "conditions": [{"type": "Progressing", "reason": "ProgressDeadlineExceeded"}],
                },
                "spec": {"replicas": 0},
            },
            "failed",
            "Deployment my-deployment's rollout failed. Please try again later.",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {"observedGeneration": 0, "conditions": []},
                "spec": {"replicas": 0},
            },
            "available",
            "Deployment my-deployment updated (no replicas, so nothing to roll out)",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {"observedGeneration": 0, "conditions": [], "replicas": 1},
                "spec": {"replicas": 2},
            },
            "progressing",
            "Waiting for rollout to finish: 0 out of 2 new replicas have been updated...",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {
                    "observedGeneration": 0,
                    "conditions": [],
                    "replicas": 1,
                    "updatedReplicas": 1,
                },
                "spec": {"replicas": 2},
            },
            "progressing",
            "Waiting for rollout to finish: 1 out of 2 new replicas have been updated...",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {
                    "observedGeneration": 0,
                    "conditions": [],
                    "replicas": 2,
                    "updatedReplicas": 1,
                },
                "spec": {"replicas": 1},
            },
            "progressing",
            "Waiting for rollout to finish: 1 old replicas are pending termination...",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {
                    "observedGeneration": 0,
                    "conditions": [],
                    "replicas": 1,
                    "updatedReplicas": 2,
                    "availableReplicas": 0,
                },
                "spec": {"replicas": 0},
            },
            "progressing",
            "Waiting for rollout to finish: 0 of 2 updated replicas are available...",
        ),
        (
            {
                "metadata": {"generation": 0},
                "status": {
                    "observedGeneration": 0,
                    "conditions": [],
                    "replicas": 1,
                    "updatedReplicas": 2,
                    "availableReplicas": 2,
                },
                "spec": {"replicas": 0},
            },
            "available",
            "Deployment my-deployment successfully rolled out.",
        ),
    ],
)
def test_deployment_rollout_status_message(deployment_object, expected_status, expected_message):
    deployment_status = _deployment_rollout_status_message(deployment_object, "my-deployment")
    assert deployment_status.status == expected_status
    assert deployment_status.message == expected_message


@pytest.mark.parametrize(
    "kube_config, expected_api, expected_query",
    [
        (
            {"api_host": "www.customhost.com"},
            "/apis/extensions/v1beta1/namespaces/quay-enterprise/deployments",
            "labelSelector=quay-enterprise-component%3Dapp",
        ),
        (
            {"api_host": "www.customhost.com", "qe_deployment_selector": "custom-selector"},
            "/apis/extensions/v1beta1/namespaces/quay-enterprise/deployments",
            "labelSelector=quay-enterprise-component%3Dcustom-selector",
        ),
        (
            {"api_host": "www.customhost.com", "qe_namespace": "custom-namespace"},
            "/apis/extensions/v1beta1/namespaces/custom-namespace/deployments",
            "labelSelector=quay-enterprise-component%3Dapp",
        ),
        (
            {
                "api_host": "www.customhost.com",
                "qe_namespace": "custom-namespace",
                "qe_deployment_selector": "custom-selector",
            },
            "/apis/extensions/v1beta1/namespaces/custom-namespace/deployments",
            "labelSelector=quay-enterprise-component%3Dcustom-selector",
        ),
    ],
)
def test_get_qe_deployments(kube_config, expected_api, expected_query):
    config = KubernetesConfig(**kube_config)
    url_hit = [False]

    @urlmatch(netloc=r"www.customhost.com")
    def handler(request, _):
        assert request.path == expected_api
        assert request.query == expected_query
        url_hit[0] = True
        return response(200, "{}")

    with HTTMock(handler):
        KubernetesAccessorSingleton._instance = None
        assert KubernetesAccessorSingleton.get_instance(config).get_qe_deployments() is not None

    assert url_hit[0]


@pytest.mark.parametrize(
    "kube_config, deployment_names, expected_api_hits",
    [
        ({"api_host": "www.customhost.com"}, [], []),
        (
            {"api_host": "www.customhost.com"},
            ["myDeployment"],
            ["/apis/extensions/v1beta1/namespaces/quay-enterprise/deployments/myDeployment"],
        ),
        (
            {"api_host": "www.customhost.com", "qe_namespace": "custom-namespace"},
            ["myDeployment", "otherDeployment"],
            [
                "/apis/extensions/v1beta1/namespaces/custom-namespace/deployments/myDeployment",
                "/apis/extensions/v1beta1/namespaces/custom-namespace/deployments/otherDeployment",
            ],
        ),
    ],
)
def test_cycle_qe_deployments(kube_config, deployment_names, expected_api_hits):
    KubernetesAccessorSingleton._instance = None

    config = KubernetesConfig(**kube_config)
    url_hit = [False] * len(expected_api_hits)
    i = [0]

    @urlmatch(netloc=r"www.customhost.com", method="PATCH")
    def handler(request, _):
        assert request.path == expected_api_hits[i[0]]
        url_hit[i[0]] = True
        i[0] += 1
        return response(200, "{}")

    with HTTMock(handler):
        KubernetesAccessorSingleton.get_instance(config).cycle_qe_deployments(deployment_names)

    assert all(url_hit)
