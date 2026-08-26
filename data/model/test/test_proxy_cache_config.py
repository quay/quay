from unittest.mock import patch

import pytest
from playhouse.test_utils import assert_query_count

from data.database import DEFAULT_PROXY_CACHE_EXPIRATION
from data.model import (
    DataModelException,
    InvalidOrganizationException,
    InvalidProxyCacheConfigException,
)
from data.model.organization import create_organization
from data.model.proxy_cache import (
    create_proxy_cache_config,
    delete_proxy_cache_config,
    get_proxy_cache_config_for_org,
    has_proxy_cache_config,
)
from data.model.user import create_user_noverify
from test.fixtures import *  # noqa: F401, F403


def create_org(user_name, user_email, org_name, org_email):
    user_obj = create_user_noverify(user_name, user_email)
    return create_organization(org_name, org_email, user_obj)


def test_has_proxy_cache_config_with_proxy_cache_org(initialized_db):
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    create_proxy_cache_config(org.username, "quay.io")
    assert has_proxy_cache_config(org.username)


def test_has_proxy_cache_config_with_regular_org(initialized_db):
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    assert not has_proxy_cache_config(org.username)


def test_create_proxy_cache_config_with_defaults(initialized_db):
    upstream_registry = "quay.io"
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    result = create_proxy_cache_config(org.username, upstream_registry)

    assert result.organization_id == org.id
    assert result.upstream_registry == upstream_registry
    assert result.upstream_registry_hostname == upstream_registry
    assert result.upstream_registry_namespace is None
    assert result.upstream_registry_username is None
    assert result.upstream_registry_password is None
    assert result.expiration_s == DEFAULT_PROXY_CACHE_EXPIRATION
    assert not result.insecure


def test_create_proxy_cache_config_without_defaults(initialized_db):
    upstream_registry = "docker.io/library"
    upstream_registry_username = "admin"
    upstream_registry_password = "password"
    expiration_s = 3600

    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    result = create_proxy_cache_config(
        org.username,
        upstream_registry=upstream_registry,
        upstream_registry_username=upstream_registry_username,
        upstream_registry_password=upstream_registry_password,
        expiration_s=expiration_s,
        insecure=True,
    )

    assert result.organization_id == org.id
    assert result.upstream_registry == upstream_registry
    assert result.upstream_registry_namespace == "library"
    assert result.upstream_registry_hostname == "docker.io"
    assert result.upstream_registry_username == upstream_registry_username
    assert result.upstream_registry_password == upstream_registry_password
    assert result.expiration_s == expiration_s
    assert result.insecure


@pytest.mark.xfail(raises=InvalidOrganizationException)
def test_create_proxy_cache_config_without_org(initialized_db):
    upstream_registry = "docker.io"
    namespace = "non-existing-org"

    create_proxy_cache_config(namespace, upstream_registry)


def test_get_proxy_cache_config_for_org(initialized_db):
    upstream_registry = "docker.io"

    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    create_proxy_cache_config(org.username, upstream_registry)
    result = get_proxy_cache_config_for_org(org.username)

    assert result.organization_id == org.id
    assert result.upstream_registry == upstream_registry
    assert result.upstream_registry_namespace is None
    assert result.upstream_registry_hostname == upstream_registry
    assert result.upstream_registry_username is None
    assert result.upstream_registry_password is None
    assert result.expiration_s == DEFAULT_PROXY_CACHE_EXPIRATION
    assert not result.insecure


@pytest.mark.xfail(raises=InvalidProxyCacheConfigException)
def test_get_proxy_cache_config_for_org_without_proxy_config(initialized_db):
    test_org = "test"
    test_email = "test@example.com"

    user_obj = create_user_noverify(test_org, test_email)
    org = create_organization("foobar", "foo@example.com", user_obj)
    get_proxy_cache_config_for_org(org.username)


@pytest.mark.xfail(raises=InvalidProxyCacheConfigException)
def test_get_proxy_cache_config_for_org_without_org(initialized_db):
    namespace = "non-existing-org"
    get_proxy_cache_config_for_org(namespace)


def test_get_proxy_cache_config_for_org_only_queries_db_once(initialized_db):
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    create_proxy_cache_config(org.username, "docker.io")

    # first call caches the result
    with assert_query_count(1):
        get_proxy_cache_config_for_org(org.username)


def test_delete_proxy_cache_config(initialized_db):
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    create_proxy_cache_config(org.username, "docker.io")
    result = delete_proxy_cache_config(org.username)
    assert result is True


@patch("features.ORG_MIRROR", True)
def test_create_proxy_cache_config_blocked_by_org_mirror(initialized_db):
    """
    Creating proxy cache config should fail when the organization already has
    an org mirror configuration.
    """
    from datetime import datetime

    from data.database import (
        OrgMirrorConfig,
        OrgMirrorStatus,
        SourceRegistryType,
        Visibility,
    )
    from data.model.user import create_robot

    org = create_org(
        user_name="test_mirror_block",
        user_email="test_mirror_block@example.com",
        org_name="mirror_block_org",
        org_email="mirror_block@example.com",
    )
    robot, _ = create_robot("mirrorbot", org)
    visibility = Visibility.get(name="private")

    OrgMirrorConfig.create(
        organization=org,
        is_enabled=True,
        external_registry_type=SourceRegistryType.HARBOR,
        external_registry_url="https://harbor.example.com",
        external_namespace="my-project",
        internal_robot=robot,
        visibility=visibility,
        sync_interval=3600,
        sync_start_date=datetime.utcnow(),
        sync_status=OrgMirrorStatus.NEVER_RUN,
        sync_retries_remaining=3,
        skopeo_timeout=300,
    )

    with pytest.raises(DataModelException) as excinfo:
        create_proxy_cache_config(org.username, "quay.io")

    assert "organization-level mirroring" in str(excinfo.value).lower()


@patch("features.ORG_MIRROR", False)
def test_create_proxy_cache_config_skips_org_mirror_check_when_disabled(initialized_db):
    """
    When features.ORG_MIRROR is disabled, the org mirror check should be skipped
    and proxy cache creation should succeed.
    """
    org = create_org(
        user_name="test_mirror_skip",
        user_email="test_mirror_skip@example.com",
        org_name="mirror_skip_org",
        org_email="mirror_skip@example.com",
    )

    result = create_proxy_cache_config(org.username, "quay.io")

    assert result is not None
    assert result.organization_id == org.id


def test_delete_for_nonexistant_config(initialized_db):
    org = create_org(
        user_name="test",
        user_email="test@example.com",
        org_name="foobar",
        org_email="foo@example.com",
    )
    result = delete_proxy_cache_config(org.username)
    assert result is False
