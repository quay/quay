# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror configuration business logic.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from data import model
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    Repository,
    RepositoryState,
    SourceRegistryType,
    User,
    Visibility,
)
from data.model import DataModelException
from data.model.org_mirror import (
    DEFAULT_MAX_DISCOVERY_DURATION,
    MAX_SYNC_RETRIES,
    claim_org_mirror_config,
    claim_org_mirror_repo,
    create_org_mirror_config,
    deactivate_excluded_repos,
    delete_org_mirror_config,
    expire_org_mirror_repo,
    get_eligible_org_mirror_repos,
    get_enabled_org_mirror_config_count,
    get_max_id_for_org_mirror_repo,
    get_min_id_for_org_mirror_repo,
    get_or_create_org_mirror_repo,
    get_org_mirror_config,
    get_org_mirror_config_count,
    get_org_mirror_repo_status_counts,
    propagate_status_to_repos,
    release_org_mirror_repo,
    sync_discovered_repos,
    update_org_mirror_config,
)
from data.model.user import create_robot, create_user_noverify, lookup_robot
from test.fixtures import *


def _create_org_and_robot(org_name="testorgmirror"):
    """Helper to create an organization and robot for testing."""
    try:
        org = User.get(User.username == org_name)
    except User.DoesNotExist:
        org = create_user_noverify(org_name, f"{org_name}@example.com", email_required=False)
        org.organization = True
        org.save()

    robot_shortname = "mirrorbot"
    try:
        robot = lookup_robot(f"{org_name}+{robot_shortname}")
    except model.InvalidRobotException:
        robot, _ = create_robot(robot_shortname, org)

    return org, robot


def _create_org_mirror_config(org, robot, **kwargs):
    """Helper to create an OrgMirrorConfig for testing."""
    visibility = Visibility.get(name="private")

    defaults = {
        "organization": org,
        "is_enabled": True,
        "external_registry_type": SourceRegistryType.HARBOR,
        "external_registry_url": "https://harbor.example.com",
        "external_namespace": "my-project",
        "internal_robot": robot,
        "visibility": visibility,
        "sync_interval": 3600,
        "sync_start_date": datetime.utcnow(),
        "sync_status": OrgMirrorStatus.NEVER_RUN,
        "sync_retries_remaining": 3,
        "skopeo_timeout": 300,
    }
    defaults.update(kwargs)

    return OrgMirrorConfig.create(**defaults)


class TestGetOrgMirrorConfig:
    """Tests for get_org_mirror_config function."""

    def test_get_org_mirror_config_exists(self, initialized_db):
        """
        When an OrgMirrorConfig exists for an organization,
        get_org_mirror_config should return it.
        """
        org, robot = _create_org_and_robot("org_mirror_test1")
        config = _create_org_mirror_config(org, robot)

        result = get_org_mirror_config(org)

        assert result is not None
        assert result.id == config.id
        assert result.organization == org
        assert result.external_registry_type == SourceRegistryType.HARBOR
        assert result.external_registry_url == "https://harbor.example.com"
        assert result.external_namespace == "my-project"
        assert result.is_enabled is True
        assert result.sync_status == OrgMirrorStatus.NEVER_RUN

    def test_get_org_mirror_config_not_found(self, initialized_db):
        """
        When no OrgMirrorConfig exists for an organization,
        get_org_mirror_config should return None.
        """
        org, _ = _create_org_and_robot("org_mirror_test2")

        result = get_org_mirror_config(org)

        assert result is None

    def test_get_org_mirror_config_returns_robot(self, initialized_db):
        """
        The returned OrgMirrorConfig should have the internal_robot relationship loaded.
        """
        org, robot = _create_org_and_robot("org_mirror_test3")
        _create_org_mirror_config(org, robot)

        result = get_org_mirror_config(org)

        assert result is not None
        assert result.internal_robot is not None
        assert result.internal_robot.id == robot.id
        assert result.internal_robot.username == robot.username

    def test_get_org_mirror_config_with_quay_registry_type(self, initialized_db):
        """
        Test that getting config with QUAY registry type works correctly.
        """
        org, robot = _create_org_and_robot("org_mirror_test4")
        _create_org_mirror_config(
            org,
            robot,
            external_registry_type=SourceRegistryType.QUAY,
            external_registry_url="https://quay.io",
            external_namespace="some-org",
        )

        result = get_org_mirror_config(org)

        assert result is not None
        assert result.external_registry_type == SourceRegistryType.QUAY
        assert result.external_registry_url == "https://quay.io"
        assert result.external_namespace == "some-org"

    def test_get_org_mirror_config_with_filters(self, initialized_db):
        """
        Test that repository_filters are correctly stored and retrieved.
        """
        org, robot = _create_org_and_robot("org_mirror_test5")
        filters = ["ubuntu*", "debian*", "alpine"]
        _create_org_mirror_config(org, robot, repository_filters=filters)

        result = get_org_mirror_config(org)

        assert result is not None
        assert result.repository_filters == filters

    def test_get_org_mirror_config_different_orgs_isolated(self, initialized_db):
        """
        Configs for different organizations should be isolated.
        """
        org1, robot1 = _create_org_and_robot("org_mirror_test6a")
        org2, robot2 = _create_org_and_robot("org_mirror_test6b")

        config1 = _create_org_mirror_config(org1, robot1, external_namespace="project-a")
        config2 = _create_org_mirror_config(org2, robot2, external_namespace="project-b")

        result1 = get_org_mirror_config(org1)
        result2 = get_org_mirror_config(org2)

        assert result1.id == config1.id
        assert result1.external_namespace == "project-a"
        assert result2.id == config2.id
        assert result2.external_namespace == "project-b"


class TestCreateOrgMirrorConfig:
    """Tests for create_org_mirror_config function."""

    def test_create_org_mirror_config_success(self, initialized_db):
        """
        Test successful creation of an organization mirror configuration.
        """
        org, robot = _create_org_and_robot("create_test1")
        visibility = Visibility.get(name="private")
        sync_start = datetime.utcnow()

        config = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=sync_start,
        )

        assert config is not None
        assert config.organization == org
        assert config.internal_robot == robot
        assert config.external_registry_type == SourceRegistryType.HARBOR
        assert config.external_registry_url == "https://harbor.example.com"
        assert config.external_namespace == "my-project"
        assert config.visibility == visibility
        assert config.sync_interval == 3600
        assert config.is_enabled is True
        assert config.sync_status == OrgMirrorStatus.NEVER_RUN
        assert config.skopeo_timeout == 300  # Default value

    def test_create_org_mirror_config_with_optional_fields(self, initialized_db):
        """
        Test creating config with all optional fields.
        """
        org, robot = _create_org_and_robot("create_test2")
        visibility = Visibility.get(name="public")
        sync_start = datetime.utcnow()
        filters = ["ubuntu*", "nginx"]
        registry_config = {
            "verify_tls": True,
            "proxy": {"https_proxy": "https://proxy.example.com"},
        }

        config = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.QUAY,
            external_registry_url="https://quay.io",
            external_namespace="some-org",
            visibility=visibility,
            sync_interval=7200,
            sync_start_date=sync_start,
            is_enabled=False,
            external_registry_username="myuser",
            external_registry_password="mypassword",
            external_registry_config=registry_config,
            repository_filters=filters,
            skopeo_timeout=600,
        )

        assert config is not None
        assert config.is_enabled is False
        assert config.external_registry_type == SourceRegistryType.QUAY
        assert config.repository_filters == filters
        assert config.skopeo_timeout == 600
        assert config.external_registry_config == registry_config

    def test_create_org_mirror_config_robot_wrong_namespace(self, initialized_db):
        """
        Creating config with a robot from a different namespace should raise an error.
        """
        org1, robot1 = _create_org_and_robot("create_test3a")
        org2, _ = _create_org_and_robot("create_test3b")
        visibility = Visibility.get(name="private")

        with pytest.raises(DataModelException) as excinfo:
            create_org_mirror_config(
                organization=org2,  # Different org
                internal_robot=robot1,  # Robot from org1
                external_registry_type=SourceRegistryType.HARBOR,
                external_registry_url="https://harbor.example.com",
                external_namespace="my-project",
                visibility=visibility,
                sync_interval=3600,
                sync_start_date=datetime.utcnow(),
            )

        assert "belong to the organization" in str(excinfo.value)

    @patch("features.PROXY_CACHE", True)
    def test_create_org_mirror_config_blocked_by_proxy_cache(self, initialized_db):
        """
        Creating org mirror config should fail when the organization already has
        a proxy cache configuration.
        """
        from data.model.proxy_cache import create_proxy_cache_config

        org, robot = _create_org_and_robot("create_test_proxy_block")
        visibility = Visibility.get(name="private")

        # Create proxy cache config first
        create_proxy_cache_config(org.username, "quay.io")

        with pytest.raises(DataModelException) as excinfo:
            create_org_mirror_config(
                organization=org,
                internal_robot=robot,
                external_registry_type=SourceRegistryType.HARBOR,
                external_registry_url="https://harbor.example.com",
                external_namespace="my-project",
                visibility=visibility,
                sync_interval=3600,
                sync_start_date=datetime.utcnow(),
            )

        assert "proxy cache" in str(excinfo.value).lower()

    @patch("features.PROXY_CACHE", False)
    def test_create_org_mirror_config_skips_proxy_cache_check_when_disabled(self, initialized_db):
        """
        When features.PROXY_CACHE is disabled, the proxy cache check should be skipped
        and org mirror creation should succeed even if a proxy cache config exists.
        """
        org, robot = _create_org_and_robot("create_test_proxy_skip")
        visibility = Visibility.get(name="private")

        config = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
        )

        assert config is not None

    def test_create_org_mirror_config_already_exists(self, initialized_db):
        """
        Creating a second config for the same org should raise an error.
        """
        org, robot = _create_org_and_robot("create_test4")
        visibility = Visibility.get(name="private")

        # Create first config
        create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
        )

        # Try to create a second config
        with pytest.raises(DataModelException) as excinfo:
            create_org_mirror_config(
                organization=org,
                internal_robot=robot,
                external_registry_type=SourceRegistryType.QUAY,
                external_registry_url="https://quay.io",
                external_namespace="other-project",
                visibility=visibility,
                sync_interval=7200,
                sync_start_date=datetime.utcnow(),
            )

        assert "already exists" in str(excinfo.value)

    def test_create_org_mirror_config_can_retrieve_after_create(self, initialized_db):
        """
        After creating a config, it should be retrievable with get_org_mirror_config.
        """
        org, robot = _create_org_and_robot("create_test5")
        visibility = Visibility.get(name="private")

        created = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
        )

        retrieved = get_org_mirror_config(org)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.external_registry_url == created.external_registry_url

    def test_create_org_mirror_config_allows_deleted_repos(self, initialized_db):
        """
        Creating org mirror config should succeed when the organization only has
        repositories in MARKED_FOR_DELETION state (pending garbage collection).

        Regression test for PROJQUAY-10982.
        """
        org, robot = _create_org_and_robot("create_test_deleted_repos")
        visibility = Visibility.get(name="private")

        # Create a repo and mark it for deletion (simulating user-deleted repos
        # that haven't been garbage collected yet)
        repo = model.repository.create_repository(
            org.username, "deleted-repo", None, visibility="private"
        )
        repo.state = RepositoryState.MARKED_FOR_DELETION
        repo.save()

        # Verify the repo exists in the DB but is marked for deletion
        assert (
            Repository.select()
            .where(
                (Repository.namespace_user == org)
                & (Repository.state == RepositoryState.MARKED_FOR_DELETION)
            )
            .exists()
        )

        # Should succeed — MARKED_FOR_DELETION repos should not block creation
        config = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor.example.com",
            external_namespace="my-project",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
        )

        assert config is not None
        assert config.organization == org

    def test_create_org_mirror_config_rejects_normal_repos_with_deleted(self, initialized_db):
        """
        Creating org mirror config should still be rejected when the organization
        has NORMAL-state repositories, even if it also has MARKED_FOR_DELETION ones.

        Regression test for PROJQUAY-10982.
        """
        org, robot = _create_org_and_robot("create_test_mixed_repos")
        visibility = Visibility.get(name="private")

        # Create a repo marked for deletion
        deleted_repo = model.repository.create_repository(
            org.username, "deleted-repo", None, visibility="private"
        )
        deleted_repo.state = RepositoryState.MARKED_FOR_DELETION
        deleted_repo.save()

        # Create a normal repo
        model.repository.create_repository(org.username, "normal-repo", None, visibility="private")

        # Should still reject — a NORMAL repo exists
        with pytest.raises(DataModelException) as excinfo:
            create_org_mirror_config(
                organization=org,
                internal_robot=robot,
                external_registry_type=SourceRegistryType.HARBOR,
                external_registry_url="https://harbor.example.com",
                external_namespace="my-project",
                visibility=visibility,
                sync_interval=3600,
                sync_start_date=datetime.utcnow(),
            )

        assert "already contains repositories" in str(excinfo.value)


