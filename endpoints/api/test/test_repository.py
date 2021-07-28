import pytest

from mock import patch, ANY, MagicMock

from data import model, database
from data.appr_model import release, channel, blob
from endpoints.appr.models_cnr import model as appr_model
from endpoints.api.test.shared import conduct_api_call
from endpoints.api.repository import RepositoryTrust, Repository, RepositoryList
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue

from test.fixtures import *


@pytest.mark.parametrize(
    "trust_enabled,repo_found,expected_status",
    [
        (True, True, 200),
        (False, True, 200),
        (False, False, 404),
        ("invalid_req", False, 400),
    ],
)
def test_post_changetrust(trust_enabled, repo_found, expected_status, client):
    with patch("endpoints.api.repository.tuf_metadata_api") as mock_tuf:
        with patch(
            "endpoints.api.repository_models_pre_oci.model.repository.get_repository"
        ) as mock_model:
            mock_model.return_value = MagicMock() if repo_found else None
            mock_tuf.get_default_tags_with_expiration.return_value = ["tags", "expiration"]
            with client_with_identity("devtable", client) as cl:
                params = {"repository": "devtable/repo"}
                request_body = {"trust_enabled": trust_enabled}
                conduct_api_call(cl, RepositoryTrust, "POST", params, request_body, expected_status)


def test_signing_disabled(client):
    with patch("features.SIGNING", FeatureNameValue("SIGNING", False)):
        with client_with_identity("devtable", client) as cl:
            params = {"repository": "devtable/simple"}
            response = conduct_api_call(cl, Repository, "GET", params).json
            assert not response["trust_enabled"]


def test_list_starred_repos(client):
    with client_with_identity("devtable", client) as cl:
        params = {
            "starred": "true",
        }

        response = conduct_api_call(cl, RepositoryList, "GET", params).json
        repos = {r["namespace"] + "/" + r["name"] for r in response["repositories"]}
        assert "devtable/simple" in repos
        assert "public/publicrepo" not in repos

        # Add a star on publicrepo.
        publicrepo = model.repository.get_repository("public", "publicrepo")
        model.repository.star_repository(model.user.get_user("devtable"), publicrepo)

        # Ensure publicrepo shows up.
        response = conduct_api_call(cl, RepositoryList, "GET", params).json
        repos = {r["namespace"] + "/" + r["name"] for r in response["repositories"]}
        assert "devtable/simple" in repos
        assert "public/publicrepo" in repos

        # Make publicrepo private and ensure it disappears.
        model.repository.set_repository_visibility(publicrepo, "private")

        response = conduct_api_call(cl, RepositoryList, "GET", params).json
        repos = {r["namespace"] + "/" + r["name"] for r in response["repositories"]}
        assert "devtable/simple" in repos
        assert "public/publicrepo" not in repos


