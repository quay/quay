"""
Model operations for OrganizationAISettings.

This module provides CRUD operations for managing AI feature settings
and credentials at the organization level.
"""
from datetime import datetime
from typing import Optional

from data.database import OrganizationAISettings, User
from data.model import InvalidOrganizationException, db_transaction


def _get_organization(org_name: str) -> User:
    """
    Get an organization by name.

    Raises InvalidOrganizationException if not found.
    """
    try:
        return User.get(username=org_name, organization=True)
    except User.DoesNotExist:
        raise InvalidOrganizationException(f"Organization does not exist: {org_name}")


def get_org_ai_settings(org_name: str) -> Optional[OrganizationAISettings]:
    """
    Get AI settings for an organization.

    Returns None if no settings exist or if the organization doesn't exist.
    """
    try:
        org = User.get(username=org_name, organization=True)
    except User.DoesNotExist:
        return None

    try:
        return OrganizationAISettings.get(OrganizationAISettings.organization == org)
    except OrganizationAISettings.DoesNotExist:
        return None


def create_or_update_org_ai_settings(
    org_name: str,
    description_generator_enabled: Optional[bool] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> OrganizationAISettings:
    """
    Create or update AI settings for an organization.

    Only updates fields that are explicitly provided (not None).
    """
    org = _get_organization(org_name)

    with db_transaction():
        try:
            settings = OrganizationAISettings.get(
                OrganizationAISettings.organization == org
            )
            # Update existing record
            if description_generator_enabled is not None:
                settings.description_generator_enabled = description_generator_enabled
            if provider is not None:
                settings.provider = provider
            if model is not None:
                settings.model = model
            if endpoint is not None:
                settings.endpoint = endpoint

            settings.updated_at = datetime.utcnow()
            settings.save()
            return settings

        except OrganizationAISettings.DoesNotExist:
            # Create new record
            settings = OrganizationAISettings.create(
                organization=org,
                description_generator_enabled=description_generator_enabled or False,
                provider=provider,
                model=model,
                endpoint=endpoint,
            )
            return settings


def _api_key_matches(encrypted_value, plaintext: str) -> bool:
    """
    Check if an encrypted API key matches a plaintext value.

    Handles the case where encrypted_value may be None or a LazyEncryptedValue.
    """
    if encrypted_value is None:
        return plaintext is None
    if plaintext is None:
        return False
    # LazyEncryptedValue provides .matches() for comparison
    return encrypted_value.matches(plaintext)


def set_org_ai_credentials(
    org_name: str,
    provider: str,
    api_key: str,
    model: str,
    endpoint: Optional[str] = None,
) -> OrganizationAISettings:
    """
    Set AI provider credentials for an organization.

    This resets the credentials_verified status since the credentials changed.
    """
    org = _get_organization(org_name)

    with db_transaction():
        try:
            settings = OrganizationAISettings.get(
                OrganizationAISettings.organization == org
            )

            # Check if credentials actually changed (requires re-verification)
            # Use .matches() for encrypted field comparison
            api_key_unchanged = _api_key_matches(settings.api_key_encrypted, api_key)
            credentials_changed = (
                settings.provider != provider
                or not api_key_unchanged
                or settings.model != model
                or settings.endpoint != endpoint
            )

            settings.provider = provider
            settings.api_key_encrypted = api_key
            settings.model = model
            settings.endpoint = endpoint
            settings.updated_at = datetime.utcnow()

            # Reset verification if credentials changed
            if credentials_changed:
                settings.credentials_verified = False
                settings.credentials_verified_at = None

            settings.save()
            return settings

        except OrganizationAISettings.DoesNotExist:
            # Create new record with credentials
            settings = OrganizationAISettings.create(
                organization=org,
                provider=provider,
                api_key_encrypted=api_key,
                model=model,
                endpoint=endpoint,
                credentials_verified=False,
            )
            return settings


def mark_credentials_verified(org_name: str, verified: bool) -> bool:
    """
    Mark an organization's AI credentials as verified or unverified.

    Returns True if the operation succeeded, False if no settings exist.
    """
    settings = get_org_ai_settings(org_name)
    if settings is None:
        return False

    settings.credentials_verified = verified
    if verified:
        settings.credentials_verified_at = datetime.utcnow()
    settings.updated_at = datetime.utcnow()
    settings.save()
    return True


def delete_org_ai_settings(org_name: str) -> bool:
    """
    Delete AI settings for an organization.

    Returns True if settings were deleted, False if they didn't exist.
    """
    settings = get_org_ai_settings(org_name)
    if settings is None:
        return False

    settings.delete_instance()
    return True


def is_description_generator_enabled(org_name: str) -> bool:
    """
    Check if the description generator feature is enabled for an organization.

    Returns False if no settings exist.
    """
    settings = get_org_ai_settings(org_name)
    if settings is None:
        return False

    return settings.description_generator_enabled


def toggle_description_generator(org_name: str, enabled: bool) -> OrganizationAISettings:
    """
    Enable or disable the description generator feature for an organization.

    Creates settings if they don't exist.
    """
    return create_or_update_org_ai_settings(
        org_name,
        description_generator_enabled=enabled,
    )