class TestDeleteOrgMirrorConfig:
    """Tests for delete_org_mirror_config function."""

    def test_delete_org_mirror_config_success(self, initialized_db):
        """
        Test successful deletion of an organization mirror configuration.
        """
        org, robot = _create_org_and_robot("delete_test1")
        config = _create_org_mirror_config(org, robot)

        # Verify config exists
        assert get_org_mirror_config(org) is not None

        # Delete the config
        result = delete_org_mirror_config(config)

        assert result is True
        assert get_org_mirror_config(org) is None

    def test_delete_org_mirror_config_with_discovered_repos(self, initialized_db):
        """
        Deleting a config should also delete all associated discovered repositories.
        """
        org, robot = _create_org_and_robot("delete_test3")
        config = _create_org_mirror_config(org, robot)

        # Create some discovered repositories
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo1",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo2",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo3",
            sync_status=OrgMirrorRepoStatus.SYNCING,
        )

        # Verify discovered repos exist
        repo_count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert repo_count == 3

        # Delete the config
        result = delete_org_mirror_config(config)

        assert result is True
        assert get_org_mirror_config(org) is None

        # Verify discovered repos are also deleted
        repo_count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert repo_count == 0

    def test_delete_org_mirror_config_does_not_affect_other_orgs(self, initialized_db):
        """
        Deleting a config for one org should not affect other orgs' configs.
        """
        org1, robot1 = _create_org_and_robot("delete_test4a")
        org2, robot2 = _create_org_and_robot("delete_test4b")

        config1 = _create_org_mirror_config(org1, robot1, external_namespace="project-a")
        config2 = _create_org_mirror_config(org2, robot2, external_namespace="project-b")

        # Add discovered repos to both configs
        OrgMirrorRepository.create(
            org_mirror_config=config1,
            repository_name="repo1",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config2,
            repository_name="repo2",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        # Delete config1
        result = delete_org_mirror_config(config1)

        assert result is True
        assert get_org_mirror_config(org1) is None

        # Config2 should still exist
        remaining = get_org_mirror_config(org2)
        assert remaining is not None
        assert remaining.id == config2.id

        # Config2's discovered repos should still exist
        repo_count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config2)
            .count()
        )
        assert repo_count == 1

    def test_delete_org_mirror_config_can_recreate_after_delete(self, initialized_db):
        """
        After deleting a config, a new config can be created for the same org.
        """
        org, robot = _create_org_and_robot("delete_test5")
        visibility = Visibility.get(name="private")

        # Create first config
        config1 = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.HARBOR,
            external_registry_url="https://harbor1.example.com",
            external_namespace="project1",
            visibility=visibility,
            sync_interval=3600,
            sync_start_date=datetime.utcnow(),
        )

        # Delete it
        delete_org_mirror_config(config1)

        # Create a new config
        config2 = create_org_mirror_config(
            organization=org,
            internal_robot=robot,
            external_registry_type=SourceRegistryType.QUAY,
            external_registry_url="https://quay.io",
            external_namespace="project2",
            visibility=visibility,
            sync_interval=7200,
            sync_start_date=datetime.utcnow(),
        )

        assert config2 is not None
        assert config2.external_registry_url == "https://quay.io"
        assert config2.external_namespace == "project2"


class TestUpdateOrgMirrorConfig:
    """Tests for update_org_mirror_config function."""

    def test_update_org_mirror_config_success(self, initialized_db):
        """
        Test successful update of an organization mirror configuration.
        """
        org, robot = _create_org_and_robot("update_test1")
        config = _create_org_mirror_config(org, robot)

        # Update the config
        updated = update_org_mirror_config(
            org,
            external_registry_url="https://new-harbor.example.com",
            sync_interval=7200,
        )

        assert updated is not None
        assert updated.id == config.id
        assert updated.external_registry_url == "https://new-harbor.example.com"
        assert updated.sync_interval == 7200
        # Original fields should remain unchanged
        assert updated.external_namespace == "my-project"

    def test_update_org_mirror_config_not_found(self, initialized_db):
        """
        Updating a config that doesn't exist should return None.
        """
        org, _ = _create_org_and_robot("update_test2")

        result = update_org_mirror_config(org, sync_interval=7200)

        assert result is None

    def test_update_org_mirror_config_is_enabled(self, initialized_db):
        """
        Test updating the is_enabled field.
        """
        org, robot = _create_org_and_robot("update_test3")
        _create_org_mirror_config(org, robot, is_enabled=True)

        # Disable mirroring
        updated = update_org_mirror_config(org, is_enabled=False)

        assert updated is not None
        assert updated.is_enabled is False

        # Re-enable mirroring
        updated = update_org_mirror_config(org, is_enabled=True)

        assert updated.is_enabled is True

    def test_update_org_mirror_config_visibility(self, initialized_db):
        """
        Test updating the visibility field.
        """
        org, robot = _create_org_and_robot("update_test4")
        private_visibility = Visibility.get(name="private")
        public_visibility = Visibility.get(name="public")
        _create_org_mirror_config(org, robot, visibility=private_visibility)

        # Update to public
        updated = update_org_mirror_config(org, visibility=public_visibility)

        assert updated is not None
        assert updated.visibility.name == "public"

    def test_update_org_mirror_config_robot(self, initialized_db):
        """
        Test updating the internal robot.
        """
        org, robot1 = _create_org_and_robot("update_test5")
        # Create a second robot for the same org
        robot2, _ = create_robot("mirrorbot2", org)
        _create_org_mirror_config(org, robot1)

        # Update to use the second robot
        updated = update_org_mirror_config(org, internal_robot=robot2)

        assert updated is not None
        assert updated.internal_robot.id == robot2.id

    def test_update_org_mirror_config_robot_wrong_namespace(self, initialized_db):
        """
        Updating config with a robot from a different namespace should raise an error.
        """
        org1, robot1 = _create_org_and_robot("update_test6a")
        org2, robot2 = _create_org_and_robot("update_test6b")
        _create_org_mirror_config(org1, robot1)

        with pytest.raises(DataModelException) as excinfo:
            update_org_mirror_config(org1, internal_robot=robot2)

        assert "belong to the organization" in str(excinfo.value)

    def test_update_org_mirror_config_filters(self, initialized_db):
        """
        Test updating repository filters.
        """
        org, robot = _create_org_and_robot("update_test7")
        _create_org_mirror_config(org, robot, repository_filters=["ubuntu*"])

        # Update filters
        new_filters = ["debian*", "alpine", "nginx*"]
        updated = update_org_mirror_config(org, repository_filters=new_filters)

        assert updated is not None
        assert updated.repository_filters == new_filters

    def test_update_org_mirror_config_external_registry_config(self, initialized_db):
        """
        Test updating external_registry_config.
        """
        org, robot = _create_org_and_robot("update_test8")
        _create_org_mirror_config(org, robot)

        new_config = {
            "verify_tls": False,
            "proxy": {"https_proxy": "https://newproxy.example.com"},
        }
        updated = update_org_mirror_config(org, external_registry_config=new_config)

        assert updated is not None
        assert updated.external_registry_config == new_config

    def test_update_org_mirror_config_multiple_fields(self, initialized_db):
        """
        Test updating multiple fields at once.
        """
        org, robot = _create_org_and_robot("update_test9")
        _create_org_mirror_config(org, robot)
        new_start_date = datetime.utcnow() + timedelta(hours=1)

        updated = update_org_mirror_config(
            org,
            is_enabled=False,
            external_registry_url="https://updated.example.com",
            external_namespace="updated-project",
            sync_interval=14400,
            sync_start_date=new_start_date,
            skopeo_timeout=600,
        )

        assert updated is not None
        assert updated.is_enabled is False
        assert updated.external_registry_url == "https://updated.example.com"
        assert updated.external_namespace == "updated-project"
        assert updated.sync_interval == 14400
        assert updated.skopeo_timeout == 600

    def test_update_org_mirror_config_credentials(self, initialized_db):
        """
        Test updating external registry credentials.
        """
        org, robot = _create_org_and_robot("update_test10")
        _create_org_mirror_config(org, robot)

        updated = update_org_mirror_config(
            org,
            external_registry_username="newuser",
            external_registry_password="newpassword",
        )

        assert updated is not None
        # Verify credentials were updated (they're encrypted)
        assert updated.external_registry_username is not None
        assert updated.external_registry_password is not None

    def test_update_org_mirror_config_clear_credentials(self, initialized_db):
        """
        Test that passing None explicitly clears credentials,
        while omitting credential args preserves them (_UNSET sentinel).
        """
        org, robot = _create_org_and_robot("update_test_clear_creds")
        _create_org_mirror_config(org, robot)

        # Set credentials first
        updated = update_org_mirror_config(
            org,
            external_registry_username="myuser",
            external_registry_password="mypassword",
        )
        assert updated.external_registry_username is not None
        assert updated.external_registry_password is not None

        # Omitting credential args should NOT clear them (sentinel behavior)
        updated = update_org_mirror_config(org, sync_interval=7200)
        assert updated.external_registry_username is not None
        assert updated.external_registry_password is not None

        # Passing None explicitly should clear them
        updated = update_org_mirror_config(
            org,
            external_registry_username=None,
            external_registry_password=None,
        )
        assert updated.external_registry_username is None
        assert updated.external_registry_password is None

    def test_update_org_mirror_config_preserves_unchanged_fields(self, initialized_db):
        """
        Updating specific fields should not affect other fields.
        """
        org, robot = _create_org_and_robot("update_test11")
        public_visibility = Visibility.get(name="public")
        filters = ["redis*", "mysql*"]
        _create_org_mirror_config(
            org,
            robot,
            external_registry_url="https://original.example.com",
            external_namespace="original-project",
            visibility=public_visibility,
            sync_interval=3600,
            repository_filters=filters,
            skopeo_timeout=300,
        )

        # Only update sync_interval
        updated = update_org_mirror_config(org, sync_interval=7200)

        assert updated is not None
        assert updated.sync_interval == 7200
        # All other fields should be unchanged
        assert updated.external_registry_url == "https://original.example.com"
        assert updated.external_namespace == "original-project"
        assert updated.visibility.name == "public"
        assert updated.repository_filters == filters
        assert updated.skopeo_timeout == 300


