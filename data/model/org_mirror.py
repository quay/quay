# -*- coding: utf-8 -*-
"""
Business logic for organization-level mirror configuration.
"""

from peewee import JOIN

from data.database import (
    OrgMirrorConfig,
    User,
)


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
