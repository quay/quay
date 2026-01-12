"""
AI-powered features API endpoints.

This module provides endpoints for managing AI settings and generating
descriptions for container images.
"""

import logging

from flask import request

import features
from features import FeatureNameValue

# Get the AI feature flag, defaulting to False if not configured
# Using getattr allows this module to load even when the feature is not in config
_AI_FEATURE = getattr(features, "AI", FeatureNameValue("AI", False))

from auth.auth_context import get_authenticated_user
from auth.permissions import (
    AdministerOrganizationPermission,
    AdministerRepositoryPermission,
    ReadRepositoryPermission,
)
from data import model
from data.model.organization_ai import (
    create_or_update_org_ai_settings,
    get_org_ai_settings,
    is_description_generator_enabled,
    mark_credentials_verified,
    set_org_ai_credentials,
    toggle_description_generator,
)
from endpoints.api import (
    ApiResource,
    RepositoryParamResource,
    log_action,
    nickname,
    path_param,
    request_error,
    require_repo_admin,
    require_repo_read,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import InvalidRequest, NotFound, Unauthorized
from util.ai.billing import check_ai_subscription_required, is_managed_mode
from util.ai.cache import AIDescriptionCache, cache_description, get_cached_description
from util.ai.history_extractor import ImageExtractionError, extract_image_analysis
from util.ai.providers import (
    ProviderAuthError,
    ProviderConfigError,
    ProviderFactory,
    ProviderRateLimitError,
    ProviderTimeoutError,
)
from util.ai.security import (
    filter_sensitive_env_vars,
    mask_api_key,
    sanitize_llm_response,
)

logger = logging.getLogger(__name__)

# Valid provider names
VALID_PROVIDERS = ["anthropic", "openai", "google", "deepseek", "custom"]


def _get_organization_or_user(orgname):
    """Get organization or user by name, raising NotFound if not found."""
    org = model.user.get_user_or_org(orgname)
    if org is None:
        raise NotFound()
    return org


def _require_org_admin(org):
    """Require admin permission on the organization or user namespace."""
    # For user namespaces, check if current user matches
    if not org.organization:
        user = get_authenticated_user()
        if user is None or user.username != org.username:
            raise Unauthorized()
        return

    # For organizations, use the standard permission check
    permission = AdministerOrganizationPermission(org.username)
    if not permission.can():
        raise Unauthorized()


@resource("/v1/organization/<orgname>/ai")
@path_param("orgname", "The name of the organization")
@show_if(_AI_FEATURE)
class OrganizationAISettings(ApiResource):
    """
    Resource for managing organization AI settings.
    """

    schemas = {
        "UpdateAISettings": {
            "type": "object",
            "properties": {
                "description_generator_enabled": {
                    "type": "boolean",
                    "description": "Whether AI description generation is enabled",
                },
                "provider": {
                    "type": "string",
                    "description": "LLM provider name",
                    "enum": VALID_PROVIDERS,
                },
                "model": {
                    "type": "string",
                    "description": "Model name to use",
                },
            },
        },
    }

    @nickname("getOrganizationAISettings")
    def get(self, orgname):
        """
        Get AI settings for the organization.
        """
        org = _get_organization_or_user(orgname)
        _require_org_admin(org)

        settings = get_org_ai_settings(org.username)

        return {
            "description_generator_enabled": (
                settings.description_generator_enabled if settings else False
            ),
            "provider": settings.provider if settings else None,
            "model": settings.model if settings else None,
            "endpoint": settings.endpoint if settings else None,
            "credentials_configured": (
                settings.api_key_encrypted is not None if settings else False
            ),
            "credentials_verified": settings.credentials_verified if settings else False,
        }

    @nickname("updateOrganizationAISettings")
    @validate_json_request("UpdateAISettings")
    def put(self, orgname):
        """
        Update AI settings for the organization.
        """
        org = _get_organization_or_user(orgname)
        _require_org_admin(org)

        req = request.get_json()

        # Validate provider if specified
        provider = req.get("provider")
        if provider and provider not in VALID_PROVIDERS:
            raise InvalidRequest(f"Invalid provider: {provider}")

        # Update settings
        settings = create_or_update_org_ai_settings(
            org.username,
            description_generator_enabled=req.get("description_generator_enabled"),
            provider=provider,
            model=req.get("model"),
        )

        log_action(
            "update_ai_settings",
            org.username,
            {"provider": provider, "model": req.get("model")},
        )

        return {
            "description_generator_enabled": settings.description_generator_enabled,
            "provider": settings.provider,
            "model": settings.model,
            "credentials_configured": settings.api_key_encrypted is not None,
            "credentials_verified": settings.credentials_verified,
        }


@resource("/v1/organization/<orgname>/ai/credentials")
@path_param("orgname", "The name of the organization")
@show_if(_AI_FEATURE)
class OrganizationAICredentials(ApiResource):
    """
    Resource for managing organization AI API credentials.
    """

    schemas = {
        "SetCredentials": {
            "type": "object",
            "required": ["provider", "api_key"],
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "LLM provider name",
                    "enum": VALID_PROVIDERS,
                },
                "api_key": {
                    "type": "string",
                    "description": "API key for the provider",
                },
                "model": {
                    "type": "string",
                    "description": "Model name to use",
                },
                "endpoint": {
                    "type": "string",
                    "description": "Custom endpoint URL (required for custom provider)",
                },
            },
        },
    }

    @nickname("setOrganizationAICredentials")
    @validate_json_request("SetCredentials")
    def put(self, orgname):
        """
        Set AI API credentials for the organization.
        """
        org = _get_organization_or_user(orgname)
        _require_org_admin(org)

        req = request.get_json()

        provider = req["provider"]
        api_key = req["api_key"]
        model = req.get("model")
        endpoint = req.get("endpoint")

        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise InvalidRequest(f"Invalid provider: {provider}")

        # Custom provider requires endpoint
        if provider == "custom" and not endpoint:
            raise InvalidRequest("Endpoint is required for custom provider")

        # Save credentials
        settings = set_org_ai_credentials(
            org.username,
            provider=provider,
            api_key=api_key,
            model=model,
            endpoint=endpoint,
        )

        log_action(
            "set_ai_credentials",
            org.username,
            {"provider": provider, "model": model},
        )

        return {
            "credentials_configured": True,
            "provider": settings.provider,
            "model": settings.model,
            "credentials_verified": settings.credentials_verified,
        }

    @nickname("deleteOrganizationAICredentials")
    def delete(self, orgname):
        """
        Delete AI API credentials for the organization.
        """
        org = _get_organization_or_user(orgname)
        _require_org_admin(org)

        # Clear credentials
        set_org_ai_credentials(
            org.username,
            provider=None,
            api_key=None,
            model=None,
            endpoint=None,
        )

        log_action("delete_ai_credentials", org.username, {})

        return "", 204


