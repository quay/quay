"""
Unit tests for organization mirror worker.

Tests worker logic with mocked discovery clients and data access.
"""

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from data.database import OrgMirrorRepoStatus, OrgMirrorStatus
from workers.orgmirrorworker import (
    DiscoveryException,
    PreemptedException,
    create_repositories,
    perform_org_mirror,
    process_org_mirrors,
)
from workers.orgmirrorworker.models_interface import OrgMirrorToken

# Test process_org_mirrors


def test_process_org_mirrors_feature_disabled():
    """Test that worker returns None when feature is disabled."""
    model = Mock()

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", False):
        result = process_org_mirrors(model, None)

    assert result is None
    model.orgs_to_mirror.assert_not_called()


def test_process_org_mirrors_no_orgs():
    """Test processing when no orgs are ready to mirror."""
    model = Mock()
    model.orgs_to_mirror.return_value = (None, None)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        with patch("workers.orgmirrorworker.undiscovered_orgs") as metrics:
            result = process_org_mirrors(model, None)

    assert result is None
    metrics.set.assert_called_once_with(0)


def test_process_org_mirrors_with_token():
    """Test processing with pagination token."""
    model = Mock()
    token = OrgMirrorToken(100)
    model.orgs_to_mirror.return_value = (None, None)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        process_org_mirrors(model, token)

    model.orgs_to_mirror.assert_called_once_with(start_token=token)


def test_process_org_mirrors_success():
    """Test successful processing of org mirrors."""
    model = Mock()

    # Create mock mirror
    mirror1 = Mock()
    mirror1.organization.username = "testorg"

    # Create iterator
    abt1 = Mock()
    iterator = [(mirror1, abt1, 0)]
    next_token = OrgMirrorToken(200)

    model.orgs_to_mirror.return_value = (iter(iterator), next_token)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        with patch("workers.orgmirrorworker.perform_org_mirror") as mock_perform:
            with patch("workers.orgmirrorworker.UseThenDisconnect"):
                result = process_org_mirrors(model, None)

    assert result == next_token
    mock_perform.assert_called_once_with(model, mirror1)
    abt1.set.assert_not_called()


def test_process_org_mirrors_preempted():
    """Test handling of preemption by another worker."""
    model = Mock()

    mirror1 = Mock()
    mirror1.organization.username = "testorg"

    abt1 = Mock()
    iterator = [(mirror1, abt1, 0)]

    model.orgs_to_mirror.return_value = (iter(iterator), None)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        with patch("workers.orgmirrorworker.perform_org_mirror", side_effect=PreemptedException()):
            with patch("workers.orgmirrorworker.UseThenDisconnect"):
                result = process_org_mirrors(model, None)

    # Should set abort flag when preempted
    abt1.set.assert_called_once()


def test_process_org_mirrors_exception():
    """Test handling of unexpected exceptions."""
    model = Mock()

    mirror1 = Mock()
    mirror1.organization.username = "testorg"

    abt1 = Mock()
    iterator = [(mirror1, abt1, 0)]

    model.orgs_to_mirror.return_value = (iter(iterator), None)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        with patch(
            "workers.orgmirrorworker.perform_org_mirror", side_effect=Exception("Test error")
        ):
            with patch("workers.orgmirrorworker.UseThenDisconnect"):
                result = process_org_mirrors(model, None)

    # Should return None on exception
    assert result is None


# Test perform_org_mirror


def test_perform_org_mirror_claim_fails():
    """Test that PreemptedException is raised when claim fails."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=None):
        with pytest.raises(PreemptedException):
            perform_org_mirror(model, mirror)


def test_perform_org_mirror_discovery_stub():
    """Test perform_org_mirror with stubbed discovery (returns empty list)."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.external_reference = "harbor.example.com/project"

    claimed_mirror = Mock()
    claimed_mirror.organization.username = "testorg"
    claimed_mirror.external_reference = "harbor.example.com/project"

    model.repos_to_create.return_value = []

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=claimed_mirror):
        with patch("workers.orgmirrorworker.discover_repositories", return_value=[]):
            with patch("workers.orgmirrorworker.record_discovered_repos"):
                with patch("workers.orgmirrorworker.logs_model"):
                    with patch("workers.orgmirrorworker.release_org_mirror") as mock_release:
                        with patch("workers.orgmirrorworker.discovered_repos_pending"):
                            perform_org_mirror(model, mirror)

    # Should release with SUCCESS when discovery returns empty list
    mock_release.assert_called_once()
    call_args = mock_release.call_args[0]
    assert call_args[1] == OrgMirrorStatus.SUCCESS


