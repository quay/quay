"""
Caching layer for AI-generated descriptions.

This module provides caching functionality to avoid redundant LLM API calls
for generating image descriptions.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from data.cache.cache_key import CacheKey

logger = logging.getLogger(__name__)

# Default TTL for cached AI descriptions (7 days)
DEFAULT_CACHE_TTL = "7d"


def for_ai_description(
    namespace_name: str,
    repo_name: str,
    manifest_digest: str,
    cache_config: Optional[Dict[str, Any]] = None,
) -> CacheKey:
    """
    Returns a cache key for an AI-generated image description.

    Args:
        namespace_name: The namespace/organization name.
        repo_name: The repository name.
        manifest_digest: The manifest digest.
        cache_config: Optional cache configuration dict.

    Returns:
        CacheKey with appropriate TTL.
    """
    if cache_config is None:
        cache_config = {}

    cache_ttl = cache_config.get("ai_description_cache_ttl", DEFAULT_CACHE_TTL)
    key = f"ai_description__{namespace_name}_{repo_name}_{manifest_digest}"

    return CacheKey(key, cache_ttl)


class AIDescriptionCache:
    """
    Cache wrapper for AI-generated image descriptions.

    Provides a high-level interface for caching descriptions with
    proper error handling and metadata.
    """

    def __init__(self, data_model_cache, cache_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the cache wrapper.

        Args:
            data_model_cache: The underlying data model cache instance.
            cache_config: Optional cache configuration.
        """
        self.cache = data_model_cache
        self.cache_config = cache_config or {}

    def get(
        self,
        namespace_name: str,
        repo_name: str,
        manifest_digest: str,
    ) -> Optional[str]:
        """
        Get a cached description for an image.

        Args:
            namespace_name: The namespace/organization name.
            repo_name: The repository name.
            manifest_digest: The manifest digest.

        Returns:
            The cached description string, or None if not cached.
        """
        if self.cache is None:
            return None

        cache_key = for_ai_description(
            namespace_name, repo_name, manifest_digest, self.cache_config
        )

        try:
            # Use retrieve with a loader that returns None to just get the cached value
            result = self.cache.retrieve(cache_key, lambda: None)
            if result is not None and isinstance(result, dict):
                return result.get("description")
            return None
        except Exception as e:
            logger.warning(
                "Error retrieving cached AI description for %s/%s@%s: %s",
                namespace_name,
                repo_name,
                manifest_digest,
                e,
            )
            return None

    def set(
        self,
        namespace_name: str,
        repo_name: str,
        manifest_digest: str,
        description: str,
    ) -> None:
        """
        Store a description in the cache.

        Args:
            namespace_name: The namespace/organization name.
            repo_name: The repository name.
            manifest_digest: The manifest digest.
            description: The description to cache.
        """
        if self.cache is None:
            return

        cache_key = for_ai_description(
            namespace_name, repo_name, manifest_digest, self.cache_config
        )

        cache_data = {
            "description": description,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        try:
            # Use retrieve with a loader that returns the cache data
            self.cache.retrieve(cache_key, lambda: cache_data)
        except Exception as e:
            logger.warning(
                "Error caching AI description for %s/%s@%s: %s",
                namespace_name,
                repo_name,
                manifest_digest,
                e,
            )

    def invalidate(
        self,
        namespace_name: str,
        repo_name: str,
        manifest_digest: str,
    ) -> None:
        """
        Remove a cached description.

        Args:
            namespace_name: The namespace/organization name.
            repo_name: The repository name.
            manifest_digest: The manifest digest.
        """
        if self.cache is None:
            return

        cache_key = for_ai_description(
            namespace_name, repo_name, manifest_digest, self.cache_config
        )

        try:
            self.cache.invalidate(cache_key)
        except Exception as e:
            logger.warning(
                "Error invalidating cached AI description for %s/%s@%s: %s",
                namespace_name,
                repo_name,
                manifest_digest,
                e,
            )


def get_cached_description(
    cache,
    namespace_name: str,
    repo_name: str,
    manifest_digest: str,
    cache_config: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Helper function to get a cached description.

    Args:
        cache: The data model cache instance.
        namespace_name: The namespace/organization name.
        repo_name: The repository name.
        manifest_digest: The manifest digest.
        cache_config: Optional cache configuration.

    Returns:
        The cached description, or None if not cached.
    """
    if cache is None:
        return None

    ai_cache = AIDescriptionCache(cache, cache_config)
    return ai_cache.get(namespace_name, repo_name, manifest_digest)


def cache_description(
    cache,
    namespace_name: str,
    repo_name: str,
    manifest_digest: str,
    description: str,
    cache_config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Helper function to cache a description.

    Args:
        cache: The data model cache instance.
        namespace_name: The namespace/organization name.
        repo_name: The repository name.
        manifest_digest: The manifest digest.
        description: The description to cache.
        cache_config: Optional cache configuration.
    """
    if cache is None:
        return

    ai_cache = AIDescriptionCache(cache, cache_config)
    ai_cache.set(namespace_name, repo_name, manifest_digest, description)


def invalidate_description_cache(
    cache,
    namespace_name: str,
    repo_name: str,
    manifest_digest: str,
    cache_config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Helper function to invalidate a cached description.

    Args:
        cache: The data model cache instance.
        namespace_name: The namespace/organization name.
        repo_name: The repository name.
        manifest_digest: The manifest digest.
        cache_config: Optional cache configuration.
    """
    if cache is None:
        return

    ai_cache = AIDescriptionCache(cache, cache_config)
    ai_cache.invalidate(namespace_name, repo_name, manifest_digest)
