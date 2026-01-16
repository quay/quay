# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror configuration business logic.
"""

from datetime import datetime, timedelta

import pytest

from data import model
from data.database import (
    OrgMirrorConfig,
    OrgMirrorStatus,
    SourceRegistryType,
    User,
    Visibility,
)
from data.model import DataModelException
from data.model.org_mirror import create_org_mirror_config, get_org_mirror_config
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

        config1 = _create_org_mirror_config(
            org1, robot1, external_namespace="project-a"
        )
        config2 = _create_org_mirror_config(
            org2, robot2, external_namespace="project-b"
        )

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
        registry_config = {"verify_tls": True, "proxy": {"https_proxy": "https://proxy.example.com"}}

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