def test_perform_org_mirror_discovery_found_repos():
    """Test perform_org_mirror when discovery finds repositories."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.external_reference = "harbor.example.com/project"

    claimed_mirror = Mock()
    claimed_mirror.organization.username = "testorg"
    claimed_mirror.external_reference = "harbor.example.com/project"

    discovered = [
        {"name": "repo1", "external_reference": "harbor.example.com/project/repo1"},
        {"name": "repo2", "external_reference": "harbor.example.com/project/repo2"},
    ]

    model.repos_to_create.return_value = []

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=claimed_mirror):
        with patch("workers.orgmirrorworker.discover_repositories", return_value=discovered):
            with patch("workers.orgmirrorworker.record_discovered_repos", return_value=2):
                with patch("workers.orgmirrorworker.logs_model"):
                    with patch("workers.orgmirrorworker.release_org_mirror") as mock_release:
                        with patch("workers.orgmirrorworker.discovered_repos_pending"):
                            perform_org_mirror(model, mirror)

    mock_release.assert_called_once()
    call_args = mock_release.call_args[0]
    assert call_args[1] == OrgMirrorStatus.SUCCESS


def test_perform_org_mirror_discovery_fails():
    """Test handling of discovery failure."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.external_reference = "harbor.example.com/project"

    claimed_mirror = Mock()
    claimed_mirror.organization.username = "testorg"
    claimed_mirror.external_reference = "harbor.example.com/project"

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=claimed_mirror):
        with patch("workers.orgmirrorworker.discover_repositories", return_value=None):
            with patch("workers.orgmirrorworker.logs_model"):
                with patch("workers.orgmirrorworker.release_org_mirror") as mock_release:
                    perform_org_mirror(model, mirror)

    # Should release with FAIL when discovery returns None
    mock_release.assert_called_once()
    call_args = mock_release.call_args[0]
    assert call_args[1] == OrgMirrorStatus.FAIL


def test_perform_org_mirror_creation_partial_failure():
    """Test handling when some repos succeed and some fail."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.external_reference = "harbor.example.com/project"

    claimed_mirror = Mock()
    claimed_mirror.organization.username = "testorg"
    claimed_mirror.external_reference = "harbor.example.com/project"

    model.repos_to_create.return_value = []

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=claimed_mirror):
        with patch("workers.orgmirrorworker.discover_repositories", return_value=[]):
            with patch("workers.orgmirrorworker.create_repositories", return_value=(2, 1, 1)):
                with patch("workers.orgmirrorworker.logs_model"):
                    with patch("workers.orgmirrorworker.release_org_mirror") as mock_release:
                        with patch("workers.orgmirrorworker.discovered_repos_pending"):
                            perform_org_mirror(model, mirror)

    # Should release with SUCCESS when at least some repos succeeded
    mock_release.assert_called_once()
    call_args = mock_release.call_args[0]
    assert call_args[1] == OrgMirrorStatus.SUCCESS


def test_perform_org_mirror_all_creations_failed():
    """Test handling when all repo creations fail."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"

    claimed_mirror = Mock()
    claimed_mirror.organization.username = "testorg"
    claimed_mirror.external_reference = "harbor.example.com/project"

    model.repos_to_create.return_value = []

    with patch("workers.orgmirrorworker.claim_org_mirror", return_value=claimed_mirror):
        with patch("workers.orgmirrorworker.discover_repositories", return_value=[]):
            with patch("workers.orgmirrorworker.create_repositories", return_value=(0, 0, 3)):
                with patch("workers.orgmirrorworker.logs_model"):
                    with patch("workers.orgmirrorworker.release_org_mirror") as mock_release:
                        with patch("workers.orgmirrorworker.discovered_repos_pending"):
                            perform_org_mirror(model, mirror)

    # Should release with FAIL when all creations failed
    mock_release.assert_called_once()
    call_args = mock_release.call_args[0]
    assert call_args[1] == OrgMirrorStatus.FAIL


# Test create_repositories


def test_create_repositories_no_repos():
    """Test create_repositories when no repos need creation."""
    model = Mock()
    mirror = Mock()
    mirror.organization.username = "testorg"

    model.repos_to_create.return_value = []

    created, skipped, failed = create_repositories(model, mirror)

    assert created == 0
    assert skipped == 0
    assert failed == 0