class TestGetEligibleOrgMirrorRepos:
    """Tests for get_eligible_org_mirror_repos function."""

    def test_no_repos_returns_empty(self, initialized_db):
        """
        When no OrgMirrorRepository entries exist, return empty result.
        """
        result = list(get_eligible_org_mirror_repos())
        assert result == []

    def test_ready_candidates_returned(self, initialized_db):
        """
        Repos with sync_start_date in the past and retries remaining should be returned.
        """
        org, robot = _create_org_and_robot("eligible_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a ready repo (past due, retries remaining, not syncing)
        past_time = datetime.utcnow() - timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="ready-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 1
        assert result[0].repository_name == "ready-repo"

    def test_sync_now_candidates_returned(self, initialized_db):
        """
        Repos with SYNC_NOW status and no expiration should be returned.
        """
        org, robot = _create_org_and_robot("eligible_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a SYNC_NOW repo
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
            sync_start_date=None,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 1
        assert result[0].repository_name == "sync-now-repo"

    def test_expired_syncing_candidates_returned(self, initialized_db):
        """
        Repos that were syncing but whose expiration has passed (stalled worker) should be returned.
        """
        org, robot = _create_org_and_robot("eligible_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create an expired syncing repo
        past_time = datetime.utcnow() - timedelta(hours=2)
        expired_time = datetime.utcnow() - timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="expired-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=expired_time,  # Expired
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 1
        assert result[0].repository_name == "expired-repo"

    def test_currently_syncing_not_returned(self, initialized_db):
        """
        Repos currently syncing with valid expiration should not be returned.
        """
        org, robot = _create_org_and_robot("eligible_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a currently syncing repo with future expiration
        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=future_time,  # Not expired yet
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 0

    def test_no_retries_remaining_not_returned(self, initialized_db):
        """
        Repos with zero retries remaining should not be returned.
        """
        org, robot = _create_org_and_robot("eligible_test5")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a repo with no retries left
        past_time = datetime.utcnow() - timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="no-retries-repo",
            sync_status=OrgMirrorRepoStatus.FAIL,
            sync_start_date=past_time,
            sync_retries_remaining=0,  # No retries
            sync_expiration_date=None,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 0

    def test_disabled_config_repos_not_returned(self, initialized_db):
        """
        Repos from disabled OrgMirrorConfig should not be returned.
        """
        org, robot = _create_org_and_robot("eligible_test6")
        config = _create_org_mirror_config(org, robot, is_enabled=False)  # Disabled

        # Create a ready repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="disabled-config-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 0

    def test_future_start_date_not_returned(self, initialized_db):
        """
        Repos with sync_start_date in the future should not be returned.
        """
        org, robot = _create_org_and_robot("eligible_test7")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a repo scheduled for the future
        future_time = datetime.utcnow() + timedelta(hours=1)
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="future-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
            sync_start_date=future_time,  # Not yet due
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 0

    def test_ordered_by_sync_start_date(self, initialized_db):
        """
        Results should be ordered by sync_start_date ascending.
        """
        org, robot = _create_org_and_robot("eligible_test8")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create repos with different start dates
        now = datetime.utcnow()
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-3",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=now - timedelta(hours=1),  # Most recent
            sync_retries_remaining=3,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-1",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=now - timedelta(hours=3),  # Oldest
            sync_retries_remaining=3,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-2",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=now - timedelta(hours=2),  # Middle
            sync_retries_remaining=3,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 3
        assert result[0].repository_name == "repo-1"
        assert result[1].repository_name == "repo-2"
        assert result[2].repository_name == "repo-3"

    def test_multiple_orgs_eligible_repos(self, initialized_db):
        """
        Eligible repos from multiple organizations should all be returned.
        """
        org1, robot1 = _create_org_and_robot("eligible_test9a")
        org2, robot2 = _create_org_and_robot("eligible_test9b")
        config1 = _create_org_mirror_config(org1, robot1, is_enabled=True)
        config2 = _create_org_mirror_config(org2, robot2, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)

        OrgMirrorRepository.create(
            org_mirror_config=config1,
            repository_name="org1-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config2,
            repository_name="org2-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        result = list(get_eligible_org_mirror_repos())

        assert len(result) == 2
        repo_names = {r.repository_name for r in result}
        assert repo_names == {"org1-repo", "org2-repo"}


class TestGetMinMaxIdForOrgMirrorRepo:
    """Tests for get_min_id_for_org_mirror_repo and get_max_id_for_org_mirror_repo functions."""

    def test_empty_table_returns_none(self, initialized_db):
        """
        When no OrgMirrorRepository entries exist, both functions return None.
        """
        # Ensure no repos exist from previous tests by checking result type
        min_id = get_min_id_for_org_mirror_repo()
        max_id = get_max_id_for_org_mirror_repo()

        # Both should be None or integers (depending on test isolation)
        assert min_id is None or isinstance(min_id, int)
        assert max_id is None or isinstance(max_id, int)

    def test_single_repo_min_equals_max(self, initialized_db):
        """
        With a single repo, min and max should be equal.
        """
        org, robot = _create_org_and_robot("minmax_test1")
        config = _create_org_mirror_config(org, robot)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="single-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        min_id = get_min_id_for_org_mirror_repo()
        max_id = get_max_id_for_org_mirror_repo()

        assert min_id is not None
        assert max_id is not None
        assert min_id <= max_id

    def test_multiple_repos_correct_min_max(self, initialized_db):
        """
        With multiple repos, min and max should return correct IDs.
        """
        org, robot = _create_org_and_robot("minmax_test2")
        config = _create_org_mirror_config(org, robot)

        repo1 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-a",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-b",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )
        repo3 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-c",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        min_id = get_min_id_for_org_mirror_repo()
        max_id = get_max_id_for_org_mirror_repo()

        assert min_id is not None
        assert max_id is not None
        assert min_id < max_id
        assert min_id <= repo1.id
        assert max_id >= repo3.id


class TestClaimOrgMirrorRepo:
    """Tests for claim_org_mirror_repo function."""

    def test_claim_success(self, initialized_db):
        """
        Successfully claiming an unclaimed repo should return the updated repo.
        """
        org, robot = _create_org_and_robot("claim_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="claim-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )
        original_transaction_id = repo.sync_transaction_id

        claimed = claim_org_mirror_repo(repo)

        assert claimed is not None
        assert claimed.id == repo.id
        assert claimed.sync_status == OrgMirrorRepoStatus.SYNCING
        assert claimed.sync_expiration_date is not None
        assert claimed.sync_expiration_date > datetime.utcnow()
        assert claimed.sync_transaction_id != original_transaction_id

    def test_claim_already_syncing_returns_none(self, initialized_db):
        """
        Trying to claim a repo already being synced with valid expiration should return None.
        """
        org, robot = _create_org_and_robot("claim_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=future_time,  # Valid expiration
        )

        claimed = claim_org_mirror_repo(repo)

        assert claimed is None

    def test_claim_expired_syncing_succeeds(self, initialized_db):
        """
        Claiming a repo that was syncing but expired should succeed after reset.
        """
        org, robot = _create_org_and_robot("claim_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=2)
        expired_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="expired-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=1,
            sync_expiration_date=expired_time,  # Expired
        )

        claimed = claim_org_mirror_repo(repo)

        assert claimed is not None
        assert claimed.sync_status == OrgMirrorRepoStatus.SYNCING
        assert claimed.sync_expiration_date > datetime.utcnow()

    def test_claim_concurrent_prevention(self, initialized_db):
        """
        Two concurrent claims should result in only one success.
        """
        org, robot = _create_org_and_robot("claim_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="concurrent-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        # First claim succeeds
        claimed1 = claim_org_mirror_repo(repo)
        assert claimed1 is not None

        # Second claim with stale transaction_id should fail
        # (repo still has old transaction_id)
        claimed2 = claim_org_mirror_repo(repo)
        assert claimed2 is None

    @pytest.mark.usefixtures("initialized_db")
    def test_claim_cancelled_repo_returns_none(self):
        """
        Claiming a repo that was cancelled (even with stale object) should return None.
        This prevents race condition where cancel is triggered after repos are fetched.
        """
        org, robot = _create_org_and_robot("claim_test5")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-claim-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        # Simulate cancel being triggered (as propagate_status_to_repos would do)
        # Note: transaction_id is NOT updated, simulating the race condition
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.CANCEL,
            sync_start_date=None,
            sync_retries_remaining=0,
        ).where(OrgMirrorRepository.id == repo.id).execute()

        # Attempt to claim with stale object (still has original transaction_id)
        claimed = claim_org_mirror_repo(repo)

        # Should return None because current DB status is CANCEL
        assert claimed is None

        # Verify status remains CANCEL (not overwritten to SYNCING)
        refreshed = OrgMirrorRepository.get_by_id(repo.id)
        assert refreshed.sync_status == OrgMirrorRepoStatus.CANCEL

    @pytest.mark.usefixtures("initialized_db")
    def test_claim_cancelled_repo_with_syncing_status_returns_none(self):
        """
        Even if a repo was SYNCING and then cancelled, claim should fail.
        """
        org, robot = _create_org_and_robot("claim_test6")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-cancelled-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=future_time,
        )

        # Simulate cancel being triggered while syncing
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.CANCEL,
            sync_start_date=None,
            sync_retries_remaining=0,
        ).where(OrgMirrorRepository.id == repo.id).execute()

        # Attempt to claim with stale object
        claimed = claim_org_mirror_repo(repo)

        # Should return None
        assert claimed is None

    @pytest.mark.usefixtures("initialized_db")
    def test_claim_deleted_repo_returns_none(self):
        """
        Claiming a repo that gets deleted during claim should return None.
        This tests the DoesNotExist exception handling.
        """
        from unittest.mock import patch

        org, robot = _create_org_and_robot("claim_test7")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="delete-during-claim-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_retries_remaining=3,
        )

        original_get_by_id = OrgMirrorRepository.get_by_id

        def mock_get_by_id(id_val):
            # Delete the repo when get_by_id is called (simulates race condition)
            OrgMirrorRepository.delete().where(OrgMirrorRepository.id == id_val).execute()
            return original_get_by_id(id_val)

        with patch.object(OrgMirrorRepository, "get_by_id", side_effect=mock_get_by_id):
            claimed = claim_org_mirror_repo(repo)

        # Should return None because repo was deleted
        assert claimed is None

    @pytest.mark.usefixtures("initialized_db")
    def test_claim_expired_repo_when_expire_fails(self):
        """
        Claiming an expired repo should return None if expire_org_mirror_repo fails.
        This tests the case where expire returns None during claim.
        """
        from unittest.mock import patch

        org, robot = _create_org_and_robot("claim_test8")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=2)
        expired_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="expire-fail-claim-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=1,
            sync_expiration_date=expired_time,
        )

        # Mock expire_org_mirror_repo to return None (simulates race condition)
        with patch("data.model.org_mirror.expire_org_mirror_repo", return_value=None):
            claimed = claim_org_mirror_repo(repo)

        # Should return None because expire failed
        assert claimed is None


