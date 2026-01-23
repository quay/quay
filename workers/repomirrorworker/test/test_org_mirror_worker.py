# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror worker functions.

Tests cover the org-level mirroring functions in workers/repomirrorworker/__init__.py
"""

from datetime import datetime, timedelta
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

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
from data.model.user import create_robot, create_user_noverify, lookup_robot
from test.fixtures import *
from util.repomirror.skopeomirror import SkopeoResults
from workers.repomirrorworker import (
    _build_external_reference,
    _ensure_local_repository,
    emit_org_mirror_log,
    perform_org_mirror_discovery,
    perform_org_mirror_repo,
    process_org_mirror_discovery,
    process_org_mirrors,
)


def disable_existing_org_mirrors(func):
    """Decorator to disable existing org mirrors during test."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        for config in OrgMirrorConfig.select():
            config.is_enabled = False
            config.save()

        func(*args, **kwargs)

        for config in OrgMirrorConfig.select():
            config.is_enabled = True
            config.save()

    return wrapper


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


class TestBuildExternalReference:
    """Tests for _build_external_reference function."""

    def test_https_url_stripped(self, initialized_db):
        """HTTPS prefix should be removed from URL."""
        org, robot = _create_org_and_robot("ext_ref_test1")
        config = _create_org_mirror_config(org, robot)

        result = _build_external_reference(config, "my-repo")

        assert result == "registry.example.com/source-namespace/my-repo"

    def test_http_url_stripped(self, initialized_db):
        """HTTP prefix should be removed from URL."""
        org, robot = _create_org_and_robot("ext_ref_test2")
        config = _create_org_mirror_config(org, robot)
        config.external_registry_url = "http://registry.example.com"
        config.save()

        result = _build_external_reference(config, "my-repo")

        assert result == "registry.example.com/source-namespace/my-repo"

    def test_no_protocol_url(self, initialized_db):
        """URL without protocol should work correctly."""
        org, robot = _create_org_and_robot("ext_ref_test3")
        config = _create_org_mirror_config(org, robot)
        config.external_registry_url = "registry.example.com"
        config.save()

        result = _build_external_reference(config, "my-repo")

        assert result == "registry.example.com/source-namespace/my-repo"

    def test_trailing_slash_removed(self, initialized_db):
        """Trailing slash in URL should be handled."""
        org, robot = _create_org_and_robot("ext_ref_test4")
        config = _create_org_mirror_config(org, robot)
        config.external_registry_url = "https://registry.example.com/"
        config.save()

        result = _build_external_reference(config, "my-repo")

        assert result == "registry.example.com/source-namespace/my-repo"

    def test_repository_with_slashes(self, initialized_db):
        """Repository names with slashes should be preserved."""
        org, robot = _create_org_and_robot("ext_ref_test5")
        config = _create_org_mirror_config(org, robot)

        result = _build_external_reference(config, "subdir/my-repo")

        assert result == "registry.example.com/source-namespace/subdir/my-repo"


class TestEnsureLocalRepository:
    """Tests for _ensure_local_repository function."""

    def test_returns_existing_linked_repo(self, initialized_db):
        """If repo is already linked, return it directly."""
        org, robot = _create_org_and_robot("ensure_repo_test1")
        config = _create_org_mirror_config(org, robot)

        # Create a repository and link it
        from data.model import repository as repository_model

        existing_repo = repository_model.create_repository(
            org.username, "linked-repo", robot, visibility="private"
        )
        repo_db = Repository.get(Repository.id == existing_repo.id)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="linked-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            repository=repo_db,
        )

        result = _ensure_local_repository(config, org_mirror_repo)

        assert result is not None
        assert result.id == repo_db.id

    def test_links_existing_unlinked_repo(self, initialized_db):
        """If repo exists but not linked, link it and return."""
        org, robot = _create_org_and_robot("ensure_repo_test2")
        config = _create_org_mirror_config(org, robot)

        # Create a repository but don't link it
        from data.model import repository as repository_model

        existing_repo = repository_model.create_repository(
            org.username, "unlinked-repo", robot, visibility="private"
        )

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="unlinked-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result = _ensure_local_repository(config, org_mirror_repo)

        assert result is not None
        # Refresh from DB
        org_mirror_repo = OrgMirrorRepository.get_by_id(org_mirror_repo.id)
        assert org_mirror_repo.repository is not None
        assert org_mirror_repo.repository.id == result.id

    def test_creates_new_repo(self, initialized_db):
        """If repo doesn't exist, create it with ORG_MIRROR state."""
        org, robot = _create_org_and_robot("ensure_repo_test3")
        config = _create_org_mirror_config(org, robot)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="new-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result = _ensure_local_repository(config, org_mirror_repo)

        assert result is not None
        assert result.name == "new-repo"
        assert result.state == RepositoryState.ORG_MIRROR
        # Verify link was created
        org_mirror_repo = OrgMirrorRepository.get_by_id(org_mirror_repo.id)
        assert org_mirror_repo.repository is not None