@resource("/v1/organization/<orgname>/ai/credentials/verify")
@path_param("orgname", "The name of the organization")
@show_if(_AI_FEATURE)
class OrganizationAICredentialsVerify(ApiResource):
    """
    Resource for verifying AI API credentials.
    """

    schemas = {
        "VerifyCredentials": {
            "type": "object",
            "required": ["provider", "api_key", "model"],
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "LLM provider name",
                    "enum": VALID_PROVIDERS,
                },
                "api_key": {
                    "type": "string",
                    "description": "API key to verify",
                },
                "model": {
                    "type": "string",
                    "description": "Model name to use",
                },
                "endpoint": {
                    "type": "string",
                    "description": "Custom endpoint URL",
                },
            },
        },
    }

    @nickname("verifyOrganizationAICredentials")
    @validate_json_request("VerifyCredentials")
    def post(self, orgname):
        """
        Verify AI API credentials.
        """
        org = _get_organization_or_user(orgname)
        _require_org_admin(org)

        req = request.get_json()

        provider = req["provider"]
        api_key = req["api_key"]
        model = req["model"]
        endpoint = req.get("endpoint")

        try:
            llm_provider = ProviderFactory.create(
                provider=provider,
                api_key=api_key,
                model=model,
                endpoint=endpoint,
            )

            success, error = llm_provider.verify_connectivity()

            if success:
                # Mark credentials as verified in database
                mark_credentials_verified(org.username, True)

                return {"valid": True}
            else:
                return {"valid": False, "error": error}

        except ProviderConfigError as e:
            return {"valid": False, "error": str(e)}
        except Exception as e:
            logger.exception("Error verifying AI credentials")
            return {"valid": False, "error": f"Verification failed: {str(e)}"}


@resource("/v1/repository/<apirepopath:repository>/ai/description")
@path_param("repository", "The full path of the repository (e.g., namespace/name)")
@show_if(_AI_FEATURE)
class RepositoryAIDescription(RepositoryParamResource):
    """
    Resource for generating AI descriptions for repository images.
    """

    schemas = {
        "GenerateDescription": {
            "type": "object",
            "required": ["tag"],
            "properties": {
                "tag": {
                    "type": "string",
                    "description": "Tag to generate description for",
                },
                "force_regenerate": {
                    "type": "boolean",
                    "description": "Force regeneration even if cached",
                    "default": False,
                },
            },
        },
    }

    @require_repo_admin()
    @nickname("generateAIDescription")
    @validate_json_request("GenerateDescription")
    def post(self, namespace_name, repo_name):
        """
        Generate an AI description for a repository image.
        """
        req = request.get_json()
        tag_name = req["tag"]
        force_regenerate = req.get("force_regenerate", False)

        # Get the repository
        repo = model.repository.get_repository(namespace_name, repo_name)
        if repo is None:
            raise NotFound()

        # Check if AI is enabled for this org/user
        owner = model.user.get_namespace_user(namespace_name)
        if owner is None:
            raise NotFound()

        # Check subscription requirements for managed mode (quay.io)
        allowed, error_message = check_ai_subscription_required(owner)
        if not allowed:
            raise InvalidRequest(error_message)

        # In managed mode, AI is always available for paid subscribers
        # In BYOK mode, check if the org has enabled and configured AI
        if not is_managed_mode():
            if not is_description_generator_enabled(owner.username):
                raise InvalidRequest(
                    "AI description generation is not enabled for this organization. "
                    "Please configure AI settings first."
                )

            # Get AI settings - required for BYOK mode
            settings = get_org_ai_settings(owner.username)
            if settings is None or not settings.api_key_encrypted:
                raise InvalidRequest(
                    "AI credentials are not configured. Please set up API credentials first."
                )
        else:
            # Managed mode - settings may exist for feature toggle but credentials not required
            settings = get_org_ai_settings(owner.username)

        # Get the tag and manifest using registry_model
        from data.registry_model import registry_model

        repo_ref = registry_model.lookup_repository(namespace_name, repo_name)
        if repo_ref is None:
            raise NotFound()

        tag = registry_model.get_repo_tag(repo_ref, tag_name)
        if tag is None:
            raise InvalidRequest(f"Tag '{tag_name}' not found")

        manifest = registry_model.get_manifest_for_tag(tag)
        if manifest is None:
            raise InvalidRequest("No manifest found for tag")

        manifest_digest = manifest.digest

        # Check cache first (unless force regenerate)
        if not force_regenerate:
            from app import model_cache

            cached = get_cached_description(model_cache, namespace_name, repo_name, manifest_digest)
            if cached:
                return {
                    "description": cached,
                    "cached": True,
                    "manifest_digest": manifest_digest,
                    "tag": tag_name,
                }

        # Extract image analysis
        try:
            # Get content retriever for blob access
            from app import storage
            from data.model.oci.retriever import RepositoryContentRetriever

            content_retriever = RepositoryContentRetriever(repo_ref.id, storage)

            # Get the parsed manifest for accessing the config
            parsed_manifest = manifest.get_parsed_manifest()

            image_analysis = extract_image_analysis(
                manifest=parsed_manifest,
                content_retriever=content_retriever,
                tag=tag_name,
            )

            # Filter sensitive environment variables before sending to LLM
            image_analysis.environment_vars = filter_sensitive_env_vars(
                image_analysis.environment_vars
            )
        except ImageExtractionError as e:
            raise InvalidRequest(f"Failed to extract image information: {str(e)}")

        # Create LLM provider and generate description
        try:
            if is_managed_mode():
                # Managed mode (quay.io) - use Quay's internal provider config
                provider = ProviderFactory.create_managed()
                provider_name = "managed"
            else:
                # BYOK mode - use org credentials
                api_key = settings.api_key_encrypted
                if hasattr(api_key, "decrypt"):
                    api_key = api_key.decrypt()

                provider = ProviderFactory.create(
                    provider=settings.provider,
                    api_key=api_key,
                    model=settings.model,
                    endpoint=settings.endpoint,
                )
                provider_name = settings.provider

            raw_description = provider.generate_description(image_analysis)
            # Sanitize the LLM response to prevent XSS and other attacks
            description = sanitize_llm_response(raw_description)
        except ProviderRateLimitError:
            raise InvalidRequest("Rate limit exceeded. Please try again later.")
        except ProviderAuthError:
            raise InvalidRequest("AI credentials are invalid. Please update your API key.")
        except ProviderTimeoutError:
            raise InvalidRequest(
                "The AI provider took too long to respond. This can happen with complex "
                "images or when the model is loading for the first time. Please try again."
            )
        except Exception as e:
            logger.exception("Error generating AI description")
            raise InvalidRequest(f"Failed to generate description: {str(e)}")

        # Cache the description
        from app import model_cache

        cache_description(model_cache, namespace_name, repo_name, manifest_digest, description)

        # Log the action
        log_action(
            "generate_ai_description",
            namespace_name,
            {
                "repository": repo_name,
                "tag": tag_name,
                "manifest_digest": manifest_digest,
                "provider": provider_name,
            },
        )

        return {
            "description": description,
            "cached": False,
            "manifest_digest": manifest_digest,
            "tag": tag_name,
        }


