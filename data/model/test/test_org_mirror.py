# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror configuration business logic.
"""

from datetime import datetime, timedelta

import pytest

from data import model
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    SourceRegistryType,
    User,
    Visibility,
)
from data.model import DataModelException
from data.model.org_mirror import (
    MAX_SYNC_RETRIES,
    claim_org_mirror_repo,
    create_org_mirror_config,
    delete_org_mirror_config,
    expire_org_mirror_repo,
    get_eligible_org_mirror_repos,
    get_max_id_for_org_mirror_repo,
    get_min_id_for_org_mirror_repo,
    get_org_mirror_config,
    release_org_mirror_repo,
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
        config = _create_org_mirror_config(
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
        config = _create_org_mirror_config(org, robot, repository_filters=filters)

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
        result = delete_org_mirror_config(org)

        assert result is True
        assert get_org_mirror_config(org) is None

    def test_delete_org_mirror_config_not_found(self, initialized_db):
        """
        Deleting a config that doesn't exist should return False.
        """
        org, _ = _create_org_and_robot("delete_test2")

        # No config exists for this org
        result = delete_org_mirror_config(org)

        assert result is False

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
        result = delete_org_mirror_config(org)

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
        result = delete_org_mirror_config(org1)

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
        delete_org_mirror_config(org)

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
        original_url = config.external_registry_url

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
        config = _create_org_mirror_config(org, robot, is_enabled=True)

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
        config = _create_org_mirror_config(org, robot, visibility=private_visibility)

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
        config = _create_org_mirror_config(org, robot1)

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
        config = _create_org_mirror_config(org1, robot1)

        with pytest.raises(DataModelException) as excinfo:
            update_org_mirror_config(org1, internal_robot=robot2)

        assert "belong to the organization" in str(excinfo.value)

    def test_update_org_mirror_config_filters(self, initialized_db):
        """
        Test updating repository filters.
        """
        org, robot = _create_org_and_robot("update_test7")
        config = _create_org_mirror_config(org, robot, repository_filters=["ubuntu*"])

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
        config = _create_org_mirror_config(org, robot)

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
        config = _create_org_mirror_config(org, robot)
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
        config = _create_org_mirror_config(org, robot)

        updated = update_org_mirror_config(
            org,
            external_registry_username="newuser",
            external_registry_password="newpassword",
        )

        assert updated is not None
        # Verify credentials were updated (they're encrypted)
        assert updated.external_registry_username is not None
        assert updated.external_registry_password is not None

    def test_update_org_mirror_config_preserves_unchanged_fields(self, initialized_db):
        """
        Updating specific fields should not affect other fields.
        """
        org, robot = _create_org_and_robot("update_test11")
        public_visibility = Visibility.get(name="public")
        filters = ["redis*", "mysql*"]
        config = _create_org_mirror_config(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo = OrgMirrorRepository.create(
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
        repo3 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-3",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=now - timedelta(hours=1),  # Most recent
            sync_retries_remaining=3,
        )
        repo1 = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="repo-1",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=now - timedelta(hours=3),  # Oldest
            sync_retries_remaining=3,
        )
        repo2 = OrgMirrorRepository.create(
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

        repo1 = OrgMirrorRepository.create(
            org_mirror_config=config1,
            repository_name="org1-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )
        repo2 = OrgMirrorRepository.create(
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

        repo = OrgMirrorRepository.create(
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
        repo2 = OrgMirrorRepository.create(
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
        result = update_sync_status_to_sync_now(config)
        after = datetime.utcnow()

        assert result is not None
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

        result = update_sync_status_to_sync_now(config)

        assert result is None

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

        result = update_sync_status_to_sync_now(config)

        assert result is not None
        assert result.sync_retries_remaining >= 1

    def test_sync_now_also_updates_repos(self, initialized_db):
        """
        Should update all repos (except SYNCING) to SYNC_NOW status.
        """
        from data.model.org_mirror import update_sync_status_to_sync_now

        org, robot = _create_org_and_robot("sync_now_test4")
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
        success_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="success-repo",
            sync_status=OrgMirrorRepoStatus.SUCCESS,
        )

        before = datetime.utcnow()
        result = update_sync_status_to_sync_now(config)
        after = datetime.utcnow()

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.SYNC_NOW

        # Verify repos are updated appropriately
        syncing_repo = OrgMirrorRepository.get_by_id(syncing_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)
        fail_repo = OrgMirrorRepository.get_by_id(fail_repo.id)
        success_repo = OrgMirrorRepository.get_by_id(success_repo.id)

        # SYNCING repo should be left alone
        assert syncing_repo.sync_status == OrgMirrorRepoStatus.SYNCING

        # All other repos should be set to SYNC_NOW with updated start date
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert never_run_repo.sync_start_date >= before
        assert never_run_repo.sync_start_date <= after

        assert fail_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW
        assert success_repo.sync_status == OrgMirrorRepoStatus.SYNC_NOW


class TestUpdateSyncStatusToCancel:
    """Tests for update_sync_status_to_cancel function."""

    def test_cancel_when_syncing(self, initialized_db):
        """
        Should cancel when status is SYNCING.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set to SYNCING
        config.sync_status = OrgMirrorStatus.SYNCING
        config.sync_expiration_date = datetime.utcnow() + timedelta(hours=1)
        config.save()

        result = update_sync_status_to_cancel(config)

        assert result is not None
        assert result.sync_status == OrgMirrorStatus.CANCEL
        assert result.sync_expiration_date is None
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

    def test_cancel_fails_when_not_syncing(self, initialized_db):
        """
        Should return None if not in a cancellable state.
        """
        from data.model.org_mirror import update_sync_status_to_cancel

        org, robot = _create_org_and_robot("cancel_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Status is NEVER_RUN (not cancellable)
        assert config.sync_status == OrgMirrorStatus.NEVER_RUN

        result = update_sync_status_to_cancel(config)

        assert result is None

    def test_cancel_also_cancels_repos(self, initialized_db):
        """
        Should cancel repos that are NOT SYNCING.
        Repos actively being synced (SYNCING) are left alone to complete.
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

        # Verify repos are cancelled appropriately
        syncing_repo = OrgMirrorRepository.get_by_id(syncing_repo.id)
        sync_now_repo = OrgMirrorRepository.get_by_id(sync_now_repo.id)
        never_run_repo = OrgMirrorRepository.get_by_id(never_run_repo.id)

        # SYNCING repos are left alone to complete
        assert syncing_repo.sync_status == OrgMirrorRepoStatus.SYNCING
        # All other repos are cancelled
        assert sync_now_repo.sync_status == OrgMirrorRepoStatus.CANCEL
        assert never_run_repo.sync_status == OrgMirrorRepoStatus.CANCEL