def test_list_repos(client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        params = {"starred": "true", "repo_kind": "application"}
        response = conduct_api_call(cl, RepositoryList, "GET", params).json
        repo_states = {r["state"] for r in response["repositories"]}
        for state in repo_states:
            assert state in ["NORMAL", "MIRROR", "READ_ONLY", "MARKED_FOR_DELETION"]


def test_list_starred_app_repos(client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        params = {"starred": "true", "repo_kind": "application"}

        devtable = model.user.get_user("devtable")
        repo = model.repository.create_repository(
            "devtable", "someappr", devtable, repo_kind="application"
        )
        model.repository.star_repository(model.user.get_user("devtable"), repo)

        response = conduct_api_call(cl, RepositoryList, "GET", params).json
        repos = {r["namespace"] + "/" + r["name"] for r in response["repositories"]}
        assert "devtable/someappr" in repos


def test_list_repositories_last_modified(client):
    with client_with_identity("devtable", client) as cl:
        params = {
            "namespace": "devtable",
            "last_modified": "true",
        }

        response = conduct_api_call(cl, RepositoryList, "GET", params).json

        for repo in response["repositories"]:
            if repo["name"] != "building":
                assert repo["last_modified"] is not None


def test_list_app_repositories_last_modified(client):
    with client_with_identity("devtable", client) as cl:
        devtable = model.user.get_user("devtable")
        repo = model.repository.create_repository(
            "devtable", "someappr", devtable, repo_kind="application"
        )

        models_ref = appr_model.models_ref
        blob.get_or_create_blob(
            "sha256:somedigest", 0, "application/vnd.cnr.blob.v0.tar+gzip", ["local_us"], models_ref
        )

        release.create_app_release(
            repo,
            "test",
            dict(mediaType="application/vnd.cnr.package-manifest.helm.v0.json"),
            "sha256:somedigest",
            models_ref,
            False,
        )

        channel.create_or_update_channel(repo, "somechannel", "test", models_ref)

        params = {
            "namespace": "devtable",
            "last_modified": "true",
            "repo_kind": "application",
        }
        response = conduct_api_call(cl, RepositoryList, "GET", params).json

        assert len(response["repositories"]) > 0
        for repo in response["repositories"]:
            assert repo["last_modified"] is not None


@pytest.mark.parametrize(
    "repo_name, extended_repo_names, expected_status",
    [
        pytest.param("x" * 255, False, 201, id="Maximum allowed length"),
        pytest.param("x" * 255, True, 201, id="Maximum allowed length"),
        pytest.param("x" * 256, False, 400, id="Over allowed length"),
        pytest.param("x" * 256, True, 400, id="Over allowed length"),
        pytest.param("a|b", False, 400, id="Invalid name"),
        pytest.param("a|b", True, 400, id="Invalid name"),
        pytest.param("UpperCase", False, 400, id="Uppercase Not Allowed"),
        pytest.param("UpperCase", True, 400, id="Uppercase Not Allowed"),
        pytest.param("testrepo/nested", False, 400, id="Slashes Not Allowed"),
        pytest.param("testrepo/nested", True, 201, id="Slashes Allowed"),
        pytest.param("testrepo/" + "x" * 247, True, 400, id="Slashes Allowed But Too Long"),
        pytest.param("devtable/" + "x" * 246, True, 201, id="Slashes Allowed Max Allowed"),
        pytest.param("devtable/nested1/nested2", False, 400, id="Slashes Allowed Multiple Levels"),
        pytest.param("devtable/nested1/nested2", True, 201, id="Slashes Allowed Multiple Levels"),
    ],
)
def test_create_repository(repo_name, extended_repo_names, expected_status, client):
    with patch(
        "features.EXTENDED_REPOSITORY_NAMES",
        FeatureNameValue("EXTENDED_REPOSITORY_NAMES", extended_repo_names),
    ):
        with client_with_identity("devtable", client) as cl:
            body = {
                "namespace": "devtable",
                "repository": repo_name,
                "visibility": "public",
                "description": "foo",
            }

            result = conduct_api_call(
                client, RepositoryList, "post", None, body, expected_code=expected_status
            ).json
            if expected_status == 201:
                assert result["name"] == repo_name
                assert model.repository.get_repository("devtable", repo_name).name == repo_name


@pytest.mark.parametrize(
    "has_tag_manifest",
    [
        True,
        False,
    ],
)
def test_get_repo(has_tag_manifest, client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        if not has_tag_manifest:
            database.TagManifestLabelMap.delete().execute()
            database.TagManifestToManifest.delete().execute()
            database.TagManifestLabel.delete().execute()
            database.TagManifest.delete().execute()

        params = {"repository": "devtable/simple"}
        response = conduct_api_call(cl, Repository, "GET", params).json
        assert response["kind"] == "image"
        assert response["state"] in ["NORMAL", "MIRROR", "READ_ONLY", "MARKED_FOR_DELETION"]


def test_get_app_repo(client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        devtable = model.user.get_user("devtable")
        repo = model.repository.create_repository(
            "devtable", "someappr", devtable, repo_kind="application"
        )

        models_ref = appr_model.models_ref
        blob.get_or_create_blob(
            "sha256:somedigest", 0, "application/vnd.cnr.blob.v0.tar+gzip", ["local_us"], models_ref
        )

        release.create_app_release(
            repo,
            "test",
            dict(mediaType="application/vnd.cnr.package-manifest.helm.v0.json"),
            "sha256:somedigest",
            models_ref,
            False,
        )

        channel.create_or_update_channel(repo, "somechannel", "test", models_ref)

        params = {"repository": "devtable/someappr"}
        response = conduct_api_call(cl, Repository, "GET", params).json
        assert response["kind"] == "application"
        assert response["channels"]
        assert response["releases"]


@pytest.mark.parametrize(
    "state, can_write",
    [
        (database.RepositoryState.NORMAL, True),
        (database.RepositoryState.READ_ONLY, False),
        (database.RepositoryState.MIRROR, False),
    ],
)
def test_get_repo_state_can_write(state, can_write, client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        response = conduct_api_call(cl, Repository, "GET", params).json
        assert response["can_write"]

    repo = model.repository.get_repository("devtable", "simple")
    repo.state = state
    repo.save()

    with client_with_identity("devtable", client) as cl:
        params = {"repository": "devtable/simple"}
        response = conduct_api_call(cl, Repository, "GET", params).json
        assert response["can_write"] == can_write


def test_delete_repo(client, initialized_db):
    with client_with_identity("devtable", client) as cl:
        resp = conduct_api_call(cl, RepositoryList, "GET", {"namespace": "devtable"}).json
        repos = {repo["name"] for repo in resp["repositories"]}
        assert "simple" in repos

        # Delete the repository.
        params = {"repository": "devtable/simple"}
        conduct_api_call(cl, Repository, "DELETE", params, expected_code=204)

        # Ensure it isn't visible anymore.
        conduct_api_call(cl, Repository, "GET", params, expected_code=404)

        resp = conduct_api_call(cl, RepositoryList, "GET", {"namespace": "devtable"}).json
        repos = {repo["name"] for repo in resp["repositories"]}
        assert "simple" not in repos

        # Check that the repository is enqueued for deletion.
        marker = database.DeletedRepository.get()
        assert marker.original_name == "simple"
        assert marker.queue_id
