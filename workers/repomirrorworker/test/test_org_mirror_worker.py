# -*- coding: utf-8 -*-
"""
Unit tests for organization-level mirror worker functions.

Tests cover the org-level mirroring functions in workers/repomirrorworker/__init__.py,
as well as manifest_utils.py and org_mirror_model.py.
"""

import json
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
from data.encryption import DecryptionFailureException
from data.model.user import create_robot, create_user_noverify, lookup_robot
from test.fixtures import *
from util.repomirror.skopeomirror import SkopeoResults
from workers.repomirrorworker import (
    PreemptedException,
    RepoMirrorSkopeoException,
    _build_external_reference,
    _ensure_local_repository,
    _get_all_tags_for_org_mirror,
    emit_org_mirror_log,
    org_mirror_discovery_total,
    org_mirror_repo_sync_total,
    org_mirror_repos_created_total,
    org_mirror_repos_discovered,
    perform_org_mirror_discovery,
    perform_org_mirror_repo,
    process_org_mirror_discovery,
    process_org_mirrors,
)
from workers.repomirrorworker.manifest_utils import (
    filter_manifests_by_architecture,
    get_available_architectures,
    get_manifest_media_type,
    is_manifest_list,
)
from workers.repomirrorworker.org_mirror_model import (
    OrgMirrorConfigToken,
    OrgMirrorModel,
    OrgMirrorToken,
)
from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker


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
    def test_successful_discovery(self, _mock_logs, mock_get_adapter, initialized_db):
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
    def test_discovery_with_filters(self, _mock_logs, mock_get_adapter, initialized_db):
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
    def test_successful_sync(self, mock_token, _mock_logs, initialized_db, app):
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
    def test_sync_no_tags(self, mock_token, _mock_logs, initialized_db, app):
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
    def test_sync_partial_failure(self, mock_token, _mock_logs, initialized_db, app):
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

    @disable_existing_org_mirrors
    @pytest.mark.usefixtures("initialized_db", "app")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    @patch("workers.repomirrorworker.check_org_mirror_repo_sync_status")
    def test_sync_cancelled_during_tag_loop(self, mock_check_status, mock_token, _mock_logs):
        """Test that sync is cancelled when cancel is detected during tag processing."""
        org, robot = _create_org_and_robot("sync_test_cancel1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo with 3 tags
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0", "v2.0", "v3.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        # First call returns SYNCING, second call returns CANCEL
        mock_check_status.side_effect = [
            OrgMirrorRepoStatus.SYNCING,
            OrgMirrorRepoStatus.CANCEL,
        ]

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.CANCEL
        # Should have only copied 2 tags before cancel was detected
        assert mock_skopeo.copy.call_count == 2

    @disable_existing_org_mirrors
    @pytest.mark.usefixtures("initialized_db", "app")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    @patch("workers.repomirrorworker.check_org_mirror_repo_sync_status")
    def test_cancel_emits_correct_log(self, mock_check_status, mock_token, mock_logs):
        """Test that correct log is emitted when sync is cancelled."""
        org, robot = _create_org_and_robot("sync_test_cancel2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-log-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0", "v2.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        # Cancel immediately after first tag
        mock_check_status.return_value = OrgMirrorRepoStatus.CANCEL

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.CANCEL

        # Verify the cancel log was emitted
        log_calls = [
            call
            for call in mock_logs.log_action.call_args_list
            if call[0][0] == "org_mirror_sync_cancelled"
        ]
        assert len(log_calls) == 1
        assert "cancelled" in log_calls[0][1]["metadata"]["message"].lower()

    @disable_existing_org_mirrors
    @pytest.mark.usefixtures("initialized_db", "app")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    @patch("workers.repomirrorworker.check_org_mirror_repo_sync_status")
    def test_cancel_stops_at_first_detection(self, mock_check_status, mock_token, _mock_logs):
        """Test that remaining tags are not processed after cancel detection."""
        org, robot = _create_org_and_robot("sync_test_cancel3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-remaining-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo with 5 tags
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(
            True, ["v1.0", "v2.0", "v3.0", "v4.0", "v5.0"], "", ""
        )
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        # Cancel after 3 tags (status check happens after each copy)
        mock_check_status.side_effect = [
            OrgMirrorRepoStatus.SYNCING,
            OrgMirrorRepoStatus.SYNCING,
            OrgMirrorRepoStatus.CANCEL,
        ]

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.CANCEL
        # Should have copied exactly 3 tags before stopping
        assert mock_skopeo.copy.call_count == 3

    @disable_existing_org_mirrors
    @pytest.mark.usefixtures("initialized_db", "app")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    @patch("workers.repomirrorworker.check_org_mirror_repo_sync_status")
    def test_cancel_releases_repo_with_cancel_status(
        self, mock_check_status, mock_token, _mock_logs
    ):
        """Test that repo is released with CANCEL status after cancellation."""
        org, robot = _create_org_and_robot("sync_test_cancel4")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        # Create org mirror repo
        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="cancel-release-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Mock skopeo
        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        # Cancel immediately
        mock_check_status.return_value = OrgMirrorRepoStatus.CANCEL

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.CANCEL

        # Verify the repo was released with CANCEL status
        # (release_org_mirror_repo sets sync_start_date to None for cancel)
        refreshed_repo = OrgMirrorRepository.get_by_id(org_mirror_repo.id)
        assert refreshed_repo.sync_status == OrgMirrorRepoStatus.CANCEL
        assert refreshed_repo.sync_start_date is None
        assert refreshed_repo.sync_retries_remaining == 0


class TestRepoCreatedAuditLogging:
    """Tests for org_mirror_repo_created and org_mirror_repo_creation_failed audit events."""

    @patch("workers.repomirrorworker.logs_model")
    def test_repo_created_emits_audit_event(self, mock_logs, initialized_db):
        """Test that creating a new repository emits org_mirror_repo_created audit event."""
        org, robot = _create_org_and_robot("audit_repo_test1")
        config = _create_org_mirror_config(org, robot)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="audit-new-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result = _ensure_local_repository(config, org_mirror_repo)

        # Verify repository was created
        assert result is not None
        assert result.name == "audit-new-repo"

        # Verify audit event was logged
        calls = mock_logs.log_action.call_args_list
        repo_created_calls = [c for c in calls if c[0][0] == "org_mirror_repo_created"]
        assert len(repo_created_calls) == 1

        call_args = repo_created_calls[0]
        assert call_args[1]["namespace_name"] == org.username
        assert call_args[1]["repository_name"] == "audit-new-repo"
        assert call_args[1]["performer"] == robot
        assert call_args[1]["ip"] is None
        metadata = call_args[1]["metadata"]
        assert "external_reference" in metadata
        assert metadata["visibility"] == "private"
        assert metadata["via_org_mirror"] is True

    @patch("workers.repomirrorworker.logs_model")
    def test_existing_repo_does_not_emit_created_event(self, mock_logs, initialized_db):
        """Test that linking an existing repository does not emit org_mirror_repo_created."""
        org, robot = _create_org_and_robot("audit_repo_test2")
        config = _create_org_mirror_config(org, robot)

        # Create a repository but don't link it
        from data.model import repository as repository_model

        repository_model.create_repository(
            org.username, "existing-repo", robot, visibility="private"
        )

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="existing-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        result = _ensure_local_repository(config, org_mirror_repo)

        # Verify repository was linked
        assert result is not None

        # Verify NO org_mirror_repo_created event was logged (repo already existed)
        calls = mock_logs.log_action.call_args_list
        repo_created_calls = [c for c in calls if c[0][0] == "org_mirror_repo_created"]
        assert len(repo_created_calls) == 0

    @patch("workers.repomirrorworker.logs_model")
    def test_already_linked_repo_does_not_emit_created_event(self, mock_logs, initialized_db):
        """Test that already linked repository does not emit org_mirror_repo_created."""
        org, robot = _create_org_and_robot("audit_repo_test3")
        config = _create_org_mirror_config(org, robot)

        # Create and link a repository
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

        # Verify repository was returned
        assert result is not None
        assert result.id == repo_db.id

        # Verify NO log_action was called at all
        assert mock_logs.log_action.call_count == 0

    @patch("workers.repomirrorworker.repository_model")
    @patch("workers.repomirrorworker.logs_model")
    def test_repo_creation_failure_emits_audit_event(
        self, mock_logs, mock_repo_model, initialized_db
    ):
        """Test that repository creation failure emits org_mirror_repo_creation_failed event."""
        org, robot = _create_org_and_robot("audit_repo_test4")
        config = _create_org_mirror_config(org, robot)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        # Mock repository creation to raise an exception
        mock_repo_model.create_repository.side_effect = Exception("Database error")

        result = _ensure_local_repository(config, org_mirror_repo)

        # Verify repository was not created
        assert result is None

        # Verify failure audit event was logged
        calls = mock_logs.log_action.call_args_list
        repo_failed_calls = [c for c in calls if c[0][0] == "org_mirror_repo_creation_failed"]
        assert len(repo_failed_calls) == 1

        call_args = repo_failed_calls[0]
        assert call_args[1]["namespace_name"] == org.username
        assert call_args[1]["repository_name"] == "fail-repo"
        assert call_args[1]["performer"] == robot
        assert call_args[1]["ip"] is None
        metadata = call_args[1]["metadata"]
        assert "external_reference" in metadata
        assert "Database error" in metadata["error"]


class TestDiscoveryAuditLogging:
    """Tests for audit events during org mirror discovery phase."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_logs_sync_started(self, mock_logs, mock_get_adapter, initialized_db):
        """Test that discovery phase logs org_mirror_sync_started event."""
        org, robot = _create_org_and_robot("audit_discovery_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["repo1"]
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify org_mirror_sync_started was logged
        calls = mock_logs.log_action.call_args_list
        started_calls = [c for c in calls if c[0][0] == "org_mirror_sync_started"]
        assert len(started_calls) == 1

        call_args = started_calls[0]
        assert call_args[1]["namespace_name"] == org.username
        assert call_args[1]["performer"] == robot
        metadata = call_args[1]["metadata"]
        assert "message" in metadata
        assert "external_registry_url" in metadata
        assert "external_namespace" in metadata

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_logs_sync_success(self, mock_logs, mock_get_adapter, initialized_db):
        """Test that successful discovery logs org_mirror_sync_success event."""
        org, robot = _create_org_and_robot("audit_discovery_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["repo1", "repo2"]
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify org_mirror_sync_success was logged
        calls = mock_logs.log_action.call_args_list
        success_calls = [c for c in calls if c[0][0] == "org_mirror_sync_success"]
        assert len(success_calls) == 1

        call_args = success_calls[0]
        assert call_args[1]["namespace_name"] == org.username
        metadata = call_args[1]["metadata"]
        assert "Discovery completed" in metadata["message"]

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_logs_sync_failed_on_error(self, mock_logs, mock_get_adapter, initialized_db):
        """Test that discovery failure logs org_mirror_sync_failed event."""
        org, robot = _create_org_and_robot("audit_discovery_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.side_effect = Exception("Connection refused")
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify org_mirror_sync_failed was logged
        calls = mock_logs.log_action.call_args_list
        failed_calls = [c for c in calls if c[0][0] == "org_mirror_sync_failed"]
        assert len(failed_calls) == 1

        call_args = failed_calls[0]
        assert call_args[1]["namespace_name"] == org.username
        metadata = call_args[1]["metadata"]
        assert "Connection refused" in metadata["message"]


# =============================================================================
# Edge case tests for process_org_mirror_discovery()
# =============================================================================


class TestProcessOrgMirrorDiscoveryIterator:
    """Tests for process_org_mirror_discovery with actual iterator behavior."""

    @patch("workers.repomirrorworker.perform_org_mirror_discovery")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_preempted_sets_abort(self, mock_features, mock_model, mock_perform, initialized_db):
        """When perform_org_mirror_discovery raises PreemptedException, abort is set."""
        mock_features.ORG_MIRROR = True
        mock_abt = Mock()
        mock_config = Mock()
        mock_model.configs_to_discover.return_value = (
            iter([(mock_config, mock_abt, 5)]),
            "next_token",
        )
        mock_perform.side_effect = PreemptedException()

        result = process_org_mirror_discovery()

        mock_abt.set.assert_called_once()
        assert result == "next_token"

    @patch("workers.repomirrorworker.perform_org_mirror_discovery")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_generic_exception_continues(
        self, mock_features, mock_model, mock_perform, initialized_db
    ):
        """When a generic exception occurs, processing continues to next config."""
        mock_features.ORG_MIRROR = True
        mock_abt1 = Mock()
        mock_abt2 = Mock()
        mock_config1 = Mock()
        mock_config2 = Mock()
        mock_model.configs_to_discover.return_value = (
            iter([(mock_config1, mock_abt1, 5), (mock_config2, mock_abt2, 4)]),
            "next_token",
        )
        mock_perform.side_effect = [Exception("error"), None]

        result = process_org_mirror_discovery()

        assert mock_perform.call_count == 2
        assert result == "next_token"

    @patch("workers.repomirrorworker.perform_org_mirror_discovery")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_successful_iteration(self, mock_features, mock_model, mock_perform, initialized_db):
        """Successful iteration processes all configs and returns next token."""
        mock_features.ORG_MIRROR = True
        mock_config = Mock()
        mock_abt = Mock()
        mock_model.configs_to_discover.return_value = (
            iter([(mock_config, mock_abt, 3)]),
            "next_token",
        )

        result = process_org_mirror_discovery()

        mock_perform.assert_called_once_with(mock_config)
        assert result == "next_token"


# =============================================================================
# Edge case tests for process_org_mirrors()
# =============================================================================


class TestProcessOrgMirrorsIterator:
    """Tests for process_org_mirrors with actual iterator behavior."""

    @patch("workers.repomirrorworker.perform_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_preempted_sets_abort(self, mock_features, mock_model, mock_perform, initialized_db):
        """When perform_org_mirror_repo raises PreemptedException, abort is set."""
        mock_features.ORG_MIRROR = True
        mock_abt = Mock()
        mock_repo = Mock()
        mock_model.repositories_to_mirror.return_value = (
            iter([(mock_repo, mock_abt, 5)]),
            "next_token",
        )
        mock_perform.side_effect = PreemptedException()
        mock_skopeo = Mock()

        result = process_org_mirrors(mock_skopeo)

        mock_abt.set.assert_called_once()
        assert result == "next_token"

    @patch("workers.repomirrorworker.perform_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_generic_exception_returns_none(
        self, mock_features, mock_model, mock_perform, initialized_db
    ):
        """When a generic exception occurs, process_org_mirrors returns None."""
        mock_features.ORG_MIRROR = True
        mock_abt = Mock()
        mock_repo = Mock()
        mock_model.repositories_to_mirror.return_value = (
            iter([(mock_repo, mock_abt, 5)]),
            "next_token",
        )
        mock_perform.side_effect = RuntimeError("unexpected")
        mock_skopeo = Mock()

        result = process_org_mirrors(mock_skopeo)

        assert result is None

    @patch("workers.repomirrorworker.perform_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model")
    @patch("workers.repomirrorworker.features")
    def test_successful_iteration(self, mock_features, mock_model, mock_perform, initialized_db):
        """Successful iteration processes all repos and returns next token."""
        mock_features.ORG_MIRROR = True
        mock_repo = Mock()
        mock_abt = Mock()
        mock_model.repositories_to_mirror.return_value = (
            iter([(mock_repo, mock_abt, 3)]),
            "next_token",
        )
        mock_skopeo = Mock()

        result = process_org_mirrors(mock_skopeo)

        mock_perform.assert_called_once_with(mock_skopeo, mock_repo)
        assert result == "next_token"


# =============================================================================
# Edge case tests for perform_org_mirror_discovery()
# =============================================================================


class TestPerformOrgMirrorDiscoveryEdgeCases:
    """Edge case tests for perform_org_mirror_discovery."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    def test_cancel_propagates_to_repos(self, mock_logs, initialized_db):
        """When config status is CANCEL, cancel is propagated to all repos."""
        org, robot = _create_org_and_robot("discovery_cancel_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_status = OrgMirrorStatus.CANCEL
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        # Create repos to cancel
        for name in ["cancel-repo1", "cancel-repo2"]:
            OrgMirrorRepository.create(
                org_mirror_config=config,
                repository_name=name,
                sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            )

        perform_org_mirror_discovery(config)

        # Verify cancel log was emitted
        cancel_calls = [
            c for c in mock_logs.log_action.call_args_list if c[0][0] == "org_mirror_sync_failed"
        ]
        assert len(cancel_calls) == 1
        assert "cancelled" in cancel_calls[0][1]["metadata"]["message"].lower()

        # Verify config released with CANCEL status
        refreshed = OrgMirrorConfig.get_by_id(config.id)
        assert refreshed.sync_status == OrgMirrorStatus.CANCEL

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_adapter_creation_failure(self, mock_logs, mock_get_adapter, initialized_db):
        """When registry adapter creation fails, discovery fails gracefully."""
        org, robot = _create_org_and_robot("discovery_adapter_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_get_adapter.side_effect = ValueError("Unknown registry type")

        perform_org_mirror_discovery(config)

        # Verify failure log
        failed_calls = [
            c for c in mock_logs.log_action.call_args_list if c[0][0] == "org_mirror_sync_failed"
        ]
        assert len(failed_calls) >= 1

        # Verify config released with FAIL status
        refreshed = OrgMirrorConfig.get_by_id(config.id)
        assert refreshed.sync_status == OrgMirrorStatus.FAIL

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_sync_now_propagation(self, _mock_logs, mock_get_adapter, initialized_db):
        """When config status is SYNC_NOW, it propagates to all discovered repos."""
        org, robot = _create_org_and_robot("discovery_syncnow_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_status = OrgMirrorStatus.SYNC_NOW
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["sync-now-repo1"]
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify repos were created with SYNC_NOW status
        repos = list(
            OrgMirrorRepository.select().where(OrgMirrorRepository.org_mirror_config == config)
        )
        assert len(repos) == 1
        assert repos[0].sync_status == OrgMirrorRepoStatus.SYNC_NOW

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.release_org_mirror_config")
    @patch("workers.repomirrorworker.claim_org_mirror_config")
    @patch("workers.repomirrorworker.logs_model")
    def test_decryption_failure(self, mock_logs, mock_claim, mock_release, initialized_db):
        """When credential decryption fails, discovery fails gracefully."""
        org, robot = _create_org_and_robot("discovery_decrypt_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        # Create a mock claimed config that raises on decrypt
        mock_config = MagicMock()
        mock_config.id = config.id
        mock_config.organization = org
        mock_config.organization.username = org.username
        mock_config.internal_robot = robot
        mock_config.external_registry_url = config.external_registry_url
        mock_config.external_namespace = config.external_namespace
        mock_config.sync_status = OrgMirrorStatus.NEVER_RUN

        mock_username = MagicMock()
        mock_username.decrypt.side_effect = DecryptionFailureException("decrypt failed")
        mock_username.__bool__ = MagicMock(return_value=True)
        mock_config.external_registry_username = mock_username

        mock_claim.return_value = mock_config

        perform_org_mirror_discovery(config)

        # Verify failure log was emitted
        failed_calls = [
            c for c in mock_logs.log_action.call_args_list if c[0][0] == "org_mirror_sync_failed"
        ]
        assert len(failed_calls) >= 1

        # Verify release was called with FAIL status
        mock_release.assert_called_once_with(mock_config, OrgMirrorStatus.FAIL)

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_source_registry_error(self, mock_logs, mock_get_adapter, initialized_db):
        """When source registry listing fails, discovery fails gracefully."""
        org, robot = _create_org_and_robot("discovery_source_err_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.side_effect = ConnectionError("Connection refused")
        mock_get_adapter.return_value = mock_adapter

        perform_org_mirror_discovery(config)

        # Verify failure log
        failed_calls = [
            c for c in mock_logs.log_action.call_args_list if c[0][0] == "org_mirror_sync_failed"
        ]
        assert len(failed_calls) >= 1
        refreshed = OrgMirrorConfig.get_by_id(config.id)
        assert refreshed.sync_status == OrgMirrorStatus.FAIL


# =============================================================================
# Edge case tests for perform_org_mirror_repo()
# =============================================================================


class TestPerformOrgMirrorRepoEdgeCases:
    """Edge case tests for perform_org_mirror_repo."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.claim_org_mirror_repo")
    @patch("workers.repomirrorworker.logs_model")
    def test_preempted_when_claim_fails(self, _mock_logs, mock_claim, initialized_db, app):
        """When claim_org_mirror_repo returns None, PreemptedException is raised."""
        org, robot = _create_org_and_robot("preempt_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="preempt-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
        )

        mock_claim.return_value = None
        mock_skopeo = Mock()

        with pytest.raises(PreemptedException):
            perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker._ensure_local_repository")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_local_repo_creation_failure(
        self, mock_token, _mock_logs, mock_ensure, initialized_db, app
    ):
        """When local repo creation fails, sync fails gracefully."""
        org, robot = _create_org_and_robot("localrepo_fail_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="local-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        mock_ensure.return_value = None
        mock_token.return_value = "robot_token"
        mock_skopeo = Mock()

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker._get_all_tags_for_org_mirror")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_skopeo_tag_listing_failure(
        self, mock_token, _mock_logs, mock_get_tags, initialized_db, app
    ):
        """When skopeo tag listing fails with RepoMirrorSkopeoException, sync fails."""
        org, robot = _create_org_and_robot("skopeo_fail_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="skopeo-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        mock_get_tags.side_effect = RepoMirrorSkopeoException(
            "skopeo list-tags failed", "stdout", "stderr"
        )
        mock_token.return_value = "robot_token"
        mock_skopeo = Mock()

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker._get_all_tags_for_org_mirror")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_generic_tag_listing_exception(
        self, mock_token, _mock_logs, mock_get_tags, initialized_db, app
    ):
        """When tag listing raises a generic exception, sync fails."""
        org, robot = _create_org_and_robot("generic_tag_fail_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="generic-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        mock_get_tags.side_effect = RuntimeError("unexpected error")
        mock_token.return_value = "robot_token"
        mock_skopeo = Mock()

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.release_org_mirror_repo")
    @patch("workers.repomirrorworker.claim_org_mirror_repo")
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_decryption_failure_during_sync(
        self, mock_token, _mock_logs, mock_claim, mock_release, initialized_db, app
    ):
        """When credential decryption fails during sync, sync fails gracefully."""
        org, robot = _create_org_and_robot("decrypt_sync_test")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="decrypt-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        # Build a mock claimed repo that raises DecryptionFailureException on credentials
        mock_claimed = MagicMock()
        mock_claimed.id = org_mirror_repo.id
        mock_claimed.repository_name = org_mirror_repo.repository_name

        mock_org_config = MagicMock()
        mock_org_config.id = config.id
        mock_org_config.organization = org
        mock_org_config.organization.username = org.username
        mock_org_config.internal_robot = robot
        mock_org_config.internal_robot.username = robot.username
        mock_org_config.external_registry_url = config.external_registry_url
        mock_org_config.external_namespace = config.external_namespace
        mock_org_config.external_registry_config = {}
        mock_org_config.skopeo_timeout = 300
        mock_org_config.visibility = config.visibility

        mock_username = MagicMock()
        mock_username.decrypt.side_effect = DecryptionFailureException("decrypt failed")
        mock_username.__bool__ = MagicMock(return_value=True)
        mock_org_config.external_registry_username = mock_username

        mock_claimed.org_mirror_config = mock_org_config
        mock_claim.return_value = mock_claimed

        mock_token.return_value = "robot_token"
        mock_skopeo = Mock()

        with patch("workers.repomirrorworker._ensure_local_repository") as mock_ensure:
            mock_ensure.return_value = Mock()

            with patch("workers.repomirrorworker._get_all_tags_for_org_mirror") as mock_get_tags:
                mock_get_tags.return_value = ["v1.0"]

                result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL
        mock_release.assert_called_once_with(mock_claimed, OrgMirrorRepoStatus.FAIL)


# =============================================================================
# Edge case tests for _get_all_tags_for_org_mirror()
# =============================================================================


class TestGetAllTagsForOrgMirror:
    """Tests for _get_all_tags_for_org_mirror edge cases."""

    def test_decryption_failure_raises_skopeo_exception(self, initialized_db, app):
        """When credential decryption fails, RepoMirrorSkopeoException is raised."""
        mock_config = MagicMock()
        mock_username = MagicMock()
        mock_username.decrypt.side_effect = DecryptionFailureException("decrypt failed")
        mock_username.__bool__ = MagicMock(return_value=True)
        mock_config.external_registry_username = mock_username

        mock_skopeo = Mock()

        with pytest.raises(RepoMirrorSkopeoException) as exc_info:
            _get_all_tags_for_org_mirror(mock_skopeo, mock_config, "registry.example.com/ns/repo")

        assert "decrypt" in str(exc_info.value.message).lower()

    @patch("workers.repomirrorworker.database")
    def test_skopeo_tags_failure_raises_exception(self, _mock_db, initialized_db, app):
        """When skopeo.tags fails, RepoMirrorSkopeoException is raised."""
        mock_config = MagicMock()
        mock_config.external_registry_username = None
        mock_config.external_registry_password = None
        mock_config.skopeo_timeout = 300
        mock_config.external_registry_config = {}

        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(False, [], "", "tags listing failed")

        with pytest.raises(RepoMirrorSkopeoException):
            _get_all_tags_for_org_mirror(mock_skopeo, mock_config, "registry.example.com/ns/repo")


# =============================================================================
# Tests for RepoMirrorWorker org mirror methods
# =============================================================================


class TestRepoMirrorWorkerOrgMethods:
    """Tests for the org mirror methods on RepoMirrorWorker."""

    @patch("workers.repomirrorworker.repomirrorworker.process_org_mirror_discovery")
    def test_process_org_mirror_discovery_loops(self, mock_process, initialized_db, app):
        """_process_org_mirror_discovery loops until token is None."""
        mock_process.side_effect = [Mock(), None]

        worker = RepoMirrorWorker()
        worker._process_org_mirror_discovery()

        assert mock_process.call_count == 2

    @patch("workers.repomirrorworker.repomirrorworker.process_org_mirrors")
    def test_process_org_mirrors_loops(self, mock_process, initialized_db, app):
        """_process_org_mirrors loops until token is None."""
        mock_process.side_effect = [Mock(), None]

        worker = RepoMirrorWorker()
        worker._process_org_mirrors()

        assert mock_process.call_count == 2


# =============================================================================
# Tests for manifest_utils.py
# =============================================================================


class TestManifestUtils:
    """Tests for manifest_utils.py error-handling paths."""

    def test_is_manifest_list_invalid_json(self):
        """Invalid JSON returns False."""
        assert is_manifest_list("not valid json") is False

    def test_is_manifest_list_none_input(self):
        """None input returns False (TypeError path)."""
        assert is_manifest_list(None) is False

    def test_is_manifest_list_no_media_type_no_manifests(self):
        """Non-list manifest without mediaType or manifests key returns False."""
        manifest = json.dumps({"schemaVersion": 2, "config": {}})
        assert is_manifest_list(manifest) is False

    def test_is_manifest_list_with_manifests_array(self):
        """Manifest with 'manifests' array but no mediaType returns True (OCI index)."""
        manifest = json.dumps({"schemaVersion": 2, "manifests": []})
        assert is_manifest_list(manifest) is True

    def test_is_manifest_list_manifests_not_a_list(self):
        """Manifest with 'manifests' key that is not a list returns False."""
        manifest = json.dumps({"schemaVersion": 2, "manifests": "not-a-list"})
        assert is_manifest_list(manifest) is False

    def test_get_manifest_media_type_invalid_json(self):
        """Invalid JSON returns None."""
        assert get_manifest_media_type("not valid json") is None

    def test_get_manifest_media_type_none_input(self):
        """None input returns None (TypeError path)."""
        assert get_manifest_media_type(None) is None

    def test_get_manifest_media_type_no_media_type_key(self):
        """Valid JSON without mediaType key returns None."""
        manifest = json.dumps({"schemaVersion": 2})
        assert get_manifest_media_type(manifest) is None

    def test_filter_manifests_by_architecture_invalid_json(self):
        """Invalid JSON returns empty list."""
        assert filter_manifests_by_architecture("not valid json", ["amd64"]) == []

    def test_filter_manifests_by_architecture_no_manifests_key(self):
        """Valid JSON without 'manifests' key returns empty list."""
        manifest = json.dumps({"schemaVersion": 2})
        assert filter_manifests_by_architecture(manifest, ["amd64"]) == []

    def test_get_available_architectures_invalid_json(self):
        """Invalid JSON returns empty list."""
        assert get_available_architectures("not valid json") == []

    def test_get_available_architectures_no_manifests_key(self):
        """Valid JSON without 'manifests' key returns empty list."""
        manifest = json.dumps({"schemaVersion": 2})
        assert get_available_architectures(manifest) == []

    def test_get_available_architectures_manifest_without_platform(self):
        """Manifests without platform info are excluded."""
        manifest = json.dumps(
            {
                "manifests": [
                    {"digest": "sha256:abc"},
                    {"digest": "sha256:def", "platform": {"architecture": "amd64"}},
                ]
            }
        )
        result = get_available_architectures(manifest)
        assert result == ["amd64"]


# =============================================================================
# Tests for org_mirror_model.py
# =============================================================================


class TestOrgMirrorModel:
    """Tests for OrgMirrorModel configs_to_discover and repositories_to_mirror."""

    # --- configs_to_discover ---

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_config")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_config")
    def test_configs_to_discover_max_id_none(self, mock_min_id, mock_max_id):
        """When max_id is None, returns (None, None)."""
        mock_min_id.return_value = 1
        mock_max_id.return_value = None

        model = OrgMirrorModel()
        iterator, token = model.configs_to_discover()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_config")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_config")
    def test_configs_to_discover_min_id_none(self, mock_min_id, mock_max_id):
        """When min_id is None, returns (None, None)."""
        mock_min_id.return_value = None
        mock_max_id.return_value = 10

        model = OrgMirrorModel()
        iterator, token = model.configs_to_discover()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_config")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_config")
    def test_configs_to_discover_min_id_gt_max_id(self, mock_min_id, mock_max_id):
        """When min_id > max_id, returns (None, None)."""
        mock_min_id.return_value = 20
        mock_max_id.return_value = 10

        model = OrgMirrorModel()
        iterator, token = model.configs_to_discover()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.yield_random_entries")
    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_config")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_config")
    def test_configs_to_discover_no_start_token(self, mock_min_id, mock_max_id, mock_yield):
        """Without start_token, uses get_min_id and returns iterator + token."""
        mock_min_id.return_value = 1
        mock_max_id.return_value = 100
        mock_yield.return_value = iter([])

        model = OrgMirrorModel()
        iterator, token = model.configs_to_discover()

        assert iterator is not None
        assert token.min_id == 101
        mock_min_id.assert_called_once()

    @patch("workers.repomirrorworker.org_mirror_model.yield_random_entries")
    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_config")
    def test_configs_to_discover_with_start_token(self, mock_max_id, mock_yield):
        """With start_token, uses token.min_id instead of get_min_id."""
        mock_max_id.return_value = 100
        mock_yield.return_value = iter([])

        model = OrgMirrorModel()
        start_token = OrgMirrorConfigToken(min_id=50)
        iterator, token = model.configs_to_discover(start_token=start_token)

        assert iterator is not None
        assert token.min_id == 101

    # --- repositories_to_mirror ---

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_repo")
    def test_repos_to_mirror_max_id_none(self, mock_min_id, mock_max_id):
        """When max_id is None, returns (None, None)."""
        mock_min_id.return_value = 1
        mock_max_id.return_value = None

        model = OrgMirrorModel()
        iterator, token = model.repositories_to_mirror()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_repo")
    def test_repos_to_mirror_min_id_none(self, mock_min_id, mock_max_id):
        """When min_id is None, returns (None, None)."""
        mock_min_id.return_value = None
        mock_max_id.return_value = 10

        model = OrgMirrorModel()
        iterator, token = model.repositories_to_mirror()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_repo")
    def test_repos_to_mirror_min_id_gt_max_id(self, mock_min_id, mock_max_id):
        """When min_id > max_id, returns (None, None)."""
        mock_min_id.return_value = 20
        mock_max_id.return_value = 10

        model = OrgMirrorModel()
        iterator, token = model.repositories_to_mirror()

        assert iterator is None
        assert token is None

    @patch("workers.repomirrorworker.org_mirror_model.yield_random_entries")
    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_repo")
    @patch("workers.repomirrorworker.org_mirror_model.get_min_id_for_org_mirror_repo")
    def test_repos_to_mirror_no_start_token(self, mock_min_id, mock_max_id, mock_yield):
        """Without start_token, uses get_min_id and returns iterator + token."""
        mock_min_id.return_value = 1
        mock_max_id.return_value = 100
        mock_yield.return_value = iter([])

        model = OrgMirrorModel()
        iterator, token = model.repositories_to_mirror()

        assert iterator is not None
        assert token.min_id == 101
        mock_min_id.assert_called_once()

    @patch("workers.repomirrorworker.org_mirror_model.yield_random_entries")
    @patch("workers.repomirrorworker.org_mirror_model.get_max_id_for_org_mirror_repo")
    def test_repos_to_mirror_with_start_token(self, mock_max_id, mock_yield):
        """With start_token, uses token.min_id instead of get_min_id."""
        mock_max_id.return_value = 100
        mock_yield.return_value = iter([])

        model = OrgMirrorModel()
        start_token = OrgMirrorToken(min_id=50)
        iterator, token = model.repositories_to_mirror(start_token=start_token)

        assert iterator is not None
        assert token.min_id == 101


# =============================================================================
# Tests for Prometheus metrics instrumentation
# =============================================================================


def _get_counter_value(counter, labels=None):
    """Get current value of a Prometheus Counter (with optional labels)."""
    if labels:
        return counter.labels(**labels)._value.get()
    return counter._value.get()


def _get_gauge_value(gauge):
    """Get current value of a Prometheus Gauge."""
    return gauge._value.get()


class TestOrgMirrorMetrics:
    """Tests for Prometheus metrics instrumentation in org mirror functions."""

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_success_increments_metrics(
        self, mock_logs, mock_get_adapter, initialized_db
    ):
        """Successful discovery should increment discovery_total(success), duration,
        repos_discovered, and repos_created counters."""
        org, robot = _create_org_and_robot("metrics_disc_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_adapter = Mock()
        mock_adapter.list_repositories.return_value = ["repo1", "repo2", "repo3"]
        mock_get_adapter.return_value = mock_adapter

        # Record baseline values
        success_before = _get_counter_value(org_mirror_discovery_total, {"status": "success"})
        created_before = _get_counter_value(org_mirror_repos_created_total)

        perform_org_mirror_discovery(config)

        assert (
            _get_counter_value(org_mirror_discovery_total, {"status": "success"})
            == success_before + 1
        )
        assert _get_gauge_value(org_mirror_repos_discovered) == 3
        assert _get_counter_value(org_mirror_repos_created_total) == created_before + 3

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.get_registry_adapter")
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_failure_increments_fail_counter(
        self, mock_logs, mock_get_adapter, initialized_db
    ):
        """Discovery failure (adapter error) should increment discovery_total(fail)."""
        org, robot = _create_org_and_robot("metrics_disc_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        mock_get_adapter.side_effect = ValueError("Unsupported registry type")

        fail_before = _get_counter_value(org_mirror_discovery_total, {"status": "fail"})

        perform_org_mirror_discovery(config)

        assert _get_counter_value(org_mirror_discovery_total, {"status": "fail"}) == fail_before + 1

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    def test_discovery_cancel_increments_cancel_counter(self, mock_logs, initialized_db):
        """Discovery cancel should increment discovery_total(cancel)."""
        org, robot = _create_org_and_robot("metrics_disc_test3")
        config = _create_org_mirror_config(org, robot, is_enabled=True)
        config.sync_status = OrgMirrorStatus.CANCEL
        config.sync_start_date = datetime.utcnow() - timedelta(hours=1)
        config.save()

        cancel_before = _get_counter_value(org_mirror_discovery_total, {"status": "cancel"})

        perform_org_mirror_discovery(config)

        assert (
            _get_counter_value(org_mirror_discovery_total, {"status": "cancel"})
            == cancel_before + 1
        )

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_repo_sync_success_increments_counter(self, mock_token, mock_logs, initialized_db, app):
        """Successful repo sync should increment repo_sync_total(success)."""
        org, robot = _create_org_and_robot("metrics_sync_test1")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="metrics-sync-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(True, [], "copied", "")
        mock_token.return_value = "robot_token"

        success_before = _get_counter_value(org_mirror_repo_sync_total, {"status": "success"})

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.SUCCESS
        assert (
            _get_counter_value(org_mirror_repo_sync_total, {"status": "success"})
            == success_before + 1
        )

    @disable_existing_org_mirrors
    @patch("workers.repomirrorworker.logs_model")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    def test_repo_sync_failure_increments_counter(self, mock_token, mock_logs, initialized_db, app):
        """Failed repo sync should increment repo_sync_total(fail)."""
        org, robot = _create_org_and_robot("metrics_sync_test2")
        config = _create_org_mirror_config(org, robot, is_enabled=True)

        past_time = datetime.utcnow() - timedelta(hours=1)
        org_mirror_repo = OrgMirrorRepository.create(
            org_mirror_config=config,
            repository_name="metrics-fail-repo",
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            sync_start_date=past_time,
            sync_retries_remaining=3,
        )

        mock_skopeo = Mock()
        mock_skopeo.tags.return_value = SkopeoResults(True, ["v1.0"], "", "")
        mock_skopeo.copy.return_value = SkopeoResults(False, [], "", "copy failed")
        mock_token.return_value = "robot_token"

        fail_before = _get_counter_value(org_mirror_repo_sync_total, {"status": "fail"})

        result = perform_org_mirror_repo(mock_skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL
        assert _get_counter_value(org_mirror_repo_sync_total, {"status": "fail"}) == fail_before + 1