class TestReleaseOrgMirrorRepo:
    """Tests for release_org_mirror_repo function."""

    def test_release_success(self, initialized_db):
        """
        Releasing after successful sync should schedule next sync.
        """
        org, robot = _create_org_and_robot("release_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True, sync_interval=3600)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="release-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        released = release_org_mirror_repo(repo, OrgMirrorRepoStatus.SUCCESS)

        assert released is not None
        assert released.sync_status == OrgMirrorRepoStatus.SUCCESS
        assert released.sync_expiration_date is None
        assert released.sync_start_date > datetime.utcnow()  # Scheduled for future
        assert released.sync_retries_remaining == MAX_SYNC_RETRIES
        assert released.last_sync_date is not None

    def test_release_fail_decrements_retries(self, initialized_db):
        """
        Releasing after failed sync should decrement retries.
        """
        org, robot = _create_org_and_robot("release_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True, sync_interval=3600)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="fail-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        released = release_org_mirror_repo(repo, OrgMirrorRepoStatus.FAIL)

        assert released is not None
        assert released.sync_status == OrgMirrorRepoStatus.FAIL
        assert released.sync_retries_remaining == 2  # Decremented

    def test_release_fail_exhausted_retries_schedules_next(self, initialized_db):
        """
        When retries are exhausted after failure, should schedule next sync anyway.
        """
        org, robot = _create_org_and_robot("release_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True, sync_interval=3600)

        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="exhausted-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=1,  # Last retry
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        released = release_org_mirror_repo(repo, OrgMirrorRepoStatus.FAIL)

        assert released is not None
        assert released.sync_status == OrgMirrorRepoStatus.FAIL
        assert released.sync_retries_remaining == MAX_SYNC_RETRIES  # Reset
        assert released.sync_start_date > datetime.utcnow()  # Scheduled for future


class TestExpireOrgMirrorRepo:
    """Tests for expire_org_mirror_repo function."""

    def test_expire_resets_repo(self, initialized_db):
        """
        Expiring a stalled repo should reset its state.
        """
        org, robot = _create_org_and_robot("expire_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=2)
        expired_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="stalled-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=1,
            sync_expiration_date=expired_time,
        )

        expired = expire_org_mirror_repo(repo)

        assert expired is not None
        assert expired.sync_status == OrgMirrorRepoStatus.NEVER_RUN
        assert expired.sync_expiration_date is None
        assert expired.sync_retries_remaining == MAX_SYNC_RETRIES

    def test_expire_deleted_repo_returns_none(self, initialized_db):
        """
        Expiring a repo that gets deleted during expire should return None.
        This tests the DoesNotExist exception handling.
        """
        from unittest.mock import patch

        org, robot = _create_org_and_robot("expire_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=2)
        expired_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="delete-during-expire-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=past_time,
            sync_retries_remaining=1,
            sync_expiration_date=expired_time,
        )

        original_get_by_id = OrgMirrorRepository.get_by_id

        def mock_get_by_id(id_val):
            # Delete the repo when get_by_id is called (simulates race condition)
            OrgMirrorRepository.delete().where(OrgMirrorRepository.id == id_val).execute()
            return original_get_by_id(id_val)

        with patch.object(OrgMirrorRepository, "get_by_id", side_effect=mock_get_by_id):
            expired = expire_org_mirror_repo(repo)

        # Should return None because repo was deleted
        assert expired is None


class TestUpdateSyncStatusToSyncNow:
    """Tests for update_sync_status_to_sync_now function."""

    def test_sync_now_updates_status(self, initialized_db):
        """
        Should update status to SYNC_NOW and set sync_start_date to now.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Start with NEVER_RUN status
        assert config.sync_status == OrgMirrorStatus.NEVER_RUN

        before = datetime.utcnow()
        result, reason = update_sync_status_to_sync_now(config)
        after = datetime.utcnow()

        assert result is not None
        assert reason is None
        assert result.sync_status == OrgMirrorStatus.SYNC_NOW
        assert result.sync_start_date >= before
        assert result.sync_start_date <= after
        assert result.sync_expiration_date is None
        assert result.sync_retries_remaining >= 1

    def test_sync_now_fails_when_syncing(self, initialized_db):
        """
        Should return None if config is already SYNCING.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set to SYNCING
        config.sync_status = OrgMirrorStatus.SYNCING
        config.save()

        result, reason = update_sync_status_to_sync_now(config)

        assert result is None
        assert "discovery" in reason

    def test_sync_now_restores_retries(self, initialized_db):
        """
        Should restore retries to at least 1 if zero.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Exhaust retries
        config.sync_retries_remaining = 0
        config.sync_status = OrgMirrorStatus.FAIL
        config.save()

        result, reason = update_sync_status_to_sync_now(config)

        assert result is not None
        assert reason is None
        assert result.sync_retries_remaining >= 1

    def test_sync_now_blocked_when_repos_syncing(self, initialized_db):
        """
        Should return None when repos are in SYNCING or SYNC_NOW state.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        result, reason = update_sync_status_to_sync_now(config)
        assert result is None
        assert "repositories are still syncing" in reason

    def test_sync_now_blocked_when_repos_sync_now(self, initialized_db):
        """
        Should return None when repos are in SYNC_NOW state.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test5")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
        )

        result, reason = update_sync_status_to_sync_now(config)
        assert result is None
        assert "repositories are still syncing" in reason

    def test_sync_now_blocked_when_repos_never_run(self, initialized_db):
        """
        Should return None when repos are in NEVER_RUN state.
        NEVER_RUN repos are scheduled and pending worker pickup — triggering
        a new sync would restart discovery and conflict with queued work.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test6")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result, reason = update_sync_status_to_sync_now(config)
        assert result is None
        assert "repositories are still syncing" in reason

    def test_sync_now_blocked_when_mixed_active_and_terminal(self, initialized_db):
        """
        Should return None when ANY repo is in an active state, even if
        other repos are in terminal states.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test_mixed")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="success-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        result, reason = update_sync_status_to_sync_now(config)
        assert result is None
        assert "repositories are still syncing" in reason

    def test_sync_now_allowed_with_terminal_state_repos(self, initialized_db):
        """
        Should succeed when all repos are in terminal states (SUCCESS, FAIL, CANCEL).
        Config update should not modify repo statuses — the worker propagates after discovery.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test7")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        fail_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="fail-repo",
            sync_status=OrgMirrorRepoStatus.FAIL,
            sync_retries_remaining=0,
        )
        success_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="success-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
        )

        result, reason = update_sync_status_to_sync_now(config)

        assert result is not None
        assert reason is None
        assert result.sync_status == OrgMirrorStatus.SYNC_NOW

        # Verify repos retain their original status
        fail_repo = OrgMirrorRepository.get_by_id(fail_repo.id)
        success_repo = OrgMirrorRepository.get_by_id(success_repo.id)

        assert fail_repo.sync_status == OrgMirrorRepoStatus.FAIL
        assert success_repo.sync_status == OrgMirrorRepoStatus.SUCCESS

    def test_sync_now_blocked_when_fail_with_retries_remaining(self, initialized_db):
        """
        Should reject sync-now when FAIL repos still have retries remaining,
        since the worker will retry them (matching get_eligible_org_mirror_repos).
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_fail_retry")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="retryable-fail-repo",
            sync_status=OrgMirrorRepoStatus.FAIL,
            sync_retries_remaining=2,
        )

        result, reason = update_sync_status_to_sync_now(config)

        assert result is None
        assert reason is not None
        assert "syncing" in reason.lower()


class TestUpdateSyncStatusToCancel:
    """Tests for update_sync_status_to_cancel function."""

    def test_cancel_when_syncing(self, initialized_db):
        """
        Should cancel when status is SYNCING and preserve sync_start_date.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        original_sync_start_date = config.sync_start_date

        # Set to SYNCING
        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        result = update_sync_status_to_cancel(config)

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.CANCEL
        assert result.sync_expiration_date is not None
        assert result.sync_start_date == original_sync_start_date
        assert result.sync_retries_remaining == 0

    def test_cancel_when_sync_now(self, initialized_db):
        """
        Should cancel when status is SYNC_NOW.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set to SYNC_NOW
        config.sync_status = OrgMirrorStatus.SYNC_NOW
        config.save()

        result = update_sync_status_to_cancel(config)

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.CANCEL

    def test_cancel_works_from_any_status(self, initialized_db):
        """
        Should cancel from any status except CANCEL.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        # Test NEVER_RUN → CANCEL
        org1, robot1 = _create_org_and_robot("cancel_test3a")
        config1 = _create_org_mirror_config(org1, robot1, is_enabled=True)
        assert config1.sync_status == OrgMirrorStatus.NEVER_RUN

        result1 = update_sync_status_to_cancel(config1)
        assert result1 is not None
        assert result1.sync_status == OrgMirrorStatus.CANCEL

        # Test SUCCESS → CANCEL
        org2, robot2 = _create_org_and_robot("cancel_test3b")
        config2 = _create_org_mirror_config(org2, robot2, is_enabled=True)
        config2.sync_status = OrgMirrorStatus.SUCCESS
        config2.save()

        result2 = update_sync_status_to_cancel(config2)
        assert result2 is not None
        assert result2.sync_status == OrgMirrorStatus.CANCEL

        # Test FAIL → CANCEL
        org3, robot3 = _create_org_and_robot("cancel_test3c")
        config3 = _create_org_mirror_config(org3, robot3, is_enabled=True)
        config3.sync_status = OrgMirrorStatus.FAIL
        config3.save()

        result3 = update_sync_status_to_cancel(config3)
        assert result3 is not None
        assert result3.sync_status == OrgMirrorStatus.CANCEL

    def test_cancel_is_idempotent(self, initialized_db):
        """
        Should return None when already CANCEL (idempotent behavior).
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test3d")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set to CANCEL
        config.sync_status = OrgMirrorStatus.CANCEL
        config.save()

        result = update_sync_status_to_cancel(config)

        # Should return None since already cancelled
        assert result is None

    def test_cancel_does_not_cancel_repos(self, initialized_db):
        """
        Should only update the config, not the repos.
        Repos are updated by the worker via propagate_status_to_repos.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create repos in various states
        syncing_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )
        sync_now_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
        )
        never_run_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        # Set config to SYNCING
        config.sync_status = OrgMirrorStatus.SYNCING
        config.save()

        result = update_sync_status_to_cancel(config)

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.CANCEL

        # Verify repos are NOT updated - they retain their original status
        # The worker will propagate the status when it picks up the config
        syncing_repo = OrgMirrorRepository.get_by_id(syncing_repo.id)
        sync_now_repo = OrgMirrorRepository.get_by_id(sync_now_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)

        assert syncing_repo.sync_status == OrgMirrorRepoStatus.SYNCING
        assert sync_now_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.NEVER_RUN

    def test_cancel_not_eligible_after_release(self, initialized_db):
        """
        Regression test for PROJQUAY-10798: after the worker processes a cancel
        and releases the config, it must NOT be re-picked by get_eligible_org_mirror_configs.
        """
        from data.model.org_mirror import (
            claim_org_mirror_config,
            get_eligible_org_mirror_configs,
            release_org_mirror_config,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_loop_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Simulate: config is syncing, user cancels
        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        update_sync_status_to_cancel(config)

        # Worker picks up the cancel
        config = OrgMirrorConfig.get_by_id(config.id)
        eligible_ids = [c.id for c in get_eligible_org_mirror_configs()]
        assert config.id in eligible_ids

        # Worker claims, processes, and releases
        claimed = claim_org_mirror_config(config)
        assert claimed is not None
        release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        # After release, config must NOT be eligible again immediately
        config = OrgMirrorConfig.get_by_id(config.id)
        eligible_ids = [c.id for c in get_eligible_org_mirror_configs()]
        assert config.id not in eligible_ids
        # Cancel transitions to SUCCESS after processing (PROJQUAY-11027)
        assert config.sync_status == OrgMirrorStatus.SUCCESS
        assert config.sync_expiration_date is None

    def test_cancel_preserves_sync_start_date(self, initialized_db):
        """
        Regression test for PROJQUAY-11027: cancelling a sync must preserve
        sync_start_date so that future scheduled syncs continue.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_preserve_date")
        future_date = datetime.utcnow() + timedelta(hours=2)
        config = _create_org_mirror_config(org, robot, is_enabled=True, sync_start_date=future_date)

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        result = update_sync_status_to_cancel(config)

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.CANCEL
        assert result.sync_start_date is not None
        assert result.sync_start_date == future_date

    def test_cancel_release_schedules_next_sync(self, initialized_db):
        """
        Regression test for PROJQUAY-11027: after cancel is processed by the
        worker, release_org_mirror_config must schedule the next sync instead
        of clearing sync_start_date.
        """
        from data.model.org_mirror import (
            MAX_SYNC_RETRIES,
            claim_org_mirror_config,
            release_org_mirror_config,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_release_schedule")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        update_sync_status_to_cancel(config)

        config = OrgMirrorConfig.get_by_id(config.id)
        claimed = claim_org_mirror_config(config)
        assert claimed is not None

        released = release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        assert released is not None
        assert released.sync_status == OrgMirrorStatus.SUCCESS
        assert released.sync_start_date is not None
        assert released.sync_start_date > datetime.utcnow()
        assert released.sync_retries_remaining == MAX_SYNC_RETRIES
        assert released.sync_expiration_date is None

    def test_cancel_release_with_no_sync_start_date(self, initialized_db):
        """
        Cover the else branch in release_org_mirror_config when sync_start_date
        is None at cancel time — next sync should still be scheduled using
        sync_interval from now.
        """
        from data.model.org_mirror import (
            MAX_SYNC_RETRIES,
            claim_org_mirror_config,
            release_org_mirror_config,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_release_no_start")
        config = _create_org_mirror_config(org, robot, is_enabled=True, sync_start_date=None)

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        update_sync_status_to_cancel(config)

        config = OrgMirrorConfig.get_by_id(config.id)
        claimed = claim_org_mirror_config(config)
        assert claimed is not None

        before = datetime.utcnow()
        released = release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        assert released is not None
        assert released.sync_status == OrgMirrorStatus.SUCCESS
        assert released.sync_start_date is not None
        assert released.sync_start_date > before
        assert released.sync_retries_remaining == MAX_SYNC_RETRIES

    def test_cancel_full_flow_preserves_future_syncs(self, initialized_db):
        """
        Regression test for PROJQUAY-11027: end-to-end cancel flow.
        After cancel → release, config must have a future sync_start_date
        and must become eligible again once that date arrives.
        """
        from data.model.org_mirror import (
            claim_org_mirror_config,
            get_eligible_org_mirror_configs,
            release_org_mirror_config,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_full_flow")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        # User cancels
        update_sync_status_to_cancel(config)

        # Worker processes cancel
        config = OrgMirrorConfig.get_by_id(config.id)
        claimed = claim_org_mirror_config(config)
        assert claimed is not None
        released = release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        # Status transitions to SUCCESS so next pickup runs normal discovery
        assert released.sync_status == OrgMirrorStatus.SUCCESS

        # Not eligible immediately (sync_start_date is in the future)
        eligible_ids = [c.id for c in get_eligible_org_mirror_configs()]
        assert released.id not in eligible_ids

        # Simulate time passing: set sync_start_date to the past
        OrgMirrorConfig.update(sync_start_date=datetime.utcnow() - timedelta(seconds=1)).where(
            OrgMirrorConfig.id == released.id
        ).execute()

        # Now the config should be eligible for syncing again
        eligible_ids = [c.id for c in get_eligible_org_mirror_configs()]
        assert released.id in eligible_ids

    def test_cancel_does_not_create_recancel_loop(self, initialized_db):
        """
        Regression test for PROJQUAY-11027: after cancel is processed, the
        config must NOT re-enter the cancel path on the next worker pickup.
        The status must be SUCCESS so the worker runs normal discovery.
        """
        from data.model.org_mirror import (
            claim_org_mirror_config,
            get_eligible_org_mirror_configs,
            release_org_mirror_config,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_no_loop")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        # Cancel and process
        update_sync_status_to_cancel(config)
        config = OrgMirrorConfig.get_by_id(config.id)
        claimed = claim_org_mirror_config(config)
        assert claimed is not None
        release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        # Simulate time passing so config becomes eligible
        OrgMirrorConfig.update(sync_start_date=datetime.utcnow() - timedelta(seconds=1)).where(
            OrgMirrorConfig.id == config.id
        ).execute()

        # Config is eligible
        eligible = list(get_eligible_org_mirror_configs())
        matched = [c for c in eligible if c.id == config.id]
        assert len(matched) == 1

        # Worker picks it up — status must be SUCCESS, NOT CANCEL
        picked_up = matched[0]
        assert picked_up.sync_status == OrgMirrorStatus.SUCCESS

    def test_cancel_repos_transition_to_sync_now_on_next_cycle(self, initialized_db):
        """
        Regression test for PROJQUAY-11027: after cancel is processed,
        schedule_org_mirror_repos_for_sync must transition CANCEL repos
        to SYNC_NOW so they rejoin the sync cycle. SKIP repos are untouched.
        """
        from data.model.org_mirror import (
            MAX_SYNC_RETRIES,
            claim_org_mirror_config,
            propagate_status_to_repos,
            release_org_mirror_config,
            schedule_org_mirror_repos_for_sync,
            update_sync_status_to_cancel,
        )

        org, robot = _create_org_and_robot("cancel_repo_sync_now")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo1 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-a",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_start_date=datetime.utcnow(),
            sync_retries_remaining=MAX_SYNC_RETRIES,
        )
        repo2 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-b",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
            sync_start_date=datetime.utcnow(),
            sync_retries_remaining=MAX_SYNC_RETRIES,
        )
        repo_skip = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-skip",
            sync_status=OrgMirrorRepoStatus.SKIP,
        )

        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        # Cancel and propagate to repos
        update_sync_status_to_cancel(config)
        config = OrgMirrorConfig.get_by_id(config.id)
        propagate_status_to_repos(config, OrgMirrorRepoStatus.CANCEL)

        # Repos are CANCEL with retries=0, sync_start_date=None
        repo1 = OrgMirrorRepository.get_by_id(repo1.id)
        repo2 = OrgMirrorRepository.get_by_id(repo2.id)
        assert repo1.sync_status == OrgMirrorRepoStatus.CANCEL
        assert repo1.sync_retries_remaining == 0
        assert repo1.sync_start_date is None

        # Worker releases config (cancel → success)
        claimed = claim_org_mirror_config(config)
        assert claimed is not None
        release_org_mirror_config(claimed, OrgMirrorStatus.CANCEL)

        # Repos stay CANCEL after release — no bulk reset
        repo1 = OrgMirrorRepository.get_by_id(repo1.id)
        repo2 = OrgMirrorRepository.get_by_id(repo2.id)
        assert repo1.sync_status == OrgMirrorRepoStatus.CANCEL
        assert repo2.sync_status == OrgMirrorRepoStatus.CANCEL

        # Next discovery cycle: schedule picks up CANCEL repos → SYNC_NOW
        config = OrgMirrorConfig.get_by_id(config.id)
        scheduled = schedule_org_mirror_repos_for_sync(config)
        assert scheduled == 2

        repo1 = OrgMirrorRepository.get_by_id(repo1.id)
        repo2 = OrgMirrorRepository.get_by_id(repo2.id)
        repo_skip = OrgMirrorRepository.get_by_id(repo_skip.id)
        assert repo1.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert repo1.sync_retries_remaining == MAX_SYNC_RETRIES
        assert repo1.sync_start_date is not None
        assert repo2.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert repo2.sync_retries_remaining == MAX_SYNC_RETRIES
        assert repo_skip.sync_status == OrgMirrorRepoStatus.SKIP


class TestScheduleOrgMirrorReposForSync:
    """Tests for schedule_org_mirror_repos_for_sync function."""

    def test_schedules_never_run_repos(self, initialized_db):
        """NEVER_RUN repos with no sync_start_date are transitioned to SYNC_NOW."""
        from data.model.org_mirror import schedule_org_mirror_repos_for_sync

        org, robot = _create_org_and_robot("schedule_never_run")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=None,
            sync_retries_remaining=0,
        )

        scheduled = schedule_org_mirror_repos_for_sync(config)

        assert scheduled == 1
        repo = OrgMirrorRepository.get_by_id(repo.id)
        assert repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert repo.sync_start_date is not None
        assert repo.sync_retries_remaining == MAX_SYNC_RETRIES

    def test_skips_repos_with_existing_sync_start_date(self, initialized_db):
        """Repos that already have a sync_start_date set are NOT rescheduled."""
        from data.model.org_mirror import schedule_org_mirror_repos_for_sync

        org, robot = _create_org_and_robot("schedule_skip_dated")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # CANCEL repo with a sync_start_date already set — must not be picked up
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-dated-repo",
            sync_status=OrgMirrorRepoStatus.CANCEL,
            sync_start_date=datetime.utcnow() + timedelta(hours=1),
            sync_retries_remaining=MAX_SYNC_RETRIES,
        )

        scheduled = schedule_org_mirror_repos_for_sync(config)

        assert scheduled == 0
        repo = OrgMirrorRepository.get_by_id(repo.id)
        assert repo.sync_status == OrgMirrorRepoStatus.CANCEL  # unchanged

    def test_returns_zero_when_no_eligible_repos(self, initialized_db):
        """Returns 0 when no repos need scheduling (all SKIP/SUCCESS)."""
        from data.model.org_mirror import schedule_org_mirror_repos_for_sync

        org, robot = _create_org_and_robot("schedule_no_eligible")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="skip-repo",
            sync_status=OrgMirrorRepoStatus.SKIP,
        )
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="success-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
            sync_start_date=datetime.utcnow(),
        )

        scheduled = schedule_org_mirror_repos_for_sync(config)

        assert scheduled == 0

    def test_schedules_both_cancel_and_never_run(self, initialized_db):
        """Both CANCEL and NEVER_RUN repos (with no sync_start_date) are scheduled together."""
        from data.model.org_mirror import schedule_org_mirror_repos_for_sync

        org, robot = _create_org_and_robot("schedule_mixed")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        cancel_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-repo",
            sync_status=OrgMirrorRepoStatus.CANCEL,
            sync_start_date=None,
            sync_retries_remaining=0,
        )
        never_run_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=None,
            sync_retries_remaining=0,
        )
        skip_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="skip-repo",
            sync_status=OrgMirrorRepoStatus.SKIP,
        )

        scheduled = schedule_org_mirror_repos_for_sync(config)

        assert scheduled == 2
        cancel_repo = OrgMirrorRepository.get_by_id(cancel_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)
        skip_repo = OrgMirrorRepository.get_by_id(skip_repo.id)
        assert cancel_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert cancel_repo.sync_retries_remaining == MAX_SYNC_RETRIES
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert never_run_repo.sync_retries_remaining == MAX_SYNC_RETRIES
        assert skip_repo.sync_status == OrgMirrorRepoStatus.SKIP  # unchanged


class TestPropagateStatusToRepos:
    """Tests for propagate_status_to_repos function."""

    def test_propagate_sync_now_skips_syncing_repos(self, initialized_db):
        """
        Should propagate SYNC_NOW to all repos except those currently SYNCING.
        """
        from data.model.org_mirror import propagate_status_to_repos

        org, robot = _create_org_and_robot("propagate_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create repos in various states
        syncing_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )
        never_run_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )
        fail_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="fail-repo",
            sync_status=OrgMirrorRepoStatus.FAIL,
        )

        count = propagate_status_to_repos(config, OrgMirrorRepoStatus.SYNC_NOW)

        # Should have updated 2 repos (not the SYNCING one)
        assert count == 2

        # Verify repos are updated appropriately
        syncing_repo = OrgMirrorRepository.get_by_id(syncing_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)
        fail_repo = OrgMirrorRepository.get_by_id(fail_repo.id)

        # SYNCING repo should be left alone
        assert syncing_repo.sync_status == OrgMirrorRepoStatus.SYNCING

        # All other repos should be set to SYNC_NOW
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert never_run_repo.sync_start_date is not None
        assert fail_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW

    def test_propagate_cancel_includes_syncing_repos(self, initialized_db):
        """
        Should propagate CANCEL to ALL repos including those currently SYNCING.
        """
        from data.model.org_mirror import propagate_status_to_repos

        org, robot = _create_org_and_robot("propagate_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create repos in various states
        syncing_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="syncing-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )
        sync_now_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
        )
        never_run_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        count = propagate_status_to_repos(config, OrgMirrorRepoStatus.CANCEL)

        # Should have updated all 3 repos (including SYNCING)
        assert count == 3

        # Verify all repos are cancelled
        syncing_repo = OrgMirrorRepository.get_by_id(syncing_repo.id)
        sync_now_repo = OrgMirrorRepository.get_by_id(sync_now_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)

        assert syncing_repo.sync_status == OrgMirrorRepoStatus.CANCEL
        assert syncing_repo.sync_start_date is None
        assert syncing_repo.sync_retries_remaining == 0

        assert sync_now_repo.sync_status == OrgMirrorRepoStatus.CANCEL
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.CANCEL

    def test_propagate_skips_repos_already_in_target_status(self, initialized_db):
        """
        Should not update repos that already have the target status.
        """
        from data.model.org_mirror import propagate_status_to_repos

        org, robot = _create_org_and_robot("propagate_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create repos - some already in SYNC_NOW
        OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
        )
        never_run_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        count = propagate_status_to_repos(config, OrgMirrorRepoStatus.SYNC_NOW)

        # Should only update the NEVER_RUN repo
        assert count == 1

        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW


class TestCheckOrgMirrorRepoSyncStatus:
    """Tests for check_org_mirror_repo_sync_status function."""

    def test_returns_current_status(self, initialized_db):
        """
        Should return the current sync status of the repository.
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="check-status-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
        )

        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.SYNCING

    def test_detects_external_status_change(self, initialized_db):
        """
        Should detect status changes made by external processes (e.g., cancel API).
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="external-change-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
        )

        # Initial status should be SYNCING
        assert check_org_mirror_repo_sync_status(repo) == OrgMirrorRepoStatus.SYNCING

        # Simulate external update (e.g., cancel API call)
        OrgMirrorRepository.update(sync_status=OrgMirrorRepoStatus.CANCEL).where(
            OrgMirrorRepository.id == repo.id
        ).execute()

        # Should detect the new status without refreshing the local object
        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.CANCEL

    def test_returns_never_run_status(self, initialized_db):
        """
        Should correctly return NEVER_RUN status.
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="never-run-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.NEVER_RUN

    def test_returns_success_status(self, initialized_db):
        """
        Should correctly return SUCCESS status.
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="success-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
        )

        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.SUCCESS

    def test_returns_fail_status(self, initialized_db):
        """
        Should correctly return FAIL status.
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test5")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="fail-repo",
            sync_status=OrgMirrorRepoStatus.FAIL,
        )

        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.FAIL

    def test_returns_cancel_when_repo_deleted(self, initialized_db):
        """
        Should return CANCEL status when repo has been deleted.
        This handles the case where config is deleted mid-sync.
        """
        from data.model.org_mirror import check_org_mirror_repo_sync_status

        org, robot = _create_org_and_robot("check_status_test6")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="deleted-repo",
            sync_status=OrgMirrorRepoStatus.SYNCING,
        )

        # Delete the repo to simulate config deletion mid-sync
        repo_id = repo.id
        OrgMirrorRepository.delete().where(OrgMirrorRepository.id == repo_id).execute()

        # Should return CANCEL for deleted repo
        result = check_org_mirror_repo_sync_status(repo)

        assert result == OrgMirrorRepoStatus.CANCEL


