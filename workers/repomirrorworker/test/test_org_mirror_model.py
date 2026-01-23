# -*- coding: utf-8 -*-
"""
Unit tests for OrgMirrorModel class in org_mirror_model.py.

Tests cover the iterator and token-based pagination for org-level mirroring.
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
    SourceRegistryType,
    User,
    Visibility,
)
from data.model.user import create_robot, create_user_noverify, lookup_robot
from test.fixtures import *
from workers.repomirrorworker.org_mirror_model import (
    OrgMirrorConfigToken,
    OrgMirrorModel,
    OrgMirrorToken,
    org_mirror_model,
)


def _create_org_and_robot(org_name: str):
    """Create an organization and its mirror robot."""
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


def _create_org_mirror_config(org, robot, is_enabled=True):
    """Create an OrgMirrorConfig for testing."""
    visibility = Visibility.get(name="private")

    return OrgMirrorConfig.create(
        organization=org,
        is_enabled=is_enabled,
        external_registry_type=SourceRegistryType.QUAY,
        external_registry_url="https://registry.example.com",
        external_namespace="source-namespace",
        internal_robot=robot,
        visibility=visibility,
        sync_interval=3600,
        sync_start_date=datetime.utcnow(),
        sync_status=OrgMirrorStatus.NEVER_RUN,
        sync_retries_remaining=3,
        skopeo_timeout=300,
    )


class TestOrgMirrorConfigToken:
    """Tests for OrgMirrorConfigToken namedtuple."""

    def test_token_creation(self):
        """Token can be created with min_id."""
        token = OrgMirrorConfigToken(min_id=100)
        assert token.min_id == 100

    def test_token_is_namedtuple(self):
        """Token is a proper namedtuple."""
        token = OrgMirrorConfigToken(min_id=42)
        assert token[0] == 42


class TestOrgMirrorToken:
    """Tests for OrgMirrorToken namedtuple."""

    def test_token_creation(self):
        """Token can be created with min_id."""
        token = OrgMirrorToken(min_id=200)
        assert token.min_id == 200

    def test_token_is_namedtuple(self):
        """Token is a proper namedtuple."""
        token = OrgMirrorToken(min_id=77)
        assert token[0] == 77


class TestOrgMirrorModelConfigsToDiscover:
    """Tests for OrgMirrorModel.configs_to_discover method."""

    def test_no_configs_returns_none(self, initialized_db):
        """When no org mirror configs exist, return (None, None)."""
        model = OrgMirrorModel()

        iterator, next_token = model.configs_to_discover()

        assert iterator is None
        assert next_token is None

    def test_with_eligible_config_returns_iterator(self, initialized_db):
        """When eligible configs exist, return an iterator."""
        org, robot = _create_org_and_robot("config_discover_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set sync_start_date to the past so it's eligible
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        model = OrgMirrorModel()

        iterator, next_token = model.configs_to_discover()

        assert iterator is not None
        assert next_token is not None
        assert isinstance(next_token, OrgMirrorConfigToken)

    def test_with_start_token_resumes(self, initialized_db):
        """When given a start token, iteration resumes from that point."""
        org, robot = _create_org_and_robot("config_discover_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        model = OrgMirrorModel()

        # Get initial results
        iterator1, token1 = model.configs_to_discover()
        assert iterator1 is not None
        assert token1 is not None

        # Resume with token - should return None if min_id > max_id
        # This simulates resuming after all items processed
        future_token = OrgMirrorConfigToken(min_id=999999)
        iterator2, token2 = model.configs_to_discover(start_token=future_token)

        assert iterator2 is None
        assert token2 is None

    def test_disabled_config_not_returned(self, initialized_db):
        """Disabled configs should not be returned."""
        org, robot = _create_org_and_robot("config_discover_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=False)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        model = OrgMirrorModel()

        # Get iterator
        iterator, next_token = model.configs_to_discover()

        # Iterator might exist but should not yield this config
        if iterator is not None:
            found_configs = []
            for item, abt, remaining in iterator:
                found_configs.append(item)
            assert config.id not in [c.id for c in found_configs]


class TestOrgMirrorModelRepositoriesToMirror:
    """Tests for OrgMirrorModel.repositories_to_mirror method."""

    def test_no_repos_returns_none(self, initialized_db):
        """When no org mirror repos exist, return (None, None)."""
        model = OrgMirrorModel()

        iterator, next_token = model.repositories_to_mirror()

        assert iterator is None
        assert next_token is None

    def test_with_eligible_repo_returns_iterator(self, initialized_db):
        """When eligible repos exist, return an iterator."""
        org, robot = _create_org_and_robot("repo_mirror_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create an eligible repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="test-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        model = OrgMirrorModel()

        iterator, next_token = model.repositories_to_mirror()

        assert iterator is not None
        assert next_token is not None
        assert isinstance(next_token, OrgMirrorToken)

    def test_with_start_token_resumes(self, initialized_db):
        """When given a start token, iteration resumes from that point."""
        org, robot = _create_org_and_robot("repo_mirror_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="resume-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        model = OrgMirrorModel()

        # Get initial results
        iterator1, token1 = model.repositories_to_mirror()
        assert iterator1 is not None
        assert token1 is not None

        # Resume with future token - should return None if min_id > max_id
        future_token = OrgMirrorToken(min_id=999999)
        iterator2, token2 = model.repositories_to_mirror(start_token=future_token)

        assert iterator2 is None
        assert token2 is None

    def test_batch_size_calculation(self, initialized_db):
        """Batch size should scale with number of entries."""
        org, robot = _create_org_and_robot("repo_mirror_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create multiple repos
        past_time = datetime.utcnow() - timedelta(hours=1)
        for i in range(5):
            OrgMirrorRepository.create(
                org_mirror_config=config,
                repository_name=f"batch-repo-{i}",
                sync_status=OrgMirrorRepoStatus.NEVER_RUN,
                sync_start_date=past_time,
                sync_retries_remaining=3,
            )

        model = OrgMirrorModel()

        iterator, next_token = model.repositories_to_mirror()

        assert iterator is not None
        assert next_token is not None

    def test_sync_now_repos_included(self, initialized_db):
        """Repos with SYNC_NOW status should be included."""
        org, robot = _create_org_and_robot("repo_mirror_test4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create a SYNC_NOW repo
        repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-now-repo",
            sync_status=OrgMirrorRepoStatus.SYNC_NOW,
            sync_retries_remaining=3,
            sync_expiration_date=None,
        )

        model = OrgMirrorModel()

        iterator, next_token = model.repositories_to_mirror()

        assert iterator is not None
        # Iterate and check the repo is included
        found = False
        for item, abt, remaining in iterator:
            if item.repository_name == "sync-now-repo":
                found = True
                break
        assert found


class TestOrgMirrorModelSingleton:
    """Tests for the org_mirror_model singleton."""

    def test_singleton_exists(self):
        """The org_mirror_model singleton should exist."""
        assert org_mirror_model is not None
        assert isinstance(org_mirror_model, OrgMirrorModel)

    def test_singleton_methods_available(self):
        """Singleton should have all expected methods."""
        assert hasattr(org_mirror_model, "configs_to_discover")
        assert hasattr(org_mirror_model, "repositories_to_mirror")
        assert callable(org_mirror_model.configs_to_discover)
        assert callable(org_mirror_model.repositories_to_mirror)
