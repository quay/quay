# -*- coding: utf-8 -*-
"""
Business logic for organization-level mirror configuration.
"""

import fnmatch
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from peewee import JOIN, IntegrityError, fn

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
    db_transaction,
    uuid_generator,
)
from data.fields import DecryptedValue
from data.model import DataModelException
from util.names import parse_robot_username

# Constants for sync management
MAX_SYNC_RETRIES = 3
MAX_SYNC_DURATION = 60 * 60 * 12  # 12 hours


def get_org_mirror_config(org):
    """
    Return the OrgMirrorConfig associated with the given organization, or None if it doesn't exist.

    Args:
        org: A User object representing the organization.

    Returns:
        OrgMirrorConfig instance or None if not found.
    """
    try:
        return (
            OrgMirrorConfig.select(OrgMirrorConfig, User)
            .join(User, JOIN.LEFT_OUTER, on=(OrgMirrorConfig.internal_robot == User.id))
            .where(OrgMirrorConfig.organization == org)
            .get()
        )
    except OrgMirrorConfig.DoesNotExist:
        return None


def create_org_mirror_config(
    organization,
    internal_robot,
    external_registry_type,
    external_registry_url,
    external_namespace,
    visibility,
    sync_interval,
    sync_start_date,
    is_enabled=True,
    external_registry_username=None,
    external_registry_password=None,
    external_registry_config=None,
    repository_filters=None,
    skopeo_timeout=300,
):
    """
    Create an organization-level mirror configuration.

    Args:
        organization: User object representing the organization
        internal_robot: User object representing the robot account
        external_registry_type: SourceRegistryType enum value
        external_registry_url: URL of the source registry
        external_namespace: Namespace/project name in source registry
        visibility: Visibility object for created repositories
        sync_interval: Seconds between syncs
        sync_start_date: Initial sync datetime
        is_enabled: Whether mirroring is enabled (default: True)
        external_registry_username: Username for source registry auth (optional)
        external_registry_password: Password for source registry auth (optional)
        external_registry_config: Dict with TLS/proxy settings (optional)
        repository_filters: List of glob patterns for filtering (optional)
        skopeo_timeout: Timeout for Skopeo operations in seconds (default: 300)

    Returns:
        Created OrgMirrorConfig instance

    Raises:
        DataModelException: If robot doesn't belong to the organization or config already exists
    """
    if not internal_robot.robot:
        raise DataModelException("Robot account must belong to the organization")

    parsed = parse_robot_username(internal_robot.username)
    if parsed is None:
        raise DataModelException("Robot account must belong to the organization")

    namespace, _ = parsed
    if namespace != organization.username:
        raise DataModelException("Robot account must belong to the organization")

    with db_transaction():
        try:
            username = (
                DecryptedValue(external_registry_username) if external_registry_username else None
            )
            password = (
                DecryptedValue(external_registry_password) if external_registry_password else None
            )

            mirror = OrgMirrorConfig.create(
                organization=organization,
                is_enabled=is_enabled,
                external_registry_type=external_registry_type,
                external_registry_url=external_registry_url,
                external_namespace=external_namespace,
                external_registry_username=username,
                external_registry_password=password,
                external_registry_config=external_registry_config or {},
                internal_robot=internal_robot,
                repository_filters=repository_filters or [],
                visibility=visibility,
                sync_interval=sync_interval,
                sync_start_date=sync_start_date,
                sync_status=OrgMirrorStatus.NEVER_RUN,
                skopeo_timeout=skopeo_timeout,
            )

            return mirror

        except IntegrityError as e:
            raise DataModelException(
                "Mirror configuration already exists for this organization"
            ) from e


def update_org_mirror_config(
    org,
    is_enabled=None,
    external_registry_url=None,
    external_namespace=None,
    external_registry_username=None,
    external_registry_password=None,
    external_registry_config=None,
    internal_robot=None,
    repository_filters=None,
    visibility=None,
    sync_interval=None,
    sync_start_date=None,
    skopeo_timeout=None,
):
    """
    Update an organization-level mirror configuration.

    Only provided non-None values will be updated. To explicitly set a field to None,
    use a sentinel value (not supported for credential fields which use None to indicate
    "no change").

    Args:
        org: User object representing the organization
        is_enabled: Whether mirroring is enabled
        external_registry_url: URL of the source registry
        external_namespace: Namespace/project name in source registry
        external_registry_username: Username for source registry auth (None = no change)
        external_registry_password: Password for source registry auth (None = no change)
        external_registry_config: Dict with TLS/proxy settings
        internal_robot: User object representing the robot account
        repository_filters: List of glob patterns for filtering
        visibility: Visibility object for created repositories
        sync_interval: Seconds between syncs
        sync_start_date: Next sync datetime
        skopeo_timeout: Timeout for Skopeo operations in seconds

    Returns:
        Updated OrgMirrorConfig instance, or None if no config exists

    Raises:
        DataModelException: If robot doesn't belong to the organization
    """
    config = get_org_mirror_config(org)
    if config is None:
        return None

    # Validate robot belongs to organization if provided
    if internal_robot is not None:
        if not internal_robot.robot:
            raise DataModelException("Robot account must belong to the organization")

        parsed = parse_robot_username(internal_robot.username)
        if parsed is None:
            raise DataModelException("Robot account must belong to the organization")

        namespace, _ = parsed
        if namespace != org.username:
            raise DataModelException("Robot account must belong to the organization")

    with db_transaction():
        if is_enabled is not None:
            config.is_enabled = is_enabled
        if external_registry_url is not None:
            config.external_registry_url = external_registry_url
        if external_namespace is not None:
            config.external_namespace = external_namespace
        if external_registry_username is not None:
            config.external_registry_username = DecryptedValue(external_registry_username)
        if external_registry_password is not None:
            config.external_registry_password = DecryptedValue(external_registry_password)
        if external_registry_config is not None:
            config.external_registry_config = external_registry_config
        if internal_robot is not None:
            config.internal_robot = internal_robot
        if repository_filters is not None:
            config.repository_filters = repository_filters
        if visibility is not None:
            config.visibility = visibility
        if sync_interval is not None:
            config.sync_interval = sync_interval
        if sync_start_date is not None:
            config.sync_start_date = sync_start_date
        if skopeo_timeout is not None:
            config.skopeo_timeout = skopeo_timeout

        config.save()

    return config


def delete_org_mirror_config(org, config=None):
    """
    Delete the organization-level mirror configuration and all associated discovered repositories.

    Args:
        org: A User object representing the organization.
        config: Optional pre-fetched OrgMirrorConfig. If None, will be fetched.

    Returns:
        True if the configuration was deleted, False if no configuration existed.
    """
    if config is None:
        config = get_org_mirror_config(org)
    if config is None:
        return False

    with db_transaction():
        # Delete all associated discovered repositories first
        OrgMirrorRepository.delete().where(
            OrgMirrorRepository.org_mirror_config == config
        ).execute()

        # Delete the config
        config.delete_instance()

    return True


def matches_repository_filter(repository_name: str, filters: Optional[List[str]]) -> bool:
    """
    Check if a repository name matches any of the glob patterns.

    Args:
        repository_name: Name of the repository to check
        filters: List of glob patterns (e.g., ["ubuntu", "debian*", "alpine-*"])

    Returns:
        True if the repository matches any filter, or if filters is empty/None
    """
    if not filters:
        return True  # Empty filters = match all

    return any(fnmatch.fnmatch(repository_name, pattern) for pattern in filters)


def get_or_create_org_mirror_repo(
    config: OrgMirrorConfig,
    repository_name: str,
) -> Tuple[OrgMirrorRepository, bool]:
    """
    Get or create an OrgMirrorRepository entry for a discovered repository.

    Args:
        config: The OrgMirrorConfig instance
        repository_name: Name of the repository (without namespace prefix)

    Returns:
        Tuple of (OrgMirrorRepository instance, created: bool)
    """
    try:
        return (
            OrgMirrorRepository.get(
                (OrgMirrorRepository.org_mirror_config == config)
                & (OrgMirrorRepository.repository_name == repository_name)
            ),
            False,
        )
    except OrgMirrorRepository.DoesNotExist:
        return (
            OrgMirrorRepository.create(
                org_mirror_config=config,
                repository_name=repository_name,
                discovery_date=datetime.utcnow(),
                sync_status=OrgMirrorRepoStatus.NEVER_RUN,
                creation_date=datetime.utcnow(),
            ),
            True,
        )