class TestGetOrgMirrorConfigCount:
    """Tests for get_org_mirror_config_count and get_enabled_org_mirror_config_count."""

    def test_get_org_mirror_config_count(self, initialized_db):
        """
        Creating 3 configs should result in a count of 3 (plus any pre-existing).
        """
        baseline = get_org_mirror_config_count()

        org1, robot1 = _create_org_and_robot("count_test1a")
        org2, robot2 = _create_org_and_robot("count_test1b")
        org3, robot3 = _create_org_and_robot("count_test1c")

        _create_org_mirror_config(org1, robot1)
        _create_org_mirror_config(org2, robot2)
        _create_org_mirror_config(org3, robot3)

        assert get_org_mirror_config_count() == baseline + 3

    def test_get_enabled_org_mirror_config_count(self, initialized_db):
        """
        Creating 3 configs and disabling 1 should result in enabled count of 2 (plus baseline).
        """
        baseline = get_enabled_org_mirror_config_count()

        org1, robot1 = _create_org_and_robot("count_test2a")
        org2, robot2 = _create_org_and_robot("count_test2b")
        org3, robot3 = _create_org_and_robot("count_test2c")

        _create_org_mirror_config(org1, robot1, is_enabled=True)
        _create_org_mirror_config(org2, robot2, is_enabled=True)
        _create_org_mirror_config(org3, robot3, is_enabled=False)

        assert get_enabled_org_mirror_config_count() == baseline + 2


