# -*- coding: utf-8 -*-
"""
Business logic for organization-level mirror configuration.
"""

import fnmatch
from datetime import datetime
from typing import List, Optional, Tuple

from peewee import JOIN, IntegrityError

from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepoStatus,
    OrgMirrorRepository,
    OrgMirrorStatus,
    SourceRegistryType,
    User,
    Visibility,
    db_transaction,
)
from data.fields import DecryptedValue
from data.model import DataModelException
from util.names import parse_robot_username


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


def delete_org_mirror_config(org):
    """
    Delete the organization-level mirror configuration and all associated discovered repositories.

    Args:
        org: A User object representing the organization.

    Returns:
        True if the configuration was deleted, False if no configuration existed.
    """
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

    Args:
        config: The OrgMirrorConfig instance
        page: Page number (1-indexed)
        limit: Number of items per page
        status_filter: Optional filter by sync status

    Returns:
        Tuple of (list of OrgMirrorRepository instances, total count)
    """
    query = OrgMirrorRepository.select().where(OrgMirrorRepository.org_mirror_config == config)

    if status_filter is not None:
        query = query.where(OrgMirrorRepository.sync_status == status_filter)

    total = query.count()
    ordered_query = query.order_by(OrgMirrorRepository.repository_name)  # type: ignore[func-returns-value]
    repos = list(ordered_query.paginate(page, limit))

    return repos, total


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