def get_org_mirror_repos(
    config: OrgMirrorConfig,
    page: int = 1,
    limit: int = 100,
    status_filter: Optional[OrgMirrorRepoStatus] = None,
) -> Tuple[List[OrgMirrorRepository], int]:
    """
    Get a paginated list of discovered repositories for an organization mirror config.

    Excludes repositories that are marked for deletion.

    Args:
        config: The OrgMirrorConfig instance
        page: Page number (1-indexed)
        limit: Number of items per page
        status_filter: Optional filter by sync status

    Returns:
        Tuple of (list of OrgMirrorRepository instances, total count)
    """
    # Join with Repository to check state, use LEFT_OUTER since repository can be NULL
    query = (
        OrgMirrorRepository.select()
        .join(Repository, JOIN.LEFT_OUTER, on=(OrgMirrorRepository.repository == Repository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .where(
            # Include if repository is NULL (not yet created) or not marked for deletion
            (OrgMirrorRepository.repository >> None)
            | (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
    )

    if status_filter is not None:
        query = query.where(OrgMirrorRepository.sync_status == status_filter)

    total = query.count()
    ordered_query = query.order_by(OrgMirrorRepository.repository_name)  # type: ignore[func-returns-value]
    repos = list(ordered_query.paginate(page, limit))

    return repos, total


def get_org_mirroring_robot(repository):
    """
    Return the robot used for org-level mirroring of a repository.

    This is the org-level equivalent of repo_mirror.get_mirroring_robot().
    Used by v2auth to authorize push access for org-level mirrored repositories.

    Args:
        repository: Repository ID or Repository model instance

    Returns:
        User object representing the robot, or None if not found
    """
    try:
        # Handle both repository ID and model instance
        repo_id = repository if isinstance(repository, int) else repository.id

        org_mirror_repo = (
            OrgMirrorRepository.select(OrgMirrorRepository, OrgMirrorConfig, User)
            .join(OrgMirrorConfig)
            .join(User, JOIN.LEFT_OUTER, on=(OrgMirrorConfig.internal_robot == User.id))
            .where(OrgMirrorRepository.repository == repo_id)
            .get()
        )
        return org_mirror_repo.org_mirror_config.internal_robot
    except OrgMirrorRepository.DoesNotExist:
        return None


def sync_discovered_repos(
    config: OrgMirrorConfig,
    discovered_names: List[str],
) -> Tuple[int, int]:
    """
    Sync the discovered repository list with the database.

    Creates new OrgMirrorRepository entries for newly discovered repos.
    Does NOT delete repos that are no longer in the source (that's a separate operation).

    Args:
        config: The OrgMirrorConfig instance
        discovered_names: List of repository names discovered from source

    Returns:
        Tuple of (total_count, newly_created_count)
    """
    newly_created = 0

    with db_transaction():
        for repo_name in discovered_names:
            _, created = get_or_create_org_mirror_repo(config, repo_name)
            if created:
                newly_created += 1

    return len(discovered_names), newly_created


def get_eligible_org_mirror_repos():
    """
    Returns OrgMirrorRepository entries that are ready to sync.

    This includes repositories that are:
    1. Immediate candidates: Status is SYNC_NOW with no expiration date (manually triggered)
    2. Ready candidates: sync_start_date <= now, retries > 0, not currently syncing, enabled
    3. Expired candidates: Was syncing but sync_expiration_date <= now (stalled worker recovery)

    Only returns repos from enabled OrgMirrorConfig entries.

    Returns:
        Peewee query of eligible OrgMirrorRepository entries ordered by sync_start_date
    """
    now = datetime.utcnow()

    # Immediate candidates - Status is SYNC_NOW with no expiration date
    # These are manually triggered syncs that should run immediately
    immediate_candidates_filter = (
        OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.SYNC_NOW
    ) & (OrgMirrorRepository.sync_expiration_date >> None)

    # Ready candidates - scheduled syncs that are due
    # sync_start_date <= now: past due for sync
    # sync_retries_remaining > 0: has retry attempts left
    # sync_status != SYNCING: not currently being processed
    # sync_expiration_date IS NULL: no active claim on this repo
    ready_candidates_filter = (
        (OrgMirrorRepository.sync_start_date <= now)
        & (OrgMirrorRepository.sync_retries_remaining > 0)
        & (OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.SYNCING)
        & (OrgMirrorRepository.sync_expiration_date >> None)
    )

    # Expired candidates - stalled worker recovery
    # These were being synced but the worker died (expiration date passed)
    # sync_start_date <= now: was scheduled
    # sync_retries_remaining > 0: has retry attempts left
    # sync_status == SYNCING: was in progress
    # sync_expiration_date <= now: but claim expired
    expired_candidates_filter = (
        (OrgMirrorRepository.sync_start_date <= now)
        & (OrgMirrorRepository.sync_retries_remaining > 0)
        & (OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.SYNCING)
        & (OrgMirrorRepository.sync_expiration_date <= now)
    )

    return (
        OrgMirrorRepository.select()
        .join(OrgMirrorConfig)
        .where(OrgMirrorConfig.is_enabled == True)
        .where(immediate_candidates_filter | ready_candidates_filter | expired_candidates_filter)
        .order_by(OrgMirrorRepository.sync_start_date.asc())
    )


def get_max_id_for_org_mirror_repo():
    """
    Gets the maximum id for organization mirror repositories.

    Returns:
        Maximum ID value or None if no records exist
    """
    return OrgMirrorRepository.select(fn.Max(OrgMirrorRepository.id)).scalar()


def get_min_id_for_org_mirror_repo():
    """
    Gets the minimum id for organization mirror repositories.

    Returns:
        Minimum ID value or None if no records exist
    """
    return OrgMirrorRepository.select(fn.Min(OrgMirrorRepository.id)).scalar()


def claim_org_mirror_repo(org_mirror_repo: OrgMirrorRepository) -> Optional[OrgMirrorRepository]:
    """
    Claim an org mirror repo by updating its status and setting a new expiration time.

    Uses optimistic locking via sync_transaction_id to prevent concurrent claims.
    If the repo is already being synced (and not expired), or if another process claims it
    first, returns None.

    Args:
        org_mirror_repo: The OrgMirrorRepository to claim

    Returns:
        Updated OrgMirrorRepository if claim successful, None otherwise
    """
    with db_transaction():
        now = datetime.utcnow()
        expiration_date = now + timedelta(seconds=MAX_SYNC_DURATION)

        # If already syncing with valid expiration, cannot claim
        if org_mirror_repo.sync_status == OrgMirrorRepoStatus.SYNCING:
            if org_mirror_repo.sync_expiration_date and now <= org_mirror_repo.sync_expiration_date:
                return None

        # If expired, reset the repo for retry (stalled worker recovery)
        if org_mirror_repo.sync_expiration_date and now > org_mirror_repo.sync_expiration_date:
            expired_repo = expire_org_mirror_repo(org_mirror_repo)
            if expired_repo is None:
                return None
            org_mirror_repo = expired_repo

        # Attempt atomic update with optimistic locking
        query = OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.SYNCING,
            sync_expiration_date=expiration_date,
            sync_transaction_id=uuid_generator(),
        ).where(
            OrgMirrorRepository.id == org_mirror_repo.id,
            OrgMirrorRepository.sync_transaction_id == org_mirror_repo.sync_transaction_id,
            OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.CANCEL,
        )

        if query.execute():
            try:
                return OrgMirrorRepository.get_by_id(org_mirror_repo.id)
            except OrgMirrorRepository.DoesNotExist:
                return None
        return None


def check_org_mirror_repo_sync_status(org_mirror_repo: OrgMirrorRepository) -> OrgMirrorRepoStatus:
    """
    Returns the current sync status for a given org mirror repository.

    Used by the worker to detect cancel requests during sync.
    If the repository has been deleted (e.g., due to config deletion),
    returns CANCEL status to gracefully interrupt the sync.

    Args:
        org_mirror_repo: The OrgMirrorRepository to check

    Returns:
        The current OrgMirrorRepoStatus of the repository, or CANCEL if deleted
    """
    try:
        return OrgMirrorRepository.get(OrgMirrorRepository.id == org_mirror_repo.id).sync_status
    except OrgMirrorRepository.DoesNotExist:
        # Repo was deleted (e.g., config deleted mid-sync), treat as cancel signal
        return OrgMirrorRepoStatus.CANCEL


def release_org_mirror_repo(
    org_mirror_repo: OrgMirrorRepository,
    sync_status: OrgMirrorRepoStatus,
) -> Optional[OrgMirrorRepository]:
    """
    Release an org mirror repo after sync attempt and update its status.

    Calculates next sync_start_date based on parent config's sync_interval.
    Decrements retries on failure, resets on success or retry exhaustion.

    If mirroring is cancelled, the job will not be attempted until manual
    sync-now is triggered by the user.

    Args:
        org_mirror_repo: The OrgMirrorRepository to release
        sync_status: The result status (SUCCESS, FAIL, CANCEL, etc.)

    Returns:
        Updated OrgMirrorRepository if release successful, None otherwise
    """
    # Get parent config for sync_interval
    config = org_mirror_repo.org_mirror_config

    retries = org_mirror_repo.sync_retries_remaining
    next_start_date = None

    if sync_status == OrgMirrorRepoStatus.FAIL:
        retries = max(0, retries - 1)

    # On success or exhausted retries, schedule next sync
    if sync_status == OrgMirrorRepoStatus.SUCCESS or (
        sync_status == OrgMirrorRepoStatus.FAIL and retries < 1
    ):
        now = datetime.utcnow()
        if org_mirror_repo.sync_start_date:
            delta = now - org_mirror_repo.sync_start_date
            delta_seconds = (delta.days * 24 * 60 * 60) + delta.seconds
            next_start_date = now + timedelta(
                seconds=config.sync_interval - (delta_seconds % config.sync_interval)
            )
        else:
            # If no previous start date, just add interval from now
            next_start_date = now + timedelta(seconds=config.sync_interval)
        retries = MAX_SYNC_RETRIES
    else:
        # Keep current start date for retry
        next_start_date = org_mirror_repo.sync_start_date

    # If cancelled, stop syncing until user triggers sync-now again
    if sync_status == OrgMirrorRepoStatus.CANCEL:
        next_start_date = None
        retries = 0

    query = OrgMirrorRepository.update(
        sync_transaction_id=uuid_generator(),
        sync_status=sync_status,
        sync_start_date=next_start_date,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
        last_sync_date=datetime.utcnow(),
    ).where(
        OrgMirrorRepository.id == org_mirror_repo.id,
        OrgMirrorRepository.sync_transaction_id == org_mirror_repo.sync_transaction_id,
    )

    if query.execute():
        return OrgMirrorRepository.get_by_id(org_mirror_repo.id)

    return None


def expire_org_mirror_repo(org_mirror_repo: OrgMirrorRepository) -> Optional[OrgMirrorRepository]:
    """
    Expire a stalled org mirror repo to allow it to be picked up again.

    This is called when a worker dies and the sync_expiration_date has passed.
    Resets the repo state to allow another worker to claim it.

    Args:
        org_mirror_repo: The OrgMirrorRepository to expire

    Returns:
        Updated OrgMirrorRepository if successful, None otherwise
    """
    query = OrgMirrorRepository.update(
        sync_transaction_id=uuid_generator(),
        sync_expiration_date=None,
        sync_retries_remaining=MAX_SYNC_RETRIES,
        sync_status=OrgMirrorRepoStatus.NEVER_RUN,  # Reset status for re-processing
    ).where(
        OrgMirrorRepository.id == org_mirror_repo.id,
        OrgMirrorRepository.sync_transaction_id == org_mirror_repo.sync_transaction_id,
        OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.CANCEL,
    )

    if query.execute():
        try:
            return OrgMirrorRepository.get_by_id(org_mirror_repo.id)
        except OrgMirrorRepository.DoesNotExist:
            return None
    return None


# ==============================================================================
# OrgMirrorConfig-level functions (for discovery phase)
# ==============================================================================


def get_eligible_org_mirror_configs():
    """
    Returns OrgMirrorConfig entries that are ready for discovery sync.

    This includes configs that are:
    1. Immediate candidates: Status is SYNC_NOW with no expiration date (manually triggered)
    2. Cancel candidates: Status is CANCEL (need to propagate to repos, no discovery)
    3. Ready candidates: sync_start_date <= now, retries > 0, not currently syncing, enabled
    4. Expired candidates: Was syncing but sync_expiration_date <= now (stalled worker recovery)

    Returns:
        Peewee query of eligible OrgMirrorConfig entries ordered by sync_start_date
    """
    now = datetime.utcnow()

    # Immediate candidates - Status is SYNC_NOW with no expiration date
    immediate_candidates_filter = (OrgMirrorConfig.sync_status == OrgMirrorStatus.SYNC_NOW) & (
        OrgMirrorConfig.sync_expiration_date >> None
    )

    # Cancel candidates - Status is CANCEL, need to propagate to repos
    # No retries check since we set retries=0 when cancelling
    cancel_candidates_filter = (OrgMirrorConfig.sync_status == OrgMirrorStatus.CANCEL) & (
        OrgMirrorConfig.sync_expiration_date >> None
    )

    # Ready candidates - scheduled syncs that are due
    ready_candidates_filter = (
        (OrgMirrorConfig.sync_start_date <= now)
        & (OrgMirrorConfig.sync_retries_remaining > 0)
        & (OrgMirrorConfig.sync_status != OrgMirrorStatus.SYNCING)
        & (OrgMirrorConfig.sync_expiration_date >> None)
    )

    # Expired candidates - stalled worker recovery
    expired_candidates_filter = (
        (OrgMirrorConfig.sync_start_date <= now)
        & (OrgMirrorConfig.sync_retries_remaining > 0)
        & (OrgMirrorConfig.sync_status == OrgMirrorStatus.SYNCING)
        & (OrgMirrorConfig.sync_expiration_date <= now)
    )

    return (
        OrgMirrorConfig.select()
        .where(OrgMirrorConfig.is_enabled == True)
        .where(
            immediate_candidates_filter
            | cancel_candidates_filter
            | ready_candidates_filter
            | expired_candidates_filter
        )
        .order_by(OrgMirrorConfig.sync_start_date.asc())
    )


def get_max_id_for_org_mirror_config():
    """
    Gets the maximum id for organization mirror configs.

    Returns:
        Maximum ID value or None if no records exist
    """
    return OrgMirrorConfig.select(fn.Max(OrgMirrorConfig.id)).scalar()


def get_min_id_for_org_mirror_config():
    """
    Gets the minimum id for organization mirror configs.

    Returns:
        Minimum ID value or None if no records exist
    """
    return OrgMirrorConfig.select(fn.Min(OrgMirrorConfig.id)).scalar()


# Duration for discovery phase (shorter than repo sync since it's just API calls)
MAX_DISCOVERY_DURATION = 60 * 30  # 30 minutes


def claim_org_mirror_config(org_mirror_config: OrgMirrorConfig) -> Optional[OrgMirrorConfig]:
    """
    Claim an org mirror config for discovery by updating its status and setting expiration.

    Uses optimistic locking via sync_transaction_id to prevent concurrent claims.

    Args:
        org_mirror_config: The OrgMirrorConfig to claim

    Returns:
        Updated OrgMirrorConfig if claim successful, None otherwise
    """
    with db_transaction():
        now = datetime.utcnow()
        expiration_date = now + timedelta(seconds=MAX_DISCOVERY_DURATION)

        # If already syncing with valid expiration, cannot claim
        if org_mirror_config.sync_status == OrgMirrorStatus.SYNCING:
            if (
                org_mirror_config.sync_expiration_date
                and now <= org_mirror_config.sync_expiration_date
            ):
                return None

        # If expired, reset for retry (stalled worker recovery)
        if org_mirror_config.sync_expiration_date and now > org_mirror_config.sync_expiration_date:
            expire_org_mirror_config(org_mirror_config)
            org_mirror_config = OrgMirrorConfig.get_by_id(org_mirror_config.id)

        # Attempt atomic update with optimistic locking
        query = OrgMirrorConfig.update(
            sync_status=OrgMirrorStatus.SYNCING,
            sync_expiration_date=expiration_date,
            sync_transaction_id=uuid_generator(),
        ).where(
            OrgMirrorConfig.id == org_mirror_config.id,
            OrgMirrorConfig.sync_transaction_id == org_mirror_config.sync_transaction_id,
        )

        updated = query.execute()

    return OrgMirrorConfig.get_by_id(org_mirror_config.id) if updated else None


def release_org_mirror_config(
    org_mirror_config: OrgMirrorConfig,
    sync_status: OrgMirrorStatus,
    _repos_discovered: int = 0,
    _repos_created: int = 0,
) -> Optional[OrgMirrorConfig]:
    """
    Release an org mirror config after discovery and update its status.

    Calculates next sync_start_date based on sync_interval.
    Decrements retries on failure, resets on success.

    If discovery is cancelled, the job will not be attempted until manual
    sync-now is triggered by the user.

    Args:
        org_mirror_config: The OrgMirrorConfig to release
        sync_status: The result status (SUCCESS, FAIL, CANCEL, etc.)
        _repos_discovered: Number of repos discovered (reserved for future use)
        _repos_created: Number of new repos created (reserved for future use)

    Returns:
        Updated OrgMirrorConfig if release successful, None otherwise
    """
    retries = org_mirror_config.sync_retries_remaining
    next_start_date = None

    if sync_status == OrgMirrorStatus.FAIL:
        retries = max(0, retries - 1)

    # On success or exhausted retries, schedule next sync
    if sync_status == OrgMirrorStatus.SUCCESS or (
        sync_status == OrgMirrorStatus.FAIL and retries < 1
    ):
        now = datetime.utcnow()
        if org_mirror_config.sync_start_date:
            delta = now - org_mirror_config.sync_start_date
            delta_seconds = (delta.days * 24 * 60 * 60) + delta.seconds
            next_start_date = now + timedelta(
                seconds=org_mirror_config.sync_interval
                - (delta_seconds % org_mirror_config.sync_interval)
            )
        else:
            next_start_date = now + timedelta(seconds=org_mirror_config.sync_interval)
        retries = MAX_SYNC_RETRIES
    else:
        next_start_date = org_mirror_config.sync_start_date

    # If cancelled, stop syncing until user triggers sync-now again
    if sync_status == OrgMirrorStatus.CANCEL:
        next_start_date = None
        retries = 0

    query = OrgMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=sync_status,
        sync_start_date=next_start_date,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
    ).where(
        OrgMirrorConfig.id == org_mirror_config.id,
        OrgMirrorConfig.sync_transaction_id == org_mirror_config.sync_transaction_id,
    )

    if query.execute():
        return OrgMirrorConfig.get_by_id(org_mirror_config.id)

    return None


def expire_org_mirror_config(org_mirror_config: OrgMirrorConfig) -> Optional[OrgMirrorConfig]:
    """
    Expire a stalled org mirror config to allow it to be picked up again.

    Args:
        org_mirror_config: The OrgMirrorConfig to expire

    Returns:
        Updated OrgMirrorConfig if successful, None otherwise
    """
    query = OrgMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_expiration_date=None,
        sync_retries_remaining=MAX_SYNC_RETRIES,
        sync_status=OrgMirrorStatus.NEVER_RUN,
    ).where(
        OrgMirrorConfig.id == org_mirror_config.id,
        OrgMirrorConfig.sync_transaction_id == org_mirror_config.sync_transaction_id,
    )

    if query.execute():
        return OrgMirrorConfig.get_by_id(org_mirror_config.id)

    return None


def schedule_org_mirror_repos_for_sync(config: OrgMirrorConfig) -> int:
    """
    Schedule all NEVER_RUN repos under a config for immediate sync.

    Called after discovery to trigger the repo-level sync phase.

    Args:
        config: The OrgMirrorConfig whose repos should be scheduled

    Returns:
        Number of repos scheduled
    """
    now = datetime.utcnow()

    query = OrgMirrorRepository.update(
        sync_start_date=now,
        sync_retries_remaining=MAX_SYNC_RETRIES,
    ).where(
        OrgMirrorRepository.org_mirror_config == config,
        OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.NEVER_RUN,
        OrgMirrorRepository.sync_start_date >> None,  # Only if not already scheduled
    )

    return query.execute()


def propagate_status_to_repos(config: OrgMirrorConfig, status: OrgMirrorRepoStatus) -> int:
    """
    Propagate a sync status to all repos under this config that don't already have it.

    This is called by the worker after discovery to set the appropriate status
    on all discovered repositories.

    For CANCEL: updates all repos (including SYNCING) so workers can detect and stop.
    For SYNC_NOW: skips SYNCING repos to avoid interrupting active syncs.

    Args:
        config: The OrgMirrorConfig whose repos should be updated
        status: The status to propagate (SYNC_NOW, CANCEL, etc.)

    Returns:
        Number of repos updated
    """
    now = datetime.utcnow()

    base_where = (OrgMirrorRepository.org_mirror_config == config) & (
        OrgMirrorRepository.sync_status != status
    )

    if status == OrgMirrorRepoStatus.SYNC_NOW:
        query = OrgMirrorRepository.update(
            sync_status=status,
            sync_start_date=now,
            sync_retries_remaining=MAX_SYNC_RETRIES,
        ).where(base_where & (OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.SYNCING))
    elif status == OrgMirrorRepoStatus.CANCEL:
        query = OrgMirrorRepository.update(
            sync_status=status,
            sync_start_date=None,
            sync_retries_remaining=0,
        ).where(base_where)
    else:
        query = OrgMirrorRepository.update(sync_status=status).where(
            base_where & (OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.SYNCING)
        )

    return query.execute()


def update_sync_status_to_sync_now(org_mirror_config: OrgMirrorConfig) -> Optional[OrgMirrorConfig]:
    """
    Change the org mirror config sync status to SYNC_NOW for immediate sync.

    Sets sync_start_date to now for immediate pickup by the worker, and
    ensures at least one retry is available.

    Note: This only updates the config status. The worker will propagate
    SYNC_NOW to associated OrgMirrorRepository entries after discovery.

    Args:
        org_mirror_config: The OrgMirrorConfig to trigger sync for

    Returns:
        Updated OrgMirrorConfig if successful, None if currently syncing
    """
    # Cannot trigger sync-now if already syncing
    if org_mirror_config.sync_status == OrgMirrorStatus.SYNCING:
        return None

    retries = max(org_mirror_config.sync_retries_remaining, 1)
    now = datetime.utcnow()

    config_query = OrgMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=OrgMirrorStatus.SYNC_NOW,
        sync_start_date=now,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
    ).where(
        OrgMirrorConfig.id == org_mirror_config.id,
        OrgMirrorConfig.sync_transaction_id == org_mirror_config.sync_transaction_id,
    )

    if not config_query.execute():
        return None

    return OrgMirrorConfig.get_by_id(org_mirror_config.id)


def update_sync_status_to_cancel(org_mirror_config: OrgMirrorConfig) -> Optional[OrgMirrorConfig]:
    """
    Cancel an ongoing or pending sync for an org mirror config.

    Sets the config status to CANCEL. The cancel request is force-applied
    (ignores transaction ID) since we need to interrupt an active worker.
    This allows cancellation from any status except when already CANCEL.

    Note: This only updates the config status. The worker will propagate
    CANCEL to associated OrgMirrorRepository entries when it picks up
    the config.

    Args:
        org_mirror_config: The OrgMirrorConfig to cancel

    Returns:
        Updated OrgMirrorConfig if successfully cancelled, None if already CANCEL
    """
    # Only skip if already cancelled (idempotent)
    if org_mirror_config.sync_status == OrgMirrorStatus.CANCEL:
        return None

    # Force cancel the config (ignore transaction_id for interrupt)
    config_query = OrgMirrorConfig.update(
        sync_transaction_id=uuid_generator(),
        sync_status=OrgMirrorStatus.CANCEL,
        sync_expiration_date=None,
        sync_retries_remaining=0,
    ).where(OrgMirrorConfig.id == org_mirror_config.id)

    if not config_query.execute():
        return None

    return OrgMirrorConfig.get_by_id(org_mirror_config.id)
