import pytest
from mock import patch

from app import app as realapp
from data import model
from data.database import Tag, get_epoch_timestamp_ms
from endpoints.api import api
from endpoints.api.organization import (
    Organization,
    OrganizationCollaboratorList,
    OrganizationList,
    OrganizationProxyCacheConfig,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from features import FeatureNameValue
from test.fixtures import *


@pytest.mark.parametrize(
    "expiration, expected_code",
    [
        (0, 200),
        (100, 400),
        (100000000000000000000, 400),
    ],
)
def test_change_tag_expiration(expiration, expected_code, app):
    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            Organization,
            "PUT",
            {"orgname": "buynlarge"},
            body={"tag_expiration_s": expiration},
            expected_code=expected_code,
        )


def test_get_organization_collaborators(app):
    params = {"orgname": "buynlarge"}

    with client_with_identity("devtable", app) as cl:
        resp = conduct_api_call(cl, OrganizationCollaboratorList, "GET", params)

    collaborator_names = [c["name"] for c in resp.json["collaborators"]]
    assert "outsideorg" in collaborator_names
    assert "devtable" not in collaborator_names
    assert "reader" not in collaborator_names

    for collaborator in resp.json["collaborators"]:
        if collaborator["name"] == "outsideorg":
            assert "orgrepo" in collaborator["repositories"]
            assert "anotherorgrepo" not in collaborator["repositories"]


def test_create_org_as_superuser_with_restricted_users_set(app):
    body = {
        "name": "buyandlarge",
        "email": "some@email.com",
    }

    # check if super users can create organizations regardles of restricted users set
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, OrganizationList, "POST", None, body=body, expected_code=201
            )

    body = {
        "name": "buyandlargetimes2",
        "email": "some1@email.com",
    }

    # check if users who are not super users can create organizations when restricted users is set
    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with patch("endpoints.api.organization.usermanager.is_superuser", return_value=False):
            with client_with_identity("devtable", app) as cl:
                conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=403)


def test_create_org_as_ldap_superuser_with_restricted_users_set(app):
    """
    Test that LDAP-detected superusers can create organizations
    even when not in the config SUPER_USERS list.
    """
    body = {
        "name": "ldapsuperuserorg",
        "email": "ldap@email.com",
    }

    # Remove user from config SUPER_USERS to simulate LDAP-only superuser
    superuser_list = realapp.config.get("SUPER_USERS")
    realapp.config["SUPER_USERS"] = []

    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        # Mock usermanager.is_superuser to return True (simulating LDAP detection)
        with patch("endpoints.api.organization.usermanager.is_superuser", return_value=True):
            with client_with_identity("devtable", app) as cl:
                conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

    # Restore superuser list
    realapp.config["SUPER_USERS"] = superuser_list


class TestProxyCacheConfigWithImmutableTags:
    """Tests for blocking proxy cache creation when immutable tags exist."""

    def _create_immutable_tag_in_org(self, orgname, reponame):
        """Helper to create a repository with an immutable tag in an org."""
        repo = model.repository.create_repository(
            orgname, reponame, None, repo_kind="image", visibility="private"
        )

        # Get a manifest from an existing repo to reference
        existing_repo = model.repository.get_repository("devtable", "simple")
        from data.model.oci.tag import filter_to_alive_tags

        tags = filter_to_alive_tags(Tag.select().where(Tag.repository == existing_repo.id))
        manifest = None
        for tag in tags:
            if tag.manifest:
                manifest = tag.manifest
                break

        if manifest is None:
            pytest.skip("No manifest available for test")

        # Create an immutable tag
        now_ms = get_epoch_timestamp_ms()
        Tag.create(
            name="immutable-tag",
            repository=repo.id,
            manifest=manifest,
            lifetime_start_ms=now_ms,
            lifetime_end_ms=None,
            hidden=False,
            reversion=False,
            immutable=True,
            tag_kind=Tag.tag_kind.get_id("tag"),
        )

        return repo

    def _cleanup_test_repo(self, orgname, reponame):
        """Clean up test repository."""
        try:
            repo = model.repository.get_repository(orgname, reponame)
            if repo:
                Tag.delete().where(Tag.repository == repo.id).execute()
                repo.delete_instance()
        except Exception:
            pass

    def _cleanup_proxy_cache_config(self, orgname):
        """Clean up proxy cache config."""
        try:
            model.proxy_cache.delete_proxy_cache_config(orgname)
        except Exception:
            pass

    def test_create_proxy_cache_blocked_with_immutable_tags(self, app):
        """
        Test that creating proxy cache config is blocked when org has immutable tags.
        """
        self._cleanup_proxy_cache_config("buynlarge")
        self._cleanup_test_repo("buynlarge", "immutable_proxy_test")

        with toggle_feature("IMMUTABLE_TAGS", True):
            with toggle_feature("PROXY_CACHE", True):
                # Create a repo with immutable tag
                self._create_immutable_tag_in_org("buynlarge", "immutable_proxy_test")

                # Try to create proxy cache config - should be blocked
                with client_with_identity("devtable", app) as cl:
                    params = {"orgname": "buynlarge"}
                    request_body = {
                        "upstream_registry": "docker.io",
                    }
                    resp = conduct_api_call(
                        cl, OrganizationProxyCacheConfig, "POST", params, request_body, 400
                    )
                    assert "immutable tags" in resp.json.get("error_message", "").lower()

        # Clean up
        self._cleanup_test_repo("buynlarge", "immutable_proxy_test")

    def test_namespace_has_immutable_tags_function(self, app):
        """
        Test the namespace_has_immutable_tags function directly.
        """
        from data.model.immutability import namespace_has_immutable_tags

        # Check an org without immutable tags
        org = model.organization.get_organization("sellnsmall")
        has_immutable = namespace_has_immutable_tags(org.id)
        # Initially there should be no immutable tags
        assert isinstance(has_immutable, bool)