class TestEmitOrgMirrorLog:
    """Tests for emit_org_mirror_log function."""

    @patch("workers.repomirrorworker.logs_model")
    def test_emits_log_with_all_fields(self, mock_logs_model, initialized_db):
        """Should emit log with all metadata fields."""
        org, robot = _create_org_and_robot("emit_log_test1")
        config = _create_org_mirror_config(org, robot)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="test-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        emit_org_mirror_log(
            config,
            org_mirror_repo,
            "org_mirror_sync_started",
            "start",
            "Test message",
            tag="v1.0",
            tags="v1.0, v2.0",
            stdout="output",
            stderr="errors",
        )

        mock_logs_model.log_action.assert_called_once()
        call_args = mock_logs_model.log_action.call_args
        assert call_args[0][0] == "org_mirror_sync_started"
        assert call_args[1]["namespace_name"] == org.username
        assert call_args[1]["repository_name"] == "test-repo"
        metadata = call_args[1]["metadata"]
        assert metadata["verb"] == "start"
        assert metadata["message"] == "Test message"
        assert metadata["tag"] == "v1.0"
        assert metadata["tags"] == "v1.0, v2.0"
        assert metadata["stdout"] == "output"
        assert metadata["stderr"] == "errors"


class TestProcessOrgMirrorDiscovery:
    """Tests for process_org_mirror_discovery function."""

    @patch("workers.repomirrorworker.features")
    def test_disabled_feature_returns_none(self, mock_features, initialized_db):
        """When ORG_MIRROR feature is disabled, return None."""
        mock_features.ORG_MIRROR = False

        result = process_org_mirror_discovery()

        assert result is None

    @patch("workers.repomirrorworker.features")
    @patch("workers.repomirrorworker.org_mirror_model")
    def test_no_configs_returns_token(self, mock_model, mock_features, initialized_db):
        """When no configs to discover, return next_token."""
        mock_features.ORG_MIRROR = True
        mock_model.configs_to_discover.return_value = (None, None)

        result = process_org_mirror_discovery()

        assert result is None


class TestProcessOrgMirrors:
    """Tests for process_org_mirrors function."""

    @patch("workers.repomirrorworker.features")
    def test_disabled_feature_returns_none(self, mock_features, initialized_db):
        """When ORG_MIRROR feature is disabled, return None."""
        mock_features.ORG_MIRROR = False
        mock_skopeo = Mock()

        result = process_org_mirrors(mock_skopeo)

        assert result is None

    @patch("workers.repomirrorworker.features")
    @patch("workers.repomirrorworker.org_mirror_model")
    def test_no_repos_returns_token(self, mock_model, mock_features, initialized_db):
        """When no repos to mirror, return next_token."""
        mock_features.ORG_MIRROR = True
        mock_model.repositories_to_mirror.return_value = (None, None)
        mock_skopeo = Mock()

        result = process_org_mirrors(mock_skopeo)

        assert result is None


class TestPerformOrgMirrorDiscovery:
    """Tests for perform_org_mirror_discovery function."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_successful_discovery(self, mock_logs, mock_get_adapter, initialized_db):
        """Test successful repository discovery."""
        org, robot = _create_org_and_robot("discovery_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set sync_start_date to the past so it's eligible
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["repo1", "repo2", "repo3"]
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify repos were created
        repos = list(
            OrgMirrorRepository.select().where(OrgMirrorRepository.org_mirror_config == config)
        )
        assert len(repos) == 3
        repo_names = {r.repository_name for r in repos}
        assert repo_names == {"repo1", "repo2", "repo3"}

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_with_filters(self, mock_logs, mock_get_adapter, initialized_db):
        """Test discovery with repository filters applied."""
        org, robot = _create_org_and_robot("discovery_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Set filter to only include repos starting with "app"
        config.repository_filters = ["app*"]
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["app-web", "app-api", "database", "cache"]
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify only filtered repos were created
        repos = list(
            OrgMirrorRepository.select().where(OrgMirrorRepository.org_mirror_config == config)
        )
        assert len(repos) == 2
        repo_names = {r.repository_name for r in repos}
        assert repo_names == {"app-web", "app-api"}


class TestPerformOrgMirrorRepo:
    """Tests for perform_org_mirror_repo function."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_successful_sync(self, mock_token, mock_logs, initialized_db, app):
        """Test successful repository sync."""
        org, robot = _create_org_and_robot("sync_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="sync-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0", "v2.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.SUCCESS

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_sync_no_tags(self, mock_token, mock_logs, initialized_db, app):
        """Test sync when no tags exist in source repo."""
        org, robot = _create_org_and_robot("sync_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="empty-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo to return no tags
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, [], "", "")
        mock_token.return_value = "robot_token"

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.SUCCESS

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_sync_partial_failure(self, mock_token, mock_logs, initialized_db, app):
        """Test sync when some tags fail to copy."""
        org, robot = _create_org_and_robot("sync_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="partial-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0", "v2.0"], "", "")

        # First copy succeeds, second fails
        mock_skopeo.copy.side_effect = [
            SkopeoResults(True, [], "copied", ""),
            SkopeoResults(False, [], "", "copy failed"),
        ]
        mock_token.return_value = "robot_token"

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL
