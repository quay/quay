"""
Data model for organization-level repository mirroring.

Provides data access layer for OrgMirrorConfig and OrgMirrorRepo with support for
distributed worker coordination via claim/release patterns and optimistic locking.
"""

from datetime import datetime, timedelta

from peewee import SQL, IntegrityError

from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepo,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    Repository,
    User,
    db_transaction,
    uuid_generator,
)
from data.fields import DecryptedValue
from data.model import DataModelException
from data.model.organization import get_organization
from data.model.repository import get_repository

# Configuration constants
MAX_SYNC_RETRIES = 3
MAX_SYNC_DURATION = 60 * 60  # 1 hour


class InvalidOrganizationException(DataModelException):
    """Raised when organization does not exist."""

    pass


# Organization Mirror Management


def get_org_mirror_config(org_name):
    """
    Get organization mirror configuration by organization name.

    Args:
        org_name: Name of the organization

    Returns:
        OrgMirrorConfig if found and enabled, None otherwise
    """
    try:
        return (
            OrgMirrorConfig.select()
            .join(User, on=(OrgMirrorConfig.organization == User.id))
            .where(
                (User.username == org_name)
                & (User.organization == True)
                & (OrgMirrorConfig.is_enabled == True)
            )
            .get()
        )
    except OrgMirrorConfig.DoesNotExist:
        return None


def create_org_mirror(
    org_name,
    external_reference,
    sync_interval,
    internal_robot,
    skopeo_timeout,
    external_registry_username=None,
    external_registry_password=None,
    external_registry_config=None,
    root_rule=None,
    is_enabled=True,
):
    """
    Create a new organization mirror configuration.

    Args:
        org_name: Name of the organization
        external_reference: External registry reference (e.g., "harbor.example.com/project")
        sync_interval: Sync interval in seconds
        internal_robot: Robot account for pulling/pushing
        skopeo_timeout: Timeout for skopeo operations in seconds
        external_registry_username: Optional username for external registry
        external_registry_password: Optional password for external registry
        external_registry_config: Optional additional config (dict)
        root_rule: Optional RepoMirrorRule for filtering
        is_enabled: Whether the mirror is enabled (default True)

    Returns:
        Created OrgMirrorConfig

    Raises:
        InvalidOrganizationException: If organization does not exist
    """
    org = get_organization(org_name)
    if not org:
        raise InvalidOrganizationException("Organization does not exist: %s" % org_name)

    username = DecryptedValue(external_registry_username) if external_registry_username else None
    password = DecryptedValue(external_registry_password) if external_registry_password else None

    return OrgMirrorConfig.create(
        organization=org,
        external_reference=external_reference,
        sync_interval=sync_interval,
        internal_robot=internal_robot,
        skopeo_timeout=skopeo_timeout,
        external_registry_username=username,
        external_registry_password=password,
        external_registry_config=external_registry_config or {},
        root_rule=root_rule,
        is_enabled=is_enabled,
    )


def delete_org_mirror(org_name):
    """
    Delete organization mirror configuration and all discovered repositories.

    Args:
        org_name: Name of the organization

    Returns:
        True if deleted, False if not found
    """
    org_mirror = get_org_mirror_config(org_name)
    if not org_mirror:
        return False

    with db_transaction():
        # Delete discovered repos first (cascading)
        OrgMirrorRepo.delete().where(OrgMirrorRepo.org_mirror == org_mirror).execute()

        # Delete the mirror config
        org_mirror.delete_instance()

    return True


# Claiming and Releasing for Workers


def orgs_to_mirror(start_token=None):
    """
    Return iterator of organization mirrors ready to sync.

    Returns organizations that are:
    - NEVER_RUN (never synced before)
    - SYNC_NOW (manual trigger)
    - SUCCESS with sync_interval expired
    - FAIL with retries remaining and sync_interval expired
    - SYNCING with expired expiration_date (stale)

    Args:
        start_token: Optional pagination token (OrgMirrorToken with min_id)

    Returns:
        Tuple of (iterator, next_token) or (None, None) if no work available
    """
    now = datetime.utcnow()

    query = (
        OrgMirrorConfig.select()
        .where(
            (OrgMirrorConfig.is_enabled == True)
            & (
                (OrgMirrorConfig.sync_status == OrgMirrorStatus.NEVER_RUN)
                | (OrgMirrorConfig.sync_status == OrgMirrorStatus.SYNC_NOW)
                | (
                    (OrgMirrorConfig.sync_status == OrgMirrorStatus.SUCCESS)
                    & (
                        SQL(
                            "sync_start_date + (sync_interval * INTERVAL '1 second') < %s",
                            [now],
                        )
                    )
                )
                | (
                    (OrgMirrorConfig.sync_status == OrgMirrorStatus.FAIL)
                    & (OrgMirrorConfig.sync_retries_remaining > 0)
                    & (
                        SQL(
                            "sync_start_date + (sync_interval * INTERVAL '1 second') < %s",
                            [now],
                        )
                    )
                )
                | (
                    (OrgMirrorConfig.sync_status == OrgMirrorStatus.SYNCING)
                    & (OrgMirrorConfig.sync_expiration_date < now)
                )
            )
        )
        .order_by(OrgMirrorConfig.id.asc())
    )

    if start_token:
        query = query.where(OrgMirrorConfig.id >= start_token.min_id)

    mirrors = list(query.limit(100))

    if not mirrors:
        return None, None

    def iterator():
        for mirror in mirrors:
            yield mirror

    # Create next token for pagination
    last_id = mirrors[-1].id if mirrors else None
    next_token = OrgMirrorToken(last_id + 1) if last_id else None

    return iterator(), next_token


def claim_org_mirror(mirror):
    """
    Claim an organization mirror for syncing using optimistic locking.

    Args:
        mirror: OrgMirrorConfig to claim

    Returns:
        Updated OrgMirrorConfig if claimed successfully, None if already claimed
    """
    with db_transaction():
        now = datetime.utcnow()
        expiration_date = now + timedelta(seconds=MAX_SYNC_DURATION)

        query = OrgMirrorConfig.update(
            sync_status=OrgMirrorStatus.SYNCING,
            sync_start_date=now,
            sync_expiration_date=expiration_date,
            sync_transaction_id=uuid_generator(),
        ).where(
            OrgMirrorConfig.id == mirror.id,
            OrgMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
        )

        updated = query.execute()
        if updated:
            return OrgMirrorConfig.get_by_id(mirror.id)
        else:
            return None  # Another worker claimed it


def release_org_mirror(mirror, sync_status):
    """
    Release an organization mirror after sync attempt.

    Args:
        mirror: OrgMirrorConfig to release
        sync_status: OrgMirrorStatus indicating result (SUCCESS, FAIL, CANCEL)

    Returns:
        Updated OrgMirrorConfig if released successfully, None otherwise
    """
    retries = mirror.sync_retries_remaining
    next_start_date = None

    if sync_status == OrgMirrorStatus.FAIL:
        retries = max(0, retries - 1)

    if sync_status == OrgMirrorStatus.SUCCESS or (
        sync_status == OrgMirrorStatus.FAIL and retries < 1
    ):
        now = datetime.utcnow()
        delta = now - mirror.sync_start_date
        delta_seconds = (delta.days * 24 * 60 * 60) + delta.seconds
        next_start_date = now + timedelta(
            seconds=mirror.sync_interval - (delta_seconds % mirror.sync_interval)
        )
        retries = MAX_SYNC_RETRIES

    with db_transaction():
        query = OrgMirrorConfig.update(
            sync_status=sync_status,
            sync_start_date=next_start_date,
            sync_expiration_date=None,
            sync_retries_remaining=retries,
            sync_transaction_id=uuid_generator(),
        ).where(
            OrgMirrorConfig.id == mirror.id,
            OrgMirrorConfig.sync_transaction_id == mirror.sync_transaction_id,
        )

        updated = query.execute()
        if updated:
            return OrgMirrorConfig.get_by_id(mirror.id)
        else:
            return None  # Another worker modified it


# Discovered Repository Management


def record_discovered_repos(org_mirror, discovered_repos):
    """
    Record newly discovered repositories for an organization mirror.

    Checks if repositories already exist in Quay and marks them as SKIPPED.
    New repositories are created with DISCOVERED status.

    Args:
        org_mirror: OrgMirrorConfig
        discovered_repos: List of dicts with 'name' and 'external_reference'

    Returns:
        Number of new repos discovered (not including skipped)
    """
    org_name = org_mirror.organization.username
    new_count = 0

    with db_transaction():
        for repo_info in discovered_repos:
            repo_name = repo_info["name"]
            external_ref = repo_info["external_reference"]

            # Check if already tracked
            try:
                existing = OrgMirrorRepo.get(
                    OrgMirrorRepo.org_mirror == org_mirror,
                    OrgMirrorRepo.repository_name == repo_name,
                )
                continue  # Already tracked, skip
            except OrgMirrorRepo.DoesNotExist:
                pass

            # Check if repository already exists in Quay
            existing_quay_repo = get_repository(org_name, repo_name)

            if existing_quay_repo:
                # Mark as skipped since it already exists
                OrgMirrorRepo.create(
                    org_mirror=org_mirror,
                    repository_name=repo_name,
                    external_repo_name=external_ref,
                    status=OrgMirrorRepoStatus.SKIPPED,
                    last_error="Repository already exists in Quay",
                )
            else:
                # New repository, mark as discovered
                OrgMirrorRepo.create(
                    org_mirror=org_mirror,
                    repository_name=repo_name,
                    external_repo_name=external_ref,
                    status=OrgMirrorRepoStatus.DISCOVERED,
                )
                new_count += 1

    return new_count


def get_discovered_repos(org_mirror, status=None):
    """
    Query discovered repositories for an organization mirror.

    Args:
        org_mirror: OrgMirrorConfig
        status: Optional OrgMirrorRepoStatus to filter by

    Returns:
        List of OrgMirrorRepo objects
    """
    query = OrgMirrorRepo.select().where(OrgMirrorRepo.org_mirror == org_mirror)

    if status is not None:
        query = query.where(OrgMirrorRepo.status == status)

    return list(query.order_by(OrgMirrorRepo.discovery_date.asc()))


def repos_to_create(org_mirror):
    """
    Get repositories ready for creation.

    Returns repositories with DISCOVERED or PENDING_SYNC status.

    Args:
        org_mirror: OrgMirrorConfig

    Returns:
        List of OrgMirrorRepo objects ready for creation
    """
    return list(
        OrgMirrorRepo.select()
        .where(
            (OrgMirrorRepo.org_mirror == org_mirror)
            & (
                (OrgMirrorRepo.status == OrgMirrorRepoStatus.DISCOVERED)
                | (OrgMirrorRepo.status == OrgMirrorRepoStatus.PENDING_SYNC)
            )
        )
        .order_by(OrgMirrorRepo.discovery_date.asc())
    )


def mark_repo_created(org_mirror_repo, repository):
    """
    Mark a discovered repository as successfully created.

    Args:
        org_mirror_repo: OrgMirrorRepo to update
        repository: Created Repository instance to link

    Returns:
        Updated OrgMirrorRepo
    """
    org_mirror_repo.status = OrgMirrorRepoStatus.CREATED
    org_mirror_repo.repository = repository
    org_mirror_repo.last_sync_date = datetime.utcnow()
    org_mirror_repo.last_error = None
    org_mirror_repo.save()
    return org_mirror_repo


def mark_repo_skipped(org_mirror_repo, reason):
    """
    Mark a discovered repository as skipped.

    Args:
        org_mirror_repo: OrgMirrorRepo to update
        reason: Reason for skipping

    Returns:
        Updated OrgMirrorRepo
    """
    org_mirror_repo.status = OrgMirrorRepoStatus.SKIPPED
    org_mirror_repo.last_sync_date = datetime.utcnow()
    org_mirror_repo.last_error = reason
    org_mirror_repo.save()
    return org_mirror_repo


def mark_repo_failed(org_mirror_repo, error):
    """
    Mark a discovered repository as failed to create.

    Args:
        org_mirror_repo: OrgMirrorRepo to update
        error: Error message

    Returns:
        Updated OrgMirrorRepo
    """
    org_mirror_repo.status = OrgMirrorRepoStatus.FAILED
    org_mirror_repo.last_sync_date = datetime.utcnow()
    org_mirror_repo.last_error = str(error)
    org_mirror_repo.save()
    return org_mirror_repo


def update_org_mirror_config(org_name, **updates):
    """
    Update organization mirror configuration.

    Args:
        org_name: Organization name
        **updates: Fields to update (is_enabled, external_reference, sync_interval, etc.)

    Returns:
        Updated OrgMirrorConfig

    Raises:
        ValueError: If org mirror doesn't exist
    """
    mirror = get_org_mirror_config(org_name)
    if not mirror:
        raise ValueError(f"Organization mirror not found: {org_name}")

    # Update fields
    for field, value in updates.items():
        if hasattr(mirror, field):
            setattr(mirror, field, value)
        else:
            raise ValueError(f"Invalid field: {field}")

    mirror.save()
    return mirror


def trigger_sync_now(mirror):
    """
    Trigger immediate sync for organization mirror.

    Sets sync_status to SYNC_NOW which signals the worker to process
    this mirror on the next iteration.

    Args:
        mirror: OrgMirrorConfig instance

    Returns:
        Updated OrgMirrorConfig
    """
    mirror.sync_status = OrgMirrorStatus.SYNC_NOW
    mirror.save()
    return mirror


# Pagination token class
class OrgMirrorToken:
    """Pagination token for orgs_to_mirror."""

    def __init__(self, min_id):
        self.min_id = min_id
