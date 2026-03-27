# -*- coding: utf-8 -*-
"""
Business logic for organization-level mirror configuration.
"""

import fnmatch
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

from peewee import JOIN, IntegrityError, fn

import features
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    Repository,
    RepositoryState,
    User,
    db_for_update,
    db_transaction,
    uuid_generator,
)
from data.fields import DecryptedValue
from data.model import DataModelException
from data.model.immutability import namespace_has_immutability_policies
from util.names import parse_robot_username
from util.security.ssrf import validate_external_registry_url

# Sentinel value to distinguish "not provided" from "explicitly set to None"
_UNSET = object()

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


def is_namespace_org_mirrored(namespace: str) -> bool:
    """
    Return True if the given namespace is an organization with org-level mirroring enabled.

    Callers must gate on ``features.ORG_MIRROR`` before calling this function
    to avoid an unnecessary DB query when the feature is disabled.
    """
    return (
        OrgMirrorConfig.select()
        .join(User, on=(OrgMirrorConfig.organization == User.id))
        .where(User.username == namespace, User.organization == True)
        .exists()
    )


def get_org_mirror_config_count():
    """
    Return the total number of OrgMirrorConfig entries.
    """
    return OrgMirrorConfig.select().count()


def get_enabled_org_mirror_config_count():
    """
    Return the number of enabled OrgMirrorConfig entries.
    """
    return OrgMirrorConfig.select().where(OrgMirrorConfig.is_enabled == True).count()


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
    allowed_hosts=None,
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
        allowed_hosts: Optional list of hostnames/CIDRs that bypass SSRF blocklist

    Returns:
        Created OrgMirrorConfig instance

    Raises:
        DataModelException: If robot doesn't belong to the organization or config already exists
    """
    # Validate URL to prevent SSRF (CWE-918) - defense-in-depth
    # DNS resolution is skipped here; the API layer performs the full check.
    try:
        validate_external_registry_url(
            external_registry_url, resolve_dns=False, allowed_hosts=allowed_hosts
        )
    except ValueError as e:
        raise DataModelException(str(e))

    if not internal_robot.robot:
        raise DataModelException("Robot account must belong to the organization")

    parsed = parse_robot_username(internal_robot.username)
    if parsed is None:
        raise DataModelException("Robot account must belong to the organization")

    namespace, _ = parsed
    if namespace != organization.username:
        raise DataModelException("Robot account must belong to the organization")

    with db_transaction():
        # Lock the org row to serialize against concurrent repo creation
        db_for_update(User.select().where(User.id == organization.id)).get()

        if Repository.select().where(Repository.namespace_user == organization).exists():
            raise DataModelException(
                "Cannot create organization mirror: the organization already contains "
                "repositories. Organization mirroring requires an empty organization."
            )

        if features.IMMUTABLE_TAGS and namespace_has_immutability_policies(organization.id):
            raise DataModelException(
                "Cannot create organization mirror: the organization has immutability "
                "policies configured. Remove all namespace immutability policies first."
            )

        if features.PROXY_CACHE:
            from data.model.proxy_cache import has_proxy_cache_config

            if has_proxy_cache_config(organization.username):
                raise DataModelException(
                    "Cannot create organization mirror: the organization has a proxy cache "
                    "configuration. Remove the proxy cache configuration first."
                )

        # Check before INSERT to avoid poisoning the PostgreSQL transaction with
        # an IntegrityError (which puts the txn into an aborted state).
        if OrgMirrorConfig.select().where(OrgMirrorConfig.organization == organization).exists():
            raise DataModelException("Mirror configuration already exists for this organization")

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
    external_registry_username=_UNSET,
    external_registry_password=_UNSET,
    external_registry_config=None,
    internal_robot=None,
    repository_filters=None,
    visibility=None,
    sync_interval=None,
    sync_start_date=None,
    skopeo_timeout=None,
    allowed_hosts=None,
):
    """
    Update an organization-level mirror configuration.

    Only provided non-None values will be updated. Credential fields use
    the _UNSET sentinel as default so that passing None explicitly clears them.

    Args:
        org: User object representing the organization
        is_enabled: Whether mirroring is enabled
        external_registry_url: URL of the source registry
        external_namespace: Namespace/project name in source registry
        external_registry_username: Username for source registry auth (_UNSET = no change, None = clear)
        external_registry_password: Password for source registry auth (_UNSET = no change, None = clear)
        external_registry_config: Dict with TLS/proxy settings
        internal_robot: User object representing the robot account
        repository_filters: List of glob patterns for filtering
        visibility: Visibility object for created repositories
        sync_interval: Seconds between syncs
        sync_start_date: Next sync datetime
        skopeo_timeout: Timeout for Skopeo operations in seconds
        allowed_hosts: Optional list of hostnames/CIDRs that bypass SSRF blocklist

    Returns:
        Updated OrgMirrorConfig instance, or None if no config exists

    Raises:
        DataModelException: If robot doesn't belong to the organization
    """
    config = get_org_mirror_config(org)
    if config is None:
        return None

    # Validate URL to prevent SSRF (CWE-918) - defense-in-depth
    # DNS resolution is skipped here; the API layer performs the full check.
    if external_registry_url is not None:
        try:
            validate_external_registry_url(
                external_registry_url, resolve_dns=False, allowed_hosts=allowed_hosts
            )
        except ValueError as e:
            raise DataModelException(str(e))

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
        if external_registry_username is not _UNSET:
            config.external_registry_username = (
                DecryptedValue(external_registry_username) if external_registry_username else None
            )
        if external_registry_password is not _UNSET:
            config.external_registry_password = (
                DecryptedValue(external_registry_password) if external_registry_password else None
            )
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


def delete_org_mirror_config(config):
    """
    Delete the organization-level mirror configuration and all associated discovered repositories.

    Args:
        config: The OrgMirrorConfig instance to delete.

    Returns:
        True if the configuration was deleted.
    """
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


def get_org_mirror_repo_status_counts(config: OrgMirrorConfig) -> dict:
    """
    Get counts of discovered repositories grouped by sync status.

    Uses the composite index on (org_mirror_config, sync_status).
    Excludes repos marked for deletion (same filter as get_org_mirror_repos).
    """
    query = (
        OrgMirrorRepository.select(
            OrgMirrorRepository.sync_status,
            fn.COUNT(OrgMirrorRepository.id).alias("count"),
        )
        .join(Repository, JOIN.LEFT_OUTER, on=(OrgMirrorRepository.repository == Repository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .where(
            (OrgMirrorRepository.repository >> None)
            | (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
        .group_by(OrgMirrorRepository.sync_status)
    )

    counts = {status.name: 0 for status in OrgMirrorRepoStatus}
    for row in query:
        counts[row.sync_status.name] = row.count
    return counts


def count_active_org_mirror_repos(config: OrgMirrorConfig) -> int:
    """
    Count repositories that haven't reached a terminal state.

    Active (non-terminal) repos:
    - SYNCING, SYNC_NOW, NEVER_RUN: always active
    - FAIL with sync_retries_remaining > 0: will be retried by the worker

    Terminal repos (not counted):
    - SUCCESS, CANCEL
    - FAIL with sync_retries_remaining == 0 (retries exhausted)

    This aligns with get_eligible_org_mirror_repos which considers FAIL repos
    with remaining retries as eligible for pickup.
    """
    always_active = [
        OrgMirrorRepoStatus.SYNCING,
        OrgMirrorRepoStatus.SYNC_NOW,
        OrgMirrorRepoStatus.NEVER_RUN,
    ]

    return (
        OrgMirrorRepository.select(fn.COUNT(OrgMirrorRepository.id))
        .join(Repository, JOIN.LEFT_OUTER, on=(OrgMirrorRepository.repository == Repository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .where(
            (OrgMirrorRepository.repository >> None)
            | (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
        .where(
            (OrgMirrorRepository.sync_status << always_active)
            | (
                (OrgMirrorRepository.sync_status == OrgMirrorRepoStatus.FAIL)
                & (OrgMirrorRepository.sync_retries_remaining > 0)
            )
        )
        .scalar()
    )


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

    Uses batch SELECT + INSERT to avoid N+1 queries.

    Args:
        config: The OrgMirrorConfig instance
        discovered_names: List of repository names discovered from source

    Returns:
        Tuple of (total_count, newly_created_count)
    """
    if not discovered_names:
        return 0, 0

    # Deduplicate while preserving order
    discovered_names = list(dict.fromkeys(discovered_names))

    # COUNT before transaction to measure net rows created accurately.
    # The FK column org_mirror_config_id is indexed, so this is cheap.
    count_before = (
        OrgMirrorRepository.select(fn.COUNT(OrgMirrorRepository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .scalar()
    )

    with db_transaction():
        # Batch SELECT: fetch all existing repo names in one query
        # Chunk the IN clause for SQLite compatibility (max ~999 variables)
        existing_names: Set[str] = set()
        for i in range(0, len(discovered_names), 900):
            chunk = discovered_names[i : i + 900]
            existing_names.update(
                row.repository_name
                for row in OrgMirrorRepository.select(OrgMirrorRepository.repository_name).where(
                    (OrgMirrorRepository.org_mirror_config == config)
                    & (OrgMirrorRepository.repository_name << chunk)
                )
            )

        # Filter to only new repos
        new_names = [name for name in discovered_names if name not in existing_names]

        # Batch INSERT: bulk insert all new repos
        if new_names:
            now = datetime.utcnow()
            rows = [
                {
                    "org_mirror_config": config,
                    "repository_name": name,
                    "discovery_date": now,
                    "sync_status": OrgMirrorRepoStatus.NEVER_RUN,
                    "creation_date": now,
                    "sync_retries_remaining": MAX_SYNC_RETRIES,
                    "sync_transaction_id": uuid_generator(),
                }
                for name in new_names
            ]
            # Chunk inserts for SQLite compatibility
            for i in range(0, len(rows), 100):
                OrgMirrorRepository.insert_many(rows[i : i + 100]).on_conflict_ignore().execute()

    count_after = (
        OrgMirrorRepository.select(fn.COUNT(OrgMirrorRepository.id))
        .where(OrgMirrorRepository.org_mirror_config == config)
        .scalar()
    )

    return len(discovered_names), count_after - count_before


def deactivate_excluded_repos(
    config: OrgMirrorConfig,
    active_repo_names: List[str],
    source_repo_names: Optional[List[str]] = None,
) -> int:
    """
    Mark repos as SKIP when no longer in the active list, and re-activate
    previously SKIP'd repos that have returned.

    This is called after discovery to handle repos that were deleted from
    the source registry or filtered out by repository filters.

    Args:
        config: The OrgMirrorConfig instance
        active_repo_names: Post-filter list of repo names from the source registry.
            An empty list will SKIP all tracked repos. The caller is responsible
            for guarding against transient source-registry failures (e.g. by not
            calling this function when the source returned no repos at all).
        source_repo_names: Pre-filter list of repo names from the source registry.
            When provided, repos not in this list are marked as "no longer in source"
            while repos in source but not in active are marked as "excluded by filters".
            When None, a generic message is used.

    Returns:
        Number of repos newly deactivated (set to SKIP)
    """

    active_set = set(active_repo_names)
    source_set = set(source_repo_names) if source_repo_names is not None else None

    # Fetch all repos for this config with their current status
    all_repos = list(
        OrgMirrorRepository.select(
            OrgMirrorRepository.id,
            OrgMirrorRepository.repository_name,
            OrgMirrorRepository.sync_status,
        ).where(OrgMirrorRepository.org_mirror_config == config)
    )

    # Repos not in active list and not already SKIP → mark SKIP
    repos_to_skip = [
        r
        for r in all_repos
        if r.repository_name not in active_set and r.sync_status != OrgMirrorRepoStatus.SKIP
    ]

    # Repos currently SKIP but back in active list → reactivate to NEVER_RUN
    to_reactivate = [
        r.id
        for r in all_repos
        if r.repository_name in active_set and r.sync_status == OrgMirrorRepoStatus.SKIP
    ]

    # Categorize skipped repos by reason when source list is available
    if source_set is not None:
        vanished_ids = [r.id for r in repos_to_skip if r.repository_name not in source_set]
        filtered_ids = [r.id for r in repos_to_skip if r.repository_name in source_set]
    else:
        vanished_ids = [r.id for r in repos_to_skip]
        filtered_ids = []

    skip_fields = dict(
        sync_status=OrgMirrorRepoStatus.SKIP,
        sync_start_date=None,
        sync_expiration_date=None,
        sync_retries_remaining=0,
    )

    # Chunk updates for SQLite compatibility (max ~999 variables)
    for i in range(0, len(vanished_ids), 900):
        chunk = vanished_ids[i : i + 900]
        OrgMirrorRepository.update(
            status_message="Repository no longer in source registry",
            **skip_fields,
        ).where(OrgMirrorRepository.id << chunk).execute()

    for i in range(0, len(filtered_ids), 900):
        chunk = filtered_ids[i : i + 900]
        OrgMirrorRepository.update(
            status_message="Repository excluded by filters",
            **skip_fields,
        ).where(OrgMirrorRepository.id << chunk).execute()

    for i in range(0, len(to_reactivate), 900):
        chunk = to_reactivate[i : i + 900]
        OrgMirrorRepository.update(
            sync_status=OrgMirrorRepoStatus.NEVER_RUN,
            status_message=None,
            sync_retries_remaining=MAX_SYNC_RETRIES,
        ).where(OrgMirrorRepository.id << chunk).execute()

    return len(repos_to_skip)


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
    status_message: Optional[str] = None,
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
        status_message: Optional message explaining the status (cleared on SUCCESS)

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

    # Clear status_message on success, persist on failure
    persisted_message = None if sync_status == OrgMirrorRepoStatus.SUCCESS else status_message

    query = OrgMirrorRepository.update(
        sync_transaction_id=uuid_generator(),
        sync_status=sync_status,
        sync_start_date=next_start_date,
        sync_expiration_date=None,
        sync_retries_remaining=retries,
        last_sync_date=datetime.utcnow(),
        status_message=persisted_message,
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


# Default duration for discovery phase (shorter than repo sync since it's just API calls)
DEFAULT_MAX_DISCOVERY_DURATION = 60 * 30  # 30 minutes


def claim_org_mirror_config(
    org_mirror_config: OrgMirrorConfig,
    max_discovery_duration: Optional[int] = None,
) -> Optional[OrgMirrorConfig]:
    """
    Claim an org mirror config for discovery by updating its status and setting expiration.

    Uses optimistic locking via sync_transaction_id to prevent concurrent claims.

    Args:
        org_mirror_config: The OrgMirrorConfig to claim
        max_discovery_duration: Maximum seconds for discovery claim. Defaults to
            ORG_MIRROR_MAX_DISCOVERY_DURATION from app config, or 1800s (30 minutes).

    Returns:
        Updated OrgMirrorConfig if claim successful, None otherwise
    """
    if max_discovery_duration is None:
        from app import app

        try:
            max_discovery_duration = int(
                app.config.get("ORG_MIRROR_MAX_DISCOVERY_DURATION", DEFAULT_MAX_DISCOVERY_DURATION)
            )
        except (ValueError, TypeError):
            max_discovery_duration = DEFAULT_MAX_DISCOVERY_DURATION

        if max_discovery_duration < 1:
            max_discovery_duration = DEFAULT_MAX_DISCOVERY_DURATION

    with db_transaction():
        now = datetime.utcnow()
        expiration_date = now + timedelta(seconds=max_discovery_duration)

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

    base_where = (
        (OrgMirrorRepository.org_mirror_config == config)
        & (OrgMirrorRepository.sync_status != status)
        & (OrgMirrorRepository.sync_status != OrgMirrorRepoStatus.SKIP)
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


def update_sync_status_to_sync_now(
    org_mirror_config: OrgMirrorConfig,
) -> tuple[Optional[OrgMirrorConfig], Optional[str]]:
    """
    Change the org mirror config sync status to SYNC_NOW for immediate sync.

    Sets sync_start_date to now for immediate pickup by the worker, and
    ensures at least one retry is available.

    Note: This only updates the config status. The worker will propagate
    SYNC_NOW to associated OrgMirrorRepository entries after discovery.

    Args:
        org_mirror_config: The OrgMirrorConfig to trigger sync for

    Returns:
        (updated_config, None) on success, or (None, reason) on rejection.
        Rejection reasons:
        - Config is in SYNCING state (discovery in progress)
        - Repositories are still actively syncing or pending worker pickup
    """
    # Cannot trigger sync-now if config is actively being discovered
    if org_mirror_config.sync_status == OrgMirrorStatus.SYNCING:
        return None, "Cannot trigger sync: discovery is currently in progress."

    # Cannot trigger sync-now if repositories are still actively syncing,
    # pending worker pickup, or awaiting retry. This includes FAIL repos with
    # retries remaining, matching the eligibility predicate in
    # get_eligible_org_mirror_repos.
    active = count_active_org_mirror_repos(org_mirror_config)
    if active > 0:
        return None, (
            "Cannot trigger sync: repositories are still syncing. "
            "Cancel the current sync and wait for all repositories to "
            "reach a terminal state before triggering a new sync."
        )

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
        return None, "Cannot trigger sync: concurrent update conflict."

    return OrgMirrorConfig.get_by_id(org_mirror_config.id), None


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