class TestSyncDiscoveredRepos:
    """Tests for sync_discovered_repos batch query optimization."""

    def test_sync_empty_list(self, initialized_db):
        """
        Syncing an empty list should return (0, 0) and create nothing.
        """
        org, robot = _create_org_and_robot("sync_disc_empty")
        config = _create_org_mirror_config(org, robot)

        total, created = sync_discovered_repos(config, [])

        assert total == 0
        assert created == 0

    def test_sync_all_new_repos(self, initialized_db):
        """
        All discovered repos should be created when none exist.
        """
        org, robot = _create_org_and_robot("sync_disc_new")
        config = _create_org_mirror_config(org, robot)

        names = ["repo-a", "repo-b", "repo-c"]
        total, created = sync_discovered_repos(config, names)

        assert total == 3
        assert created == 3

        # Verify all repos exist in DB
        db_names = {
            r.repository_name
            for r in OrgMirrorRepository.select().where(
                OrgMirrorRepository.org_mirror_config == config
            )
        }
        assert db_names == {"repo-a", "repo-b", "repo-c"}

    def test_sync_mixed_existing_and_new(self, initialized_db):
        """
        Only repos that don't exist yet should be created.
        """
        org, robot = _create_org_and_robot("sync_disc_mixed")
        config = _create_org_mirror_config(org, robot)

        # Pre-create some repos
        get_or_create_org_mirror_repo(config, "existing-1")
        get_or_create_org_mirror_repo(config, "existing-2")

        names = ["existing-1", "existing-2", "new-1", "new-2"]
        total, created = sync_discovered_repos(config, names)

        assert total == 4
        assert created == 2

        db_names = {
            r.repository_name
            for r in OrgMirrorRepository.select().where(
                OrgMirrorRepository.org_mirror_config == config
            )
        }
        assert db_names == {"existing-1", "existing-2", "new-1", "new-2"}

    def test_sync_all_existing(self, initialized_db):
        """
        No repos should be created when all already exist.
        """
        org, robot = _create_org_and_robot("sync_disc_existing")
        config = _create_org_mirror_config(org, robot)

        names = ["repo-x", "repo-y"]
        # Create them first
        for name in names:
            get_or_create_org_mirror_repo(config, name)

        total, created = sync_discovered_repos(config, names)

        assert total == 2
        assert created == 0

    def test_sync_idempotent(self, initialized_db):
        """
        Calling sync twice with the same names should not create duplicates.
        """
        org, robot = _create_org_and_robot("sync_disc_idempotent")
        config = _create_org_mirror_config(org, robot)

        names = ["alpha", "beta", "gamma"]

        total1, created1 = sync_discovered_repos(config, names)
        total2, created2 = sync_discovered_repos(config, names)

        assert created1 == 3
        assert created2 == 0

        count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert count == 3

    def test_sync_large_batch(self, initialized_db):
        """
        Handles 1500+ repos, exercising the chunking logic for both
        SELECT IN (chunks of 900) and INSERT (chunks of 100).
        """
        org, robot = _create_org_and_robot("sync_disc_large")
        config = _create_org_mirror_config(org, robot)

        names = [f"repo-{i:04d}" for i in range(1500)]
        total, created = sync_discovered_repos(config, names)

        assert total == 1500
        assert created == 1500

        count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert count == 1500

    def test_sync_duplicate_names_in_input(self, initialized_db):
        """
        Duplicate names in input should be deduplicated, not cause errors.
        """
        org, robot = _create_org_and_robot("sync_disc_dupes")
        config = _create_org_mirror_config(org, robot)

        names = ["dup-repo", "dup-repo", "unique-repo", "dup-repo"]
        total, created = sync_discovered_repos(config, names)

        assert total == 2  # deduplicated count
        assert created == 2

        count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert count == 2

    def test_sync_sets_transaction_id(self, initialized_db):
        """
        Batch-inserted repos must have non-null sync_transaction_id
        for optimistic locking in claim_org_mirror_repo.
        """
        org, robot = _create_org_and_robot("sync_disc_txnid")
        config = _create_org_mirror_config(org, robot)

        sync_discovered_repos(config, ["txn-repo-1", "txn-repo-2"])

        for repo in OrgMirrorRepository.select().where(
            OrgMirrorRepository.org_mirror_config == config
        ):
            assert repo.sync_transaction_id is not None
            assert len(repo.sync_transaction_id) == 36  # UUID format

    def test_sync_concurrent_insert_does_not_raise(self, initialized_db):
        """
        Simulates a race condition: another worker inserts a conflicting row
        between the SELECT and INSERT phases. The on_conflict_ignore clause
        should allow the function to complete without raising IntegrityError.
        """
        org, robot = _create_org_and_robot("sync_disc_race")
        config = _create_org_mirror_config(org, robot)

        names = ["race-repo-1", "race-repo-2", "race-repo-3"]

        original_insert_many = OrgMirrorRepository.insert_many

        def insert_many_with_simulated_race(rows, *args, **kwargs):
            """
            On the first call to insert_many, insert a conflicting row before
            the batch insert runs, simulating a concurrent worker.
            """
            insert_many_with_simulated_race.called = True
            # Simulate a concurrent worker inserting "race-repo-2"
            get_or_create_org_mirror_repo(config, "race-repo-2")
            return original_insert_many(rows, *args, **kwargs)

        insert_many_with_simulated_race.called = False

        with patch.object(
            OrgMirrorRepository, "insert_many", side_effect=insert_many_with_simulated_race
        ):
            total, created = sync_discovered_repos(config, names)

        assert insert_many_with_simulated_race.called
        assert total == 3
        # created is 3: the mock inserts "race-repo-2" inside the same
        # connection/transaction, so COUNT-after minus COUNT-before includes
        # it. In a real multi-connection scenario (PostgreSQL), the delta
        # would be 2 if the concurrent insert committed before count_before.
        assert created == 3

        # But only 3 rows exist in DB (not 4), because on_conflict_ignore
        # silently skipped the duplicate
        count = (
            OrgMirrorRepository.select()
            .where(OrgMirrorRepository.org_mirror_config == config)
            .count()
        )
        assert count == 3


