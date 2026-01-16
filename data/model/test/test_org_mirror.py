"""
Unit tests for organization mirror data model.

Tests all data access functions for OrgMirrorConfig and OrgMirrorRepo including
claim/release patterns, optimistic locking, and transaction safety.
"""

from datetime import datetime, timedelta
from threading import Thread

import pytest

from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepo,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
)
from data.model.org_mirror import (
    MAX_SYNC_DURATION,
    MAX_SYNC_RETRIES,
    InvalidOrganizationException,
    OrgMirrorToken,
    claim_org_mirror,
    create_org_mirror,
    delete_org_mirror,
    get_discovered_repos,
    get_org_mirror_config,
    mark_repo_created,
    mark_repo_failed,
    mark_repo_skipped,
    orgs_to_mirror,
    record_discovered_repos,
    release_org_mirror,
    repos_to_create,
)
from data.model.organization import create_organization
from data.model.repository import create_repository
from data.model.user import get_user
from test.fixtures import *

# Test get_org_mirror_config


def test_get_org_mirror_config_success(initialized_db):
    """Test retrieving an organization mirror configuration."""
    # Create organization and robot
    org = create_organization("testorg", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    # Create mirror config
    mirror = create_org_mirror(
        "testorg",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Retrieve it
    retrieved = get_org_mirror_config("testorg")
    assert retrieved is not None
    assert retrieved.id == mirror.id
    assert retrieved.organization.username == "testorg"
    assert retrieved.external_reference == "harbor.example.com/project"
    assert retrieved.sync_interval == 3600


def test_get_org_mirror_config_not_found(initialized_db):
    """Test retrieving non-existent organization mirror returns None."""
    result = get_org_mirror_config("nonexistent")
    assert result is None


def test_get_org_mirror_config_disabled(initialized_db):
    """Test that disabled mirrors are not returned."""
    org = create_organization("testorg2", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg2",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Disable the mirror
    mirror.is_enabled = False
    mirror.save()

    # Should not be returned
    result = get_org_mirror_config("testorg2")
    assert result is None


# Test create_org_mirror


def test_create_org_mirror(initialized_db):
    """Test creating an organization mirror with all fields."""
    org = create_organization("testorg3", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg3",
        "harbor.example.com/myproject",
        sync_interval=7200,
        internal_robot=robot,
        skopeo_timeout=600,
        external_registry_username="testuser",
        external_registry_password="testpass",
        external_registry_config={"verify_tls": False},
    )

    assert mirror is not None
    assert mirror.organization.username == "testorg3"
    assert mirror.external_reference == "harbor.example.com/myproject"
    assert mirror.sync_interval == 7200
    assert mirror.skopeo_timeout == 600
    assert mirror.external_registry_config == {"verify_tls": False}
    assert mirror.sync_status == OrgMirrorStatus.NEVER_RUN
    assert mirror.is_enabled is True


def test_create_org_mirror_invalid_org(initialized_db):
    """Test creating mirror for non-existent organization raises exception."""
    robot = get_user("devtable+robot")

    with pytest.raises(InvalidOrganizationException):
        create_org_mirror(
            "nonexistentorg",
            "harbor.example.com/project",
            sync_interval=3600,
            internal_robot=robot,
            skopeo_timeout=300,
        )


# Test delete_org_mirror


def test_delete_org_mirror(initialized_db):
    """Test deleting an organization mirror cascades to discovered repos."""
    org = create_organization("testorg4", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg4",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Add discovered repos
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="harbor.example.com/project/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo2",
        external_repo_name="harbor.example.com/project/repo2",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )

    # Delete the mirror
    result = delete_org_mirror("testorg4")
    assert result is True

    # Verify mirror is gone
    assert get_org_mirror_config("testorg4") is None

    # Verify repos are gone
    repos = list(OrgMirrorRepo.select().where(OrgMirrorRepo.org_mirror == mirror.id))
    assert len(repos) == 0


def test_delete_org_mirror_not_found(initialized_db):
    """Test deleting non-existent mirror returns False."""
    result = delete_org_mirror("nonexistent")
    assert result is False


# Test orgs_to_mirror


def test_orgs_to_mirror_never_run(initialized_db):
    """Test that NEVER_RUN mirrors are returned."""
    org = create_organization("testorg5", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg5",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Should be returned since status is NEVER_RUN
    iterator, next_token = orgs_to_mirror()
    assert iterator is not None
    mirrors = list(iterator)
    assert len(mirrors) >= 1
    assert any(m.id == mirror.id for m in mirrors)


def test_orgs_to_mirror_sync_now(initialized_db):
    """Test that SYNC_NOW mirrors are returned."""
    org = create_organization("testorg6", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg6",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Set to SYNC_NOW
    mirror.sync_status = OrgMirrorStatus.SYNC_NOW
    mirror.save()

    iterator, next_token = orgs_to_mirror()
    assert iterator is not None
    mirrors = list(iterator)
    assert any(m.id == mirror.id for m in mirrors)


def test_orgs_to_mirror_interval_expired(initialized_db):
    """Test that SUCCESS mirrors with expired interval are returned."""
    org = create_organization("testorg7", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg7",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Set to SUCCESS with old sync_start_date
    mirror.sync_status = OrgMirrorStatus.SUCCESS
    mirror.sync_start_date = datetime.utcnow() - timedelta(seconds=7200)  # 2 hours ago
    mirror.save()

    iterator, next_token = orgs_to_mirror()
    assert iterator is not None
    mirrors = list(iterator)
    assert any(m.id == mirror.id for m in mirrors)


def test_orgs_to_mirror_disabled_not_returned(initialized_db):
    """Test that disabled mirrors are not returned."""
    org = create_organization("testorg8", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg8",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    mirror.is_enabled = False
    mirror.save()

    iterator, next_token = orgs_to_mirror()
    if iterator:
        mirrors = list(iterator)
        assert not any(m.id == mirror.id for m in mirrors)


# Test claim_org_mirror


def test_claim_org_mirror_success(initialized_db):
    """Test successfully claiming a mirror."""
    org = create_organization("testorg9", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg9",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    original_txn_id = mirror.sync_transaction_id

    # Claim the mirror
    claimed = claim_org_mirror(mirror)

    assert claimed is not None
    assert claimed.sync_status == OrgMirrorStatus.SYNCING
    assert claimed.sync_expiration_date is not None
    assert claimed.sync_transaction_id != original_txn_id


def test_claim_org_mirror_already_claimed(initialized_db):
    """Test that claiming an already-claimed mirror returns None (optimistic locking)."""
    org = create_organization("testorg10", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg10",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # First claim succeeds
    claimed1 = claim_org_mirror(mirror)
    assert claimed1 is not None

    # Second claim with stale transaction ID fails
    claimed2 = claim_org_mirror(mirror)
    assert claimed2 is None


# Test release_org_mirror


def test_release_org_mirror_success(initialized_db):
    """Test releasing a mirror with SUCCESS status."""
    org = create_organization("testorg11", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg11",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Claim it
    claimed = claim_org_mirror(mirror)
    assert claimed is not None

    # Release with SUCCESS
    released = release_org_mirror(claimed, OrgMirrorStatus.SUCCESS)

    assert released is not None
    assert released.sync_status == OrgMirrorStatus.SUCCESS
    assert released.sync_expiration_date is None
    assert released.sync_retries_remaining == MAX_SYNC_RETRIES
    assert released.sync_start_date is not None  # Next sync time set


def test_release_org_mirror_failure(initialized_db):
    """Test releasing a mirror with FAIL status decrements retries."""
    org = create_organization("testorg12", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg12",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    # Claim it
    claimed = claim_org_mirror(mirror)
    assert claimed is not None

    original_retries = claimed.sync_retries_remaining

    # Release with FAIL
    released = release_org_mirror(claimed, OrgMirrorStatus.FAIL)

    assert released is not None
    assert released.sync_status == OrgMirrorStatus.FAIL
    assert released.sync_retries_remaining == original_retries - 1


# Test record_discovered_repos


def test_record_discovered_repos_new(initialized_db):
    """Test recording newly discovered repositories."""
    org = create_organization("testorg13", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg13",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    discovered = [
        {"name": "repo1", "external_reference": "harbor.example.com/project/repo1"},
        {"name": "repo2", "external_reference": "harbor.example.com/project/repo2"},
        {"name": "repo3", "external_reference": "harbor.example.com/project/repo3"},
    ]

    count = record_discovered_repos(mirror, discovered)

    assert count == 3

    repos = get_discovered_repos(mirror)
    assert len(repos) == 3
    assert all(r.status == OrgMirrorRepoStatus.DISCOVERED for r in repos)


def test_record_discovered_repos_existing_quay_repo(initialized_db):
    """Test that existing Quay repos are marked as SKIPPED."""
    org = create_organization("testorg14", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    # Create an existing repository in Quay
    existing_repo = create_repository("testorg14", "existingrepo", get_user("devtable"))

    mirror = create_org_mirror(
        "testorg14",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    discovered = [
        {"name": "existingrepo", "external_reference": "harbor.example.com/project/existingrepo"},
        {"name": "newrepo", "external_reference": "harbor.example.com/project/newrepo"},
    ]

    count = record_discovered_repos(mirror, discovered)

    # Only newrepo should be counted as new
    assert count == 1

    repos = get_discovered_repos(mirror)
    assert len(repos) == 2

    skipped = [r for r in repos if r.status == OrgMirrorRepoStatus.SKIPPED]
    discovered_repos = [r for r in repos if r.status == OrgMirrorRepoStatus.DISCOVERED]

    assert len(skipped) == 1
    assert skipped[0].repository_name == "existingrepo"
    assert len(discovered_repos) == 1
    assert discovered_repos[0].repository_name == "newrepo"


def test_record_discovered_repos_duplicate_call(initialized_db):
    """Test that calling record_discovered_repos multiple times doesn't duplicate."""
    org = create_organization("testorg15", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg15",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    discovered = [
        {"name": "repo1", "external_reference": "harbor.example.com/project/repo1"},
    ]

    # Record twice
    count1 = record_discovered_repos(mirror, discovered)
    count2 = record_discovered_repos(mirror, discovered)

    assert count1 == 1
    assert count2 == 0  # Should skip on second call

    repos = get_discovered_repos(mirror)
    assert len(repos) == 1


# Test get_discovered_repos


def test_get_discovered_repos_all(initialized_db):
    """Test retrieving all discovered repos."""
    org = create_organization("testorg16", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg16",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo2",
        external_repo_name="ext/repo2",
        status=OrgMirrorRepoStatus.CREATED,
    )

    repos = get_discovered_repos(mirror)
    assert len(repos) == 2


def test_get_discovered_repos_filtered(initialized_db):
    """Test filtering discovered repos by status."""
    org = create_organization("testorg17", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg17",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo2",
        external_repo_name="ext/repo2",
        status=OrgMirrorRepoStatus.CREATED,
    )

    discovered = get_discovered_repos(mirror, status=OrgMirrorRepoStatus.DISCOVERED)
    assert len(discovered) == 1
    assert discovered[0].repository_name == "repo1"


# Test repos_to_create


def test_repos_to_create(initialized_db):
    """Test getting repos ready for creation."""
    org = create_organization("testorg18", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg18",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo2",
        external_repo_name="ext/repo2",
        status=OrgMirrorRepoStatus.PENDING_SYNC,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo3",
        external_repo_name="ext/repo3",
        status=OrgMirrorRepoStatus.CREATED,
    )
    OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo4",
        external_repo_name="ext/repo4",
        status=OrgMirrorRepoStatus.SKIPPED,
    )

    repos = repos_to_create(mirror)

    assert len(repos) == 2
    names = [r.repository_name for r in repos]
    assert "repo1" in names
    assert "repo2" in names
    assert "repo3" not in names
    assert "repo4" not in names


# Test mark_repo_* functions


def test_mark_repo_created(initialized_db):
    """Test marking a repo as created."""
    org = create_organization("testorg19", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg19",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    org_mirror_repo = OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )

    created_repo = create_repository("testorg19", "repo1", get_user("devtable"))

    updated = mark_repo_created(org_mirror_repo, created_repo)

    assert updated.status == OrgMirrorRepoStatus.CREATED
    assert updated.repository.id == created_repo.id
    assert updated.last_sync_date is not None
    assert updated.last_error is None


def test_mark_repo_skipped(initialized_db):
    """Test marking a repo as skipped."""
    org = create_organization("testorg20", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg20",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    org_mirror_repo = OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )

    updated = mark_repo_skipped(org_mirror_repo, "Already exists")

    assert updated.status == OrgMirrorRepoStatus.SKIPPED
    assert updated.last_error == "Already exists"
    assert updated.last_sync_date is not None


def test_mark_repo_failed(initialized_db):
    """Test marking a repo as failed."""
    org = create_organization("testorg21", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg21",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    org_mirror_repo = OrgMirrorRepo.create(
        org_mirror=mirror,
        repository_name="repo1",
        external_repo_name="ext/repo1",
        status=OrgMirrorRepoStatus.DISCOVERED,
    )

    updated = mark_repo_failed(org_mirror_repo, "Permission denied")

    assert updated.status == OrgMirrorRepoStatus.FAILED
    assert updated.last_error == "Permission denied"
    assert updated.last_sync_date is not None


# Test concurrent access scenarios


def test_concurrent_claims(initialized_db):
    """Test that only one worker can claim a mirror (optimistic locking)."""
    org = create_organization("testorg22", "test@example.com", get_user("devtable"))
    robot = get_user("devtable+robot")

    mirror = create_org_mirror(
        "testorg22",
        "harbor.example.com/project",
        sync_interval=3600,
        internal_robot=robot,
        skopeo_timeout=300,
    )

    results = []

    def try_claim():
        # Re-fetch mirror to simulate different worker
        fresh_mirror = get_org_mirror_config("testorg22")
        result = claim_org_mirror(fresh_mirror)
        results.append(result)

    # Simulate two workers trying to claim simultaneously
    thread1 = Thread(target=try_claim)
    thread2 = Thread(target=try_claim)

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Only one should succeed
    successful_claims = [r for r in results if r is not None]
    assert len(successful_claims) == 1


# Test OrgMirrorToken


def test_org_mirror_token(initialized_db):
    """Test pagination token functionality."""
    token = OrgMirrorToken(100)
    assert token.min_id == 100