@resource("/v1/repository/<apirepopath:repository>/ai/description/tags")
@path_param("repository", "The full path of the repository")
@show_if(_AI_FEATURE)
class RepositoryAIDescriptionTags(RepositoryParamResource):
    """
    Resource for listing available tags for AI description generation.
    """

    @require_repo_read(allow_for_global_readonly_superuser=True)
    @nickname("listAIDescriptionTags")
    def get(self, namespace_name, repo_name):
        """
        List available tags for AI description generation.
        """
        from data.registry_model import registry_model

        repo_ref = registry_model.lookup_repository(namespace_name, repo_name)
        if repo_ref is None:
            raise NotFound()

        # Get tags (limited to 50 for performance)
        tags, _ = registry_model.list_repository_tag_history(
            repo_ref, page=1, size=50, active_tags_only=True
        )

        return {
            "tags": [
                {
                    "name": tag.name,
                    "manifest_digest": tag.manifest_digest,
                }
                for tag in tags
            ]
        }


@resource("/v1/repository/<apirepopath:repository>/ai/description/cached/<manifest_digest>")
@path_param("repository", "The full path of the repository")
@path_param("manifest_digest", "The manifest digest")
@show_if(_AI_FEATURE)
class RepositoryAIDescriptionCached(RepositoryParamResource):
    """
    Resource for retrieving cached AI descriptions.
    """

    @require_repo_read(allow_for_global_readonly_superuser=True)
    @nickname("getCachedAIDescription")
    def get(self, namespace_name, repo_name, manifest_digest):
        """
        Get a cached AI description for a manifest.
        """
        from app import model_cache

        description = get_cached_description(
            model_cache, namespace_name, repo_name, manifest_digest
        )

        return {
            "description": description,
            "cached": description is not None,
            "manifest_digest": manifest_digest,
        }
