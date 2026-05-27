import pytest
from mock import patch

from app import app as realapp
from data import model
from data.database import Tag, get_epoch_timestamp_ms
from endpoints.api import api
from endpoints.api.organization import (
    Organization,
    OrganizationApplicationResource,
    OrganizationApplications,
    OrganizationCollaboratorList,
    OrganizationList,
    OrganizationProxyCacheConfig,
    ProxyCacheConfigValidation,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity, toggle_feature
from features import FeatureNameValue
from test.fixtures import *


class TestContactEmail:
    def test_create_org_with_contact_email(self, app):
        body = {
            "name": "contactemailorg",
            "contact_email": "contact@example.com",
        }
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

        org = model.organization.get_organization("contactemailorg")
        assert org.email == "contact@example.com"

    def test_create_org_without_email(self, app):
        body = {"name": "noemailorg"}
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

        org = model.organization.get_organization("noemailorg")
        from util.validation import validate_email

        assert not validate_email(org.email)

    def test_create_org_email_backward_compat(self, app):
        body = {
            "name": "backcompatorg",
            "email": "compat@example.com",
        }
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

        org = model.organization.get_organization("backcompatorg")
        assert org.email == "compat@example.com"

    def test_update_org_contact_email(self, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": "updated@example.com"},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        assert org.email == "updated@example.com"

    def test_update_org_duplicate_contact_email(self, app):
        body = {
            "name": "dupemailorg",
            "contact_email": "shared@example.com",
        }
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": "shared@example.com"},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        assert org.email == "shared@example.com"

    def test_get_org_admin_sees_email(self, app):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, Organization, "GET", {"orgname": "buynlarge"}, expected_code=200
            )
        assert "email" in resp.json

    def test_get_org_nonadmin_no_email(self, app):
        with client_with_identity("freshuser", app) as cl:
            resp = conduct_api_call(
                cl, Organization, "GET", {"orgname": "buynlarge"}, expected_code=200
            )
        assert resp.json.get("email") == ""

    def test_clear_contact_email(self, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": "temp@example.com"},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        assert org.email == "temp@example.com"

        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": ""},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        from util.validation import validate_email

        assert not validate_email(org.email)

    def test_clear_contact_email_with_null(self, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": "temp@example.com"},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        assert org.email == "temp@example.com"

        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": None},
                expected_code=200,
            )

        org = model.organization.get_organization("buynlarge")
        from util.validation import validate_email

        assert not validate_email(org.email)

    def test_create_org_no_email_with_mailing(self, app):
        body = {"name": "mailingnoemailorg"}
        with toggle_feature("MAILING", True):
            with client_with_identity("devtable", app) as cl:
                conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=201)

        org = model.organization.get_organization("mailingnoemailorg")
        from util.validation import validate_email

        assert not validate_email(org.email)

    def test_create_org_invalid_contact_email(self, app):
        body = {
            "name": "invalemailorg",
            "contact_email": "not-a-valid-email",
        }
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(cl, OrganizationList, "POST", None, body=body, expected_code=400)

    def test_update_org_invalid_contact_email(self, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                Organization,
                "PUT",
                {"orgname": "buynlarge"},
                body={"contact_email": "not-a-valid-email"},
                expected_code=400,
            )


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


@pytest.mark.parametrize(
    "is_superuser, is_restricted, expected_code",
    [
        # LDAP superuser + not restricted by LDAP -> allowed
        (True, False, 201),
        # LDAP superuser + restricted by LDAP -> allowed (superuser bypass)
        (True, True, 201),
        # Non-superuser + restricted -> forbidden
        (False, True, 403),
    ],
)
def test_create_org_ldap_restricted_user_no_whitelist(
    is_superuser, is_restricted, expected_code, app
):
    """
    Test org creation when FEATURE_RESTRICTED_USERS is enabled without
    RESTRICTED_USERS_WHITELIST (the LDAP-only restricted user path).
    Verifies LDAP superusers not matched by LDAP_RESTRICTED_USER_FILTER
    are not incorrectly blocked.
    """
    suffix = f"{str(is_superuser).lower()}{str(is_restricted).lower()}"
    body = {
        "name": f"ldaprestrictedorg{suffix}",
        "email": f"ldap{suffix}@email.com",
    }

    with patch("features.RESTRICTED_USERS", FeatureNameValue("RESTRICTED_USERS", True)):
        with patch(
            "endpoints.api.organization.usermanager.is_superuser",
            return_value=is_superuser,
        ):
            with patch(
                "endpoints.api.organization.usermanager.is_restricted_user",
                return_value=is_restricted,
            ):
                with client_with_identity("devtable", app) as cl:
                    conduct_api_call(
                        cl, OrganizationList, "POST", None, body=body, expected_code=expected_code
                    )


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

    def test_create_proxy_cache_blocked_when_org_mirrored(self, app):
        """
        Test that creating proxy cache config is blocked when org has org mirror enabled.
        """
        from data.database import OrgMirrorConfig as OrgMirrorConfigTable
        from data.database import OrgMirrorStatus, SourceRegistryType, Visibility

        self._cleanup_proxy_cache_config("buynlarge")

        org = model.organization.get_organization("buynlarge")
        robot = model.user.lookup_robot("buynlarge+coolrobot")

        # Create org mirror config directly at DB level
        mirror = OrgMirrorConfigTable.create(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=Visibility.get(name="private"),
            sync_interval=3600,
            sync_start_date="2025-01-01T00:00:00",
            is_enabled=True,
            sync_status=OrgMirrorStatus.NEVER_RUN,
            skopeo_timeout=300,
        )

        try:
            with toggle_feature("ORG_MIRROR", True):
                with toggle_feature("PROXY_CACHE", True):
                    with client_with_identity("devtable", app) as cl:
                        params = {"orgname": "buynlarge"}
                        request_body = {
                            "upstream_registry": "docker.io",
                        }
                        resp = conduct_api_call(
                            cl, OrganizationProxyCacheConfig, "POST", params, request_body, 400
                        )
                        assert "organization-level mirroring" in resp.json.get("error_message", "")
        finally:
            mirror.delete_instance()

    def test_create_proxy_cache_success(self, app):
        """
        Test that proxy cache creation succeeds on a clean org (regression test
        for the missing org_name argument fix).
        """
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                request_body = {
                    "upstream_registry": "docker.io",
                }
                conduct_api_call(
                    cl, OrganizationProxyCacheConfig, "POST", params, request_body, 201
                )

        # Clean up
        self._cleanup_proxy_cache_config("buynlarge")

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


def test_create_application_rejects_reserved_bootstrap_name(app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrganizationApplications,
            "POST",
            {"orgname": "buynlarge"},
            {"name": model.oauth.BOOTSTRAP_APP_NAME},
            400,
        )

    assert "reserved" in response.json["error_message"]


def test_create_application_allows_non_reserved_bootstrap_like_name(app):
    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrganizationApplications,
            "POST",
            {"orgname": "buynlarge"},
            {"name": "custom-bootstrap-api"},
        )

    assert response.json["name"] == "custom-bootstrap-api"


