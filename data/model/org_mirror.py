# -*- coding: utf-8 -*-
"""
Business logic for organization-level mirror configuration.
"""

from datetime import datetime

from peewee import IntegrityError, JOIN

from data.database import (
    OrgMirrorConfig,
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
    assert internal_robot.robot

    namespace, _ = parse_robot_username(internal_robot.username)
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

        except IntegrityError:
            raise DataModelException(
                "Mirror configuration already exists for this organization"
            )


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
