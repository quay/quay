import pytest

from data.model import vulnerabilitysuppression
from data.registry_model import registry_model
from endpoints.api.manifest import (
    RepositoryManifest,
    RepositoryManifestSuppressedVulnerabilities,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def test_repository_manifest(app):
    with client_with_identity("devtable", app) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tags = registry_model.list_all_active_repository_tags(repo_ref)
        for tag in tags:
            manifest_digest = tag.manifest_digest
            if manifest_digest is None:
                continue

            params = {
                "repository": "devtable/simple",
                "manifestref": manifest_digest,
            }
            result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
            assert result["digest"] == manifest_digest
            assert result["manifest_data"]


def test_repository_manifest_vulnerability_suppression(client):
    with client_with_identity("devtable", client) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.lookup_manifest_by_digest(repo_ref, tag.manifest_digest)

        suppression = vulnerabilitysuppression.create_vulnerability_suppression_for_manifest(
            manifest, ["CVE-2019-1234"]
        )

        assert suppression.vulnerability_names == ["CVE-2019-1234"]

        params = {
            "repository": "devtable/simple",
            "manifestref": manifest.digest,
        }

        # check that we are getting the expected suppressed vulnerabilities
        result = conduct_api_call(
            cl, RepositoryManifestSuppressedVulnerabilities, "GET", params, None, 200
        ).json

        assert result["suppressed_vulnerabilities"] == ["CVE-2019-1234"]

        # check that we can set new suppressed vulnerabilities

        params = {
            "repository": "devtable/simple",
            "manifestref": manifest.digest,
        }

        body = {"suppressed_vulnerabilities": ["CVE-2019-1234", "CVE-2019-5678"]}

        result = conduct_api_call(
            cl, RepositoryManifestSuppressedVulnerabilities, "PUT", params, body, 204
        )

        assert result.status_code == 204
        assert result.data == b""
        assert vulnerabilitysuppression.get_vulnerability_suppression_for_manifest(manifest) == [
            "CVE-2019-1234",
            "CVE-2019-5678",
        ]

        # check that we delete the suppressed vulnerabilities if we set an empty list

        params = {
            "repository": "devtable/simple",
            "manifestref": manifest.digest,
        }

        body = {"suppressed_vulnerabilities": []}

        result = conduct_api_call(
            cl, RepositoryManifestSuppressedVulnerabilities, "PUT", params, body, 204
        )

        assert result.status_code == 204
        assert result.data == b""
        assert vulnerabilitysuppression.get_vulnerability_suppression_for_manifest(manifest) == []


@pytest.mark.parametrize(
    "repo, manifestref",
    [
        (
            "devtable/simple",
            "sha256:1234567890",
        ),
        (
            "devtable/doesntexist",
            "sha256:1234567890",
        ),
    ],
)
def test_repository_manifest_vulnerability_suppression_nonexistent(client, repo, manifestref):
    with client_with_identity("devtable", client) as cl:
        # try to set suppressed vulnerabilities for a manifest that doesn't exist

        params = {
            "repository": repo,
            "manifestref": manifestref,
        }

        body = {"suppressed_vulnerabilities": ["CVE-2019-1234", "CVE-2019-5678"]}

        conduct_api_call(cl, RepositoryManifestSuppressedVulnerabilities, "PUT", params, body, 404)

        # try to get suppressed vulnerabilities for a manifest that doesn't exist

        conduct_api_call(cl, RepositoryManifestSuppressedVulnerabilities, "GET", params, None, 404)


@pytest.mark.parametrize(
    "suppressed_vulns",
    [
        (" CVE-2019-1234 ",),
        (" CVE-2019-1234",),
        ("CVE-2019-1234 ",),
        (" ",),
        ("",),
    ],
)
def test_repository_manifest_vulnerability_suppression_invalid(client, suppressed_vulns):
    with client_with_identity("devtable", client) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tag = registry_model.get_repo_tag(repo_ref, "latest")
        manifest = registry_model.lookup_manifest_by_digest(repo_ref, tag.manifest_digest)

        params = {
            "repository": "devtable/simple",
            "manifestref": manifest.digest,
        }

        body = {"suppressed_vulnerabilities": suppressed_vulns}

        result = conduct_api_call(
            cl, RepositoryManifestSuppressedVulnerabilities, "PUT", params, body, 400
        )

        assert result.status_code == 400