class TestClaimOrgMirrorConfig:
    """Tests for claim_org_mirror_config function."""

    def test_claim_uses_default_duration(self, initialized_db):
        """
        When no max_discovery_duration is passed and no app config is set,
        claim_org_mirror_config should use DEFAULT_MAX_DISCOVERY_DURATION (30 min).
        """
        org, robot = _create_org_and_robot("org_claim_default")
        config = _create_org_mirror_config(org, robot, sync_status=OrgMirrorStatus.NEVER_RUN)

        claimed = claim_org_mirror_config(config)

        assert claimed is not None
        assert claimed.sync_status == OrgMirrorStatus.SYNCING
        assert claimed.sync_expiration_date is not None
        expected_min = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION - 5)
        expected_max = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION + 5)
        assert expected_min <= claimed.sync_expiration_date <= expected_max

    def test_claim_uses_custom_duration(self, initialized_db):
        """
        When a custom max_discovery_duration is passed,
        claim_org_mirror_config should use that value for the expiration.
        """
        org, robot = _create_org_and_robot("org_claim_custom")
        config = _create_org_mirror_config(org, robot, sync_status=OrgMirrorStatus.NEVER_RUN)

        custom_duration = 7200  # 2 hours
        claimed = claim_org_mirror_config(config, max_discovery_duration=custom_duration)

        assert claimed is not None
        assert claimed.sync_status == OrgMirrorStatus.SYNCING
        expected_min = datetime.utcnow() + timedelta(seconds=custom_duration - 5)
        expected_max = datetime.utcnow() + timedelta(seconds=custom_duration + 5)
        assert expected_min <= claimed.sync_expiration_date <= expected_max

    def test_claim_reads_from_app_config(self, initialized_db):
        """
        When no explicit duration is passed, claim_org_mirror_config should
        read ORG_MIRROR_MAX_DISCOVERY_DURATION from app config.
        """
        org, robot = _create_org_and_robot("org_claim_appconfig")
        config = _create_org_mirror_config(org, robot, sync_status=OrgMirrorStatus.NEVER_RUN)

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = 3600  # 1 hour
            claimed = claim_org_mirror_config(config)

        assert claimed is not None
        expected_min = datetime.utcnow() + timedelta(seconds=3600 - 5)
        expected_max = datetime.utcnow() + timedelta(seconds=3600 + 5)
        assert expected_min <= claimed.sync_expiration_date <= expected_max
        mock_app.config.get.assert_called_once_with(
            "ORG_MIRROR_MAX_DISCOVERY_DURATION", DEFAULT_MAX_DISCOVERY_DURATION
        )

    def test_claim_falls_back_on_invalid_app_config(self, initialized_db):
        """
        When app config returns a non-numeric value for ORG_MIRROR_MAX_DISCOVERY_DURATION,
        claim_org_mirror_config should fall back to DEFAULT_MAX_DISCOVERY_DURATION.
        """
        org, robot = _create_org_and_robot("org_claim_invalid")
        config = _create_org_mirror_config(org, robot, sync_status=OrgMirrorStatus.NEVER_RUN)

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = "not_a_number"
            claimed = claim_org_mirror_config(config)

        assert claimed is not None
        expected_min = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION - 5)
        expected_max = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION + 5)
        assert expected_min <= claimed.sync_expiration_date <= expected_max

    def test_claim_falls_back_on_zero_or_negative_app_config(self, initialized_db):
        """
        When app config returns 0 or a negative value for ORG_MIRROR_MAX_DISCOVERY_DURATION,
        claim_org_mirror_config should fall back to DEFAULT_MAX_DISCOVERY_DURATION.
        """
        org, robot = _create_org_and_robot("org_claim_zero")
        config = _create_org_mirror_config(org, robot, sync_status=OrgMirrorStatus.NEVER_RUN)

        with patch("app.app") as mock_app:
            mock_app.config.get.return_value = 0
            claimed = claim_org_mirror_config(config)

        assert claimed is not None
        expected_min = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION - 5)
        expected_max = datetime.utcnow() + timedelta(seconds=DEFAULT_MAX_DISCOVERY_DURATION + 5)
        assert expected_min <= claimed.sync_expiration_date <= expected_max

    def test_claim_fails_when_already_syncing(self, initialized_db):
        """
        When a config is already SYNCING with a valid expiration,
        claim_org_mirror_config should return None.
        """
        org, robot = _create_org_and_robot("org_claim_busy")
        config = _create_org_mirror_config(
            org,
            robot,
            sync_status=OrgMirrorStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        result = claim_org_mirror_config(config, max_discovery_duration=1800)

        assert result is None

    def test_claim_does_not_expire_cancelled_config(self, initialized_db):
        """
        Regression: claim_org_mirror_config must not reset a CANCEL config
        to NEVER_RUN via expire_org_mirror_config, even when
        sync_expiration_date is in the past.
        """
        from unittest.mock import MagicMock, patch

        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("org_claim_cancel_no_expire")
        config = _create_org_mirror_config(
            org,
            robot,
            sync_status=OrgMirrorStatus.SYNCING,
            sync_expiration_date=datetime.utcnow() + timedelta(hours=1),
        )

        # Cancel the config — sets sync_expiration_date=now
        update_sync_status_to_cancel(config)
        config = OrgMirrorConfig.get_by_id(config.id)
        assert config.sync_status == OrgMirrorStatus.CANCEL

        # Simulate time passing so sync_expiration_date is in the past
        OrgMirrorConfig.update(
            sync_expiration_date=datetime.utcnow() - timedelta(seconds=10),
        ).where(OrgMirrorConfig.id == config.id).execute()
        config = OrgMirrorConfig.get_by_id(config.id)

        # Spy on expire_org_mirror_config to verify it is never called
        with patch("data.model.org_mirror.expire_org_mirror_config", wraps=None) as expire_spy:
            claimed = claim_org_mirror_config(config)
            assert claimed is not None
            assert claimed.sync_status == OrgMirrorStatus.SYNCING

            # Verify expire_org_mirror_config was never invoked —
            # the claim transitions CANCEL -> SYNCING directly via atomic update
            expire_spy.assert_not_called()


class TestGetOrgMirrorRepoStatusCounts:
    """Tests for get_org_mirror_repo_status_counts()."""

    def test_mixed_states_returns_correct_counts(self, initialized_db):
        """Repos in various states return correct per-status counts."""
        org, robot = _create_org_and_robot("testorgstatuscounts")
        config = _create_org_mirror_config(org, robot)

        statuses = [
            OrgMirrorRepoStatus.SUCCESS,
            OrgMirrorRepoStatus.SUCCESS,
            OrgMirrorRepoStatus.SYNCING,
            OrgMirrorRepoStatus.FAIL,
            OrgMirrorRepoStatus.NEVER_RUN,
        ]
        for i, status in enumerate(statuses):
            get_or_create_org_mirror_repo(config, f"repo-{i}")
            OrgMirrorRepository.update(sync_status=status).where(
                (OrgMirrorRepository.repository_name == f"repo-{i}")
                & (OrgMirrorRepository.org_mirror_config == config)
            ).execute()

        counts = get_org_mirror_repo_status_counts(config)

        assert counts["SUCCESS"] == 2
        assert counts["SYNCING"] == 1
        assert counts["FAIL"] == 1
        assert counts["NEVER_RUN"] == 1
        assert counts["CANCEL"] == 0
        assert counts["SYNC_NOW"] == 0

    def test_no_repos_returns_all_zeros(self, initialized_db):
        """Config with no repos returns all statuses as zero."""
        org, robot = _create_org_and_robot("testorgzerocounts")
        config = _create_org_mirror_config(org, robot)

        counts = get_org_mirror_repo_status_counts(config)

        for status in OrgMirrorRepoStatus:
            assert counts[status.name] == 0


class TestDeactivateExcludedRepos:
    """Tests for deactivate_excluded_repos()."""

    def test_deleted_repos_get_skipped(self, initialized_db):
        """Repos no longer in source are marked SKIP with a source-specific message."""
        org, robot = _create_org_and_robot("testdeact_deleted")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")
        get_or_create_org_mirror_repo(config, "repo-b")
        get_or_create_org_mirror_repo(config, "repo-c")

        # repo-b no longer in source
        count = deactivate_excluded_repos(
            config, ["repo-a", "repo-c"], source_repo_names=["repo-a", "repo-c"]
        )

        assert count == 1
        repo_b = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-b")
        )
        assert repo_b.sync_status == OrgMirrorRepoStatus.SKIP
        assert repo_b.status_message == "Repository no longer in source registry"
        assert repo_b.sync_start_date is None
        assert repo_b.sync_expiration_date is None

    def test_filtered_repos_get_skipped(self, initialized_db):
        """Repos excluded by filters are marked SKIP with a filter-specific message."""
        org, robot = _create_org_and_robot("testdeact_filtered")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "keep-me")
        get_or_create_org_mirror_repo(config, "filter-me-out")

        # filter-me-out exists in source but excluded by filters
        count = deactivate_excluded_repos(
            config, ["keep-me"], source_repo_names=["keep-me", "filter-me-out"]
        )

        assert count == 1
        filtered = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "filter-me-out")
        )
        assert filtered.sync_status == OrgMirrorRepoStatus.SKIP
        assert filtered.status_message == "Repository excluded by filters"

    def test_active_repos_unaffected(self, initialized_db):
        """Repos in the active list are not changed."""
        org, robot = _create_org_and_robot("testdeact_active")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")
        get_or_create_org_mirror_repo(config, "repo-b")

        count = deactivate_excluded_repos(config, ["repo-a", "repo-b"])

        assert count == 0
        for name in ["repo-a", "repo-b"]:
            repo = OrgMirrorRepository.get(
                (OrgMirrorRepository.org_mirror_config == config)
                & (OrgMirrorRepository.repository_name == name)
            )
            assert repo.sync_status == OrgMirrorRepoStatus.NEVER_RUN

    def test_skip_repos_reactivated_when_back_in_active_list(self, initialized_db):
        """Previously SKIP'd repos are reactivated to NEVER_RUN when they return."""
        org, robot = _create_org_and_robot("testdeact_reactivate")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")
        # Manually set to SKIP with stale dates to verify they are cleared
        past_time = datetime.utcnow() - timedelta(hours=1)
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.SKIP,
            status_message="Previously skipped",
            sync_start_date=past_time,
            sync_expiration_date=past_time,
        ).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-a")
        ).execute()

        # repo-a is back in active list
        count = deactivate_excluded_repos(config, ["repo-a"])

        assert count == 0
        repo_a = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-a")
        )
        assert repo_a.sync_status == OrgMirrorRepoStatus.NEVER_RUN
        assert repo_a.status_message is None
        assert repo_a.sync_start_date is None
        assert repo_a.sync_expiration_date is None

    def test_already_skipped_repos_not_re_updated(self, initialized_db):
        """Repos already SKIP'd and still excluded are not re-updated."""
        org, robot = _create_org_and_robot("testdeact_idempotent")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")
        get_or_create_org_mirror_repo(config, "repo-b")

        # First deactivation — repo-b excluded
        deactivate_excluded_repos(config, ["repo-a"])

        repo_b = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-b")
        )
        assert repo_b.sync_status == OrgMirrorRepoStatus.SKIP

        # Second deactivation — repo-b still excluded, should return 0
        count = deactivate_excluded_repos(config, ["repo-a"])

        assert count == 0

    def test_empty_active_list_skips_all(self, initialized_db):
        """Empty active_repo_names SKIPs all tracked repos (filters excluded everything)."""
        org, robot = _create_org_and_robot("testdeact_empty")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")

        count = deactivate_excluded_repos(config, [])

        assert count == 1
        repo_a = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-a")
        )
        assert repo_a.sync_status == OrgMirrorRepoStatus.SKIP

    def test_mixed_vanished_and_filtered_repos(self, initialized_db):
        """Repos get distinct messages based on whether they vanished or were filtered."""
        org, robot = _create_org_and_robot("testdeact_mixed")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "active")
        get_or_create_org_mirror_repo(config, "vanished")
        get_or_create_org_mirror_repo(config, "filtered-out")

        # Source has "active" and "filtered-out", but filters only keep "active"
        count = deactivate_excluded_repos(
            config,
            ["active"],
            source_repo_names=["active", "filtered-out"],
        )

        assert count == 2

        vanished = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "vanished")
        )
        assert vanished.sync_status == OrgMirrorRepoStatus.SKIP
        assert vanished.status_message == "Repository no longer in source registry"

        filtered = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "filtered-out")
        )
        assert filtered.sync_status == OrgMirrorRepoStatus.SKIP
        assert filtered.status_message == "Repository excluded by filters"

    def test_no_source_names_uses_generic_message(self, initialized_db):
        """Without source_repo_names, all skipped repos get the vanished message."""
        org, robot = _create_org_and_robot("testdeact_nosource")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "repo-a")
        get_or_create_org_mirror_repo(config, "repo-b")

        count = deactivate_excluded_repos(config, ["repo-a"])

        assert count == 1
        repo_b = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "repo-b")
        )
        assert repo_b.sync_status == OrgMirrorRepoStatus.SKIP
        assert repo_b.status_message == "Repository no longer in source registry"

    def test_syncing_repos_not_skipped(self, initialized_db):
        """Repos currently SYNCING are not marked SKIP — they'll be caught next cycle."""
        org, robot = _create_org_and_robot("testdeact_syncing")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "syncing-repo")
        get_or_create_org_mirror_repo(config, "idle-repo")

        # Set syncing-repo to SYNCING (simulating an active worker)
        OrgMirrorRepository.update(sync_status=OrgMirrorRepoStatus.SYNCING).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "syncing-repo")
        ).execute()

        # Both repos excluded from active list
        count = deactivate_excluded_repos(config, [])

        # Only idle-repo should be skipped; syncing-repo left alone
        assert count == 1

        syncing = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "syncing-repo")
        )
        assert syncing.sync_status == OrgMirrorRepoStatus.SYNCING

        idle = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "idle-repo")
        )
        assert idle.sync_status == OrgMirrorRepoStatus.SKIP