def test_create_repositories_new_repo_success():
    """Test successful creation of new repository."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.internal_robot = Mock()

    org_mirror_repo = Mock()
    org_mirror_repo.repository_name = "newrepo"
    org_mirror_repo.external_repo_name = "external/newrepo"

    model.repos_to_create.return_value = [org_mirror_repo]

    new_repo = Mock()

    with patch("workers.orgmirrorworker.get_repository", return_value=None):
        with patch("workers.orgmirrorworker.create_repository", return_value=new_repo):
            with patch("workers.orgmirrorworker.mark_repo_created") as mock_mark:
                with patch("workers.orgmirrorworker.logs_model"):
                    created, skipped, failed = create_repositories(model, mirror)

    assert created == 1
    assert skipped == 0
    assert failed == 0
    mock_mark.assert_called_once_with(org_mirror_repo, new_repo)


def test_create_repositories_existing_repo_skipped():
    """Test that existing repositories are skipped."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"

    org_mirror_repo = Mock()
    org_mirror_repo.repository_name = "existingrepo"
    org_mirror_repo.external_repo_name = "external/existingrepo"

    model.repos_to_create.return_value = [org_mirror_repo]

    existing_repo = Mock()

    with patch("workers.orgmirrorworker.get_repository", return_value=existing_repo):
        with patch("workers.orgmirrorworker.mark_repo_skipped") as mock_skip:
            created, skipped, failed = create_repositories(model, mirror)

    assert created == 0
    assert skipped == 1
    assert failed == 0
    mock_skip.assert_called_once_with(org_mirror_repo, "Repository already exists")


def test_create_repositories_creation_fails():
    """Test handling of repository creation failure."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.internal_robot = Mock()

    org_mirror_repo = Mock()
    org_mirror_repo.repository_name = "failrepo"
    org_mirror_repo.external_repo_name = "external/failrepo"

    model.repos_to_create.return_value = [org_mirror_repo]

    with patch("workers.orgmirrorworker.get_repository", return_value=None):
        with patch(
            "workers.orgmirrorworker.create_repository",
            side_effect=Exception("Permission denied"),
        ):
            with patch("workers.orgmirrorworker.mark_repo_failed") as mock_fail:
                with patch("workers.orgmirrorworker.logs_model"):
                    created, skipped, failed = create_repositories(model, mirror)

    assert created == 0
    assert skipped == 0
    assert failed == 1
    mock_fail.assert_called_once()


def test_create_repositories_mixed_results():
    """Test creating multiple repositories with mixed results."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"
    mirror.internal_robot = Mock()

    repo1 = Mock()  # Will be created
    repo1.repository_name = "newrepo"
    repo1.external_repo_name = "external/newrepo"

    repo2 = Mock()  # Will be skipped (exists)
    repo2.repository_name = "existingrepo"
    repo2.external_repo_name = "external/existingrepo"

    repo3 = Mock()  # Will fail
    repo3.repository_name = "failrepo"
    repo3.external_repo_name = "external/failrepo"

    model.repos_to_create.return_value = [repo1, repo2, repo3]

    new_repo = Mock()
    existing_repo = Mock()

    def get_repository_side_effect(org, name):
        if name == "existingrepo":
            return existing_repo
        return None

    def create_repository_side_effect(org, name, robot, description=None):
        if name == "failrepo":
            raise Exception("Creation failed")
        return new_repo

    with patch("workers.orgmirrorworker.get_repository", side_effect=get_repository_side_effect):
        with patch(
            "workers.orgmirrorworker.create_repository",
            side_effect=create_repository_side_effect,
        ):
            with patch("workers.orgmirrorworker.mark_repo_created"):
                with patch("workers.orgmirrorworker.mark_repo_skipped"):
                    with patch("workers.orgmirrorworker.mark_repo_failed"):
                        with patch("workers.orgmirrorworker.logs_model"):
                            created, skipped, failed = create_repositories(model, mirror)

    assert created == 1
    assert skipped == 1
    assert failed == 1


# Test metrics updates


def test_metrics_updated_correctly():
    """Test that Prometheus metrics are updated correctly."""
    model = Mock()

    mirror = Mock()
    mirror.organization.username = "testorg"

    abt = Mock()
    iterator = [(mirror, abt, 5)]

    model.orgs_to_mirror.return_value = (iter(iterator), None)

    with patch("workers.orgmirrorworker.features.ORG_MIRROR", True):
        with patch("workers.orgmirrorworker.perform_org_mirror"):
            with patch("workers.orgmirrorworker.undiscovered_orgs") as metrics:
                with patch("workers.orgmirrorworker.UseThenDisconnect"):
                    process_org_mirrors(model, None)

    # Should set metric to number of remaining orgs
    metrics.set.assert_called_with(5)