def test_update_application_rejects_reserved_bootstrap_name(app):
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "legit-bootstrap-api-test", "", "")

    with client_with_identity("devtable", app) as cl:
        response = conduct_api_call(
            cl,
            OrganizationApplicationResource,
            "PUT",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {
                "name": model.oauth.BOOTSTRAP_APP_NAME,
                "redirect_uri": "",
                "application_uri": "",
            },
            400,
        )

    application = model.oauth.lookup_application(org, application.client_id)
    assert "reserved" in response.json["error_message"]
    assert application.name == "legit-bootstrap-api-test"


def test_update_application_allows_non_reserved_bootstrap_like_name(app):
    org = model.organization.get_organization("buynlarge")
    application = model.oauth.create_application(org, "legit-custom-bootstrap-api-test", "", "")

    with client_with_identity("devtable", app) as cl:
        conduct_api_call(
            cl,
            OrganizationApplicationResource,
            "PUT",
            {"orgname": "buynlarge", "client_id": application.client_id},
            {
                "name": "custom-bootstrap-api",
                "redirect_uri": "",
                "application_uri": "",
            },
        )

    application = model.oauth.lookup_application(org, application.client_id)
    assert application.name == "custom-bootstrap-api"



@pytest.fixture()
def _mock_dns_for_ssrf_validation():
    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        yield mock_dns


@pytest.mark.usefixtures("_mock_dns_for_ssrf_validation")
class TestProxyCacheSSRFProtection:
    """Tests for SSRF protection in proxy cache configuration endpoints (CVE-2026-32591)."""

    def _cleanup_proxy_cache_config(self, orgname):
        try:
            model.proxy_cache.delete_proxy_cache_config(orgname)
        except Exception:
            pass

    def test_create_with_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_loopback_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "127.0.0.1"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_aws_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "169.254.169.254"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_kubernetes_hostname_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "kubernetes.default.svc"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_gcp_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "metadata.google.internal"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_valid_registry_succeeds(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "docker.io"}
                conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 201)

        self._cleanup_proxy_cache_config("buynlarge")

    def test_validate_with_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_validate_with_aws_metadata_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "169.254.169.254"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_validate_with_localhost_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "localhost"}
                resp = conduct_api_call(cl, ProxyCacheConfigValidation, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")

    def test_create_with_upstream_namespace_and_private_ip_rejected(self, app):
        self._cleanup_proxy_cache_config("buynlarge")

        with toggle_feature("PROXY_CACHE", True):
            with client_with_identity("devtable", app) as cl:
                params = {"orgname": "buynlarge"}
                body = {"upstream_registry": "10.0.0.1/myorg"}
                resp = conduct_api_call(cl, OrganizationProxyCacheConfig, "POST", params, body, 400)
                assert "not allowed" in resp.json.get("error_message", "")