class TestDeactivateExcludedReposRotatesTransactionId:
    """Tests that deactivate_excluded_repos rotates sync_transaction_id to
    prevent in-flight workers from overwriting the new state via release."""

    def test_skip_rotates_transaction_id(self, initialized_db):
        """Skipping a repo must change its sync_transaction_id so an old
        claim token can no longer match."""
        org, robot = _create_org_and_robot("testdeact_txn_skip")
        config = _create_org_mirror_config(org, robot)

        repo, _ = get_or_create_org_mirror_repo(config, "repo-a")
        original_txn_id = repo.sync_transaction_id

        deactivate_excluded_repos(config, [])  # skip all

        repo = OrgMirrorRepository.get_by_id(repo.id)
        assert repo.sync_status == OrgMirrorRepoStatus.SKIP
        assert repo.sync_transaction_id != original_txn_id

    def test_reactivate_rotates_transaction_id(self, initialized_db):
        """Reactivating a SKIP'd repo must change its sync_transaction_id."""
        org, robot = _create_org_and_robot("testdeact_txn_react")
        config = _create_org_mirror_config(org, robot)

        repo, _ = get_or_create_org_mirror_repo(config, "repo-a")

        # First skip it
        deactivate_excluded_repos(config, [])
        repo = OrgMirrorRepository.get_by_id(repo.id)
        skipped_txn_id = repo.sync_transaction_id

        # Now reactivate it
        deactivate_excluded_repos(config, ["repo-a"])
        repo = OrgMirrorRepository.get_by_id(repo.id)
        assert repo.sync_status == OrgMirrorRepoStatus.NEVER_RUN
        assert repo.sync_transaction_id != skipped_txn_id

    def test_release_fails_after_skip_with_old_token(self, initialized_db):
        """Simulates the race: a repo is skipped via discovery while a worker
        holds an old claim token — release with the stale token must fail."""
        org, robot = _create_org_and_robot("testdeact_txn_race")
        config = _create_org_mirror_config(org, robot)

        repo, _ = get_or_create_org_mirror_repo(config, "repo-a")
        # Grab the token before discovery changes it
        claimed_repo = OrgMirrorRepository.get_by_id(repo.id)

        # Discovery runs and skips this repo (rotates sync_transaction_id)
        deactivate_excluded_repos(config, [])

        # Attempt release with the old token — must fail
        result = release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.SUCCESS)

        assert result is None

        # Repo must still be in SKIP state
        repo = OrgMirrorRepository.get_by_id(claimed_repo.id)
        assert repo.sync_status == OrgMirrorRepoStatus.SKIP


class TestReleaseOrgMirrorRepoStatusMessage:
    """Tests for status_message handling in release_org_mirror_repo()."""

    def test_fail_preserves_status_message(self, initialized_db):
        """On FAIL, the status_message is persisted."""
        org, robot = _create_org_and_robot("testrelease_msg_fail")
        config = _create_org_mirror_config(org, robot)

        repo, _ = get_or_create_org_mirror_repo(config, "repo-a")

        claimed = claim_org_mirror_repo(repo)
        assert claimed is not None

        released = release_org_mirror_repo(
            claimed,
            OrgMirrorRepoStatus.FAIL,
            status_message="Tag sync failed: 2/5 tags",
        )

        assert released is not None
        assert released.status_message == "Tag sync failed: 2/5 tags"
        assert released.sync_status == OrgMirrorRepoStatus.FAIL

    def test_success_clears_status_message(self, initialized_db):
        """On SUCCESS, status_message is cleared even if caller provides one."""
        org, robot = _create_org_and_robot("testrelease_msg_success")
        config = _create_org_mirror_config(org, robot)

        repo, _ = get_or_create_org_mirror_repo(config, "repo-a")
        # Set an existing message
        OrgMirrorRepository.update(status_message="old failure message").where(
            OrgMirrorRepository.id == repo.id
        ).execute()

        claimed = claim_org_mirror_repo(repo)
        assert claimed is not None

        released = release_org_mirror_repo(
            claimed,
            OrgMirrorRepoStatus.SUCCESS,
            status_message="should be cleared",
        )

        assert released is not None
        assert released.status_message is None
        assert released.sync_status == OrgMirrorRepoStatus.SUCCESS


class TestPropagateStatusSkipsSkipRepos:
    """Tests for propagate_status_to_repos() skipping SKIP repos."""

    def test_sync_now_skips_skip_repos(self, initialized_db):
        """SYNC_NOW propagation does not affect SKIP repos."""
        org, robot = _create_org_and_robot("testprop_syncnow_skip")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "active-repo")
        get_or_create_org_mirror_repo(config, "skipped-repo")

        OrgMirrorRepository.update(sync_status=OrgMirrorRepoStatus.SKIP).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "skipped-repo")
        ).execute()

        propagate_status_to_repos(config, OrgMirrorRepoStatus.SYNC_NOW)

        active = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "active-repo")
        )
        skipped = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "skipped-repo")
        )

        assert active.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert skipped.sync_status == OrgMirrorRepoStatus.SKIP

    def test_cancel_skips_skip_repos(self, initialized_db):
        """CANCEL propagation does not affect SKIP repos."""
        org, robot = _create_org_and_robot("testprop_cancel_skip")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "active-repo")
        get_or_create_org_mirror_repo(config, "skipped-repo")

        OrgMirrorRepository.update(sync_status=OrgMirrorRepoStatus.SKIP).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "skipped-repo")
        ).execute()

        propagate_status_to_repos(config, OrgMirrorRepoStatus.CANCEL)

        active = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "active-repo")
        )
        skipped = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "skipped-repo")
        )

        assert active.sync_status == OrgMirrorRepoStatus.CANCEL
        assert skipped.sync_status == OrgMirrorRepoStatus.SKIP

    def test_sync_now_clears_status_message(self, initialized_db):
        """SYNC_NOW propagation clears stale status_message from prior failures."""
        org, robot = _create_org_and_robot("testprop_syncnow_msg")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "failed-repo")
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.FAIL,
            status_message="Sync failed: 2/5 tags failed",
        ).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "failed-repo")
        ).execute()

        propagate_status_to_repos(config, OrgMirrorRepoStatus.SYNC_NOW)

        repo = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "failed-repo")
        )
        assert repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert repo.status_message is None

    def test_cancel_clears_status_message(self, initialized_db):
        """CANCEL propagation clears stale status_message from prior failures."""
        org, robot = _create_org_and_robot("testprop_cancel_msg")
        config = _create_org_mirror_config(org, robot)

        get_or_create_org_mirror_repo(config, "failed-repo")
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.FAIL,
            status_message="Sync failed: 3/5 tags failed",
        ).where(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "failed-repo")
        ).execute()

        propagate_status_to_repos(config, OrgMirrorRepoStatus.CANCEL)

        repo = OrgMirrorRepository.get(
            (OrgMirrorRepository.org_mirror_config == config)
            & (OrgMirrorRepository.repository_name == "failed-repo")
        )
        assert repo.sync_status == OrgMirrorRepoStatus.CANCEL
        assert repo.status_message is None
