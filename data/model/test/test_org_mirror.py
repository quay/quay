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
    create_org_mirror_config,
    delete_org_mirror_config,
    get_org_mirror_config,
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
