"""
Tests for AI description caching.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from util.ai.cache import (
    AIDescriptionCache,
    get_cached_description,
    cache_description,
    invalidate_description_cache,
    for_ai_description,
    DEFAULT_CACHE_TTL,
)


class TestCacheKeyFunction:
    """Tests for the cache key generation function."""

    def test_generates_cache_key_with_digest(self):
        """Test that cache key includes manifest digest."""
        cache_key = for_ai_description(
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )

        assert "sha256:abc123" in cache_key.key
        assert "myorg" in cache_key.key
        assert "myrepo" in cache_key.key

    def test_cache_key_has_expiration(self):
        """Test that cache key has TTL set."""
        cache_key = for_ai_description(
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )

        assert cache_key.expiration is not None

    def test_cache_key_respects_config_ttl(self):
        """Test that cache key uses config TTL when provided."""
        cache_key = for_ai_description(
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
            cache_config={"ai_description_cache_ttl": "1d"},
        )

        assert cache_key.expiration == "1d"

    def test_cache_key_uses_default_ttl(self):
        """Test that cache key uses default TTL when not configured."""
        cache_key = for_ai_description(
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
            cache_config={},
        )

        assert cache_key.expiration == DEFAULT_CACHE_TTL

    def test_different_digests_different_keys(self):
        """Test that different digests produce different keys."""
        key1 = for_ai_description("org", "repo", "sha256:abc")
        key2 = for_ai_description("org", "repo", "sha256:def")

        assert key1.key != key2.key

    def test_different_repos_different_keys(self):
        """Test that different repos produce different keys."""
        key1 = for_ai_description("org", "repo1", "sha256:abc")
        key2 = for_ai_description("org", "repo2", "sha256:abc")

        assert key1.key != key2.key


class TestAIDescriptionCache:
    """Tests for the AIDescriptionCache class."""

    def test_get_returns_none_when_not_cached(self):
        """Test that get returns None when description is not cached."""
        mock_cache = MagicMock()
        mock_cache.retrieve.return_value = None

        ai_cache = AIDescriptionCache(mock_cache)
        result = ai_cache.get("myorg", "myrepo", "sha256:abc123")

        assert result is None

    def test_get_returns_cached_description(self):
        """Test that get returns cached description."""
        mock_cache = MagicMock()
        cached_data = {
            "description": "This is a Node.js web server image.",
            "generated_at": "2024-01-15T10:00:00Z",
        }
        mock_cache.retrieve.return_value = cached_data

        ai_cache = AIDescriptionCache(mock_cache)
        result = ai_cache.get("myorg", "myrepo", "sha256:abc123")

        assert result == "This is a Node.js web server image."

    def test_set_stores_description(self):
        """Test that set stores description in cache."""
        mock_cache = MagicMock()
        # Make retrieve call the loader to store the value
        mock_cache.retrieve.side_effect = lambda key, loader, **kwargs: loader()

        ai_cache = AIDescriptionCache(mock_cache)
        ai_cache.set("myorg", "myrepo", "sha256:abc123", "Test description")

        mock_cache.retrieve.assert_called_once()

    def test_invalidate_removes_cached_description(self):
        """Test that invalidate removes the cached description."""
        mock_cache = MagicMock()

        ai_cache = AIDescriptionCache(mock_cache)
        ai_cache.invalidate("myorg", "myrepo", "sha256:abc123")

        mock_cache.invalidate.assert_called_once()


class TestCacheHelperFunctions:
    """Tests for the cache helper functions."""

    def test_get_cached_description_with_no_cache(self):
        """Test get_cached_description returns None when no cache configured."""
        result = get_cached_description(
            cache=None,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )

        assert result is None

    def test_get_cached_description_returns_value(self):
        """Test get_cached_description returns cached value."""
        mock_cache = MagicMock()
        cached_data = {
            "description": "Cached description",
            "generated_at": "2024-01-15T10:00:00Z",
        }
        mock_cache.retrieve.return_value = cached_data

        result = get_cached_description(
            cache=mock_cache,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )

        assert result == "Cached description"

    def test_cache_description_stores_value(self):
        """Test cache_description stores the description."""
        mock_cache = MagicMock()
        mock_cache.retrieve.side_effect = lambda key, loader, **kwargs: loader()

        cache_description(
            cache=mock_cache,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
            description="New description",
        )

        mock_cache.retrieve.assert_called_once()

    def test_cache_description_does_nothing_with_no_cache(self):
        """Test cache_description does nothing when cache is None."""
        # Should not raise
        cache_description(
            cache=None,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
            description="New description",
        )

    def test_invalidate_description_cache_removes_value(self):
        """Test invalidate_description_cache removes the cached value."""
        mock_cache = MagicMock()

        invalidate_description_cache(
            cache=mock_cache,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )

        mock_cache.invalidate.assert_called_once()

    def test_invalidate_description_cache_does_nothing_with_no_cache(self):
        """Test invalidate_description_cache does nothing when cache is None."""
        # Should not raise
        invalidate_description_cache(
            cache=None,
            namespace_name="myorg",
            repo_name="myrepo",
            manifest_digest="sha256:abc123",
        )


class TestCacheIntegrationWithInMemory:
    """Integration tests using in-memory cache."""

    def test_round_trip_cache_and_retrieve(self):
        """Test storing and retrieving from cache."""
        from data.cache import InMemoryDataModelCache

        memory_cache = InMemoryDataModelCache({})
        ai_cache = AIDescriptionCache(memory_cache)

        # Store a description
        ai_cache.set("myorg", "myrepo", "sha256:abc123", "Test description")

        # Retrieve it
        result = ai_cache.get("myorg", "myrepo", "sha256:abc123")

        assert result == "Test description"

    def test_different_digests_cached_separately(self):
        """Test that different digests are cached separately."""
        from data.cache import InMemoryDataModelCache

        memory_cache = InMemoryDataModelCache({})
        ai_cache = AIDescriptionCache(memory_cache)

        # Store descriptions for different digests
        ai_cache.set("myorg", "myrepo", "sha256:abc", "Description A")
        ai_cache.set("myorg", "myrepo", "sha256:def", "Description B")

        # Retrieve them
        result_a = ai_cache.get("myorg", "myrepo", "sha256:abc")
        result_b = ai_cache.get("myorg", "myrepo", "sha256:def")

        assert result_a == "Description A"
        assert result_b == "Description B"

    def test_invalidate_removes_only_target(self):
        """Test that invalidate only removes the targeted description."""
        from data.cache import InMemoryDataModelCache

        memory_cache = InMemoryDataModelCache({})
        ai_cache = AIDescriptionCache(memory_cache)

        # Store descriptions
        ai_cache.set("myorg", "myrepo", "sha256:abc", "Description A")
        ai_cache.set("myorg", "myrepo", "sha256:def", "Description B")

        # Invalidate one
        ai_cache.invalidate("myorg", "myrepo", "sha256:abc")

        # Check results
        result_a = ai_cache.get("myorg", "myrepo", "sha256:abc")
        result_b = ai_cache.get("myorg", "myrepo", "sha256:def")

        assert result_a is None
        assert result_b == "Description B"


class TestCacheMetadata:
    """Tests for cache metadata (generated_at timestamp)."""

    def test_cached_data_includes_generated_at(self):
        """Test that cached data includes generation timestamp."""
        mock_cache = MagicMock()
        stored_data = None

        def capture_loader(key, loader, **kwargs):
            nonlocal stored_data
            stored_data = loader()
            return stored_data

        mock_cache.retrieve.side_effect = capture_loader

        ai_cache = AIDescriptionCache(mock_cache)
        ai_cache.set("myorg", "myrepo", "sha256:abc123", "Test description")

        assert stored_data is not None
        assert "description" in stored_data
        assert "generated_at" in stored_data
        assert stored_data["description"] == "Test description"

    def test_generated_at_is_valid_timestamp(self):
        """Test that generated_at is a valid ISO timestamp."""
        mock_cache = MagicMock()
        stored_data = None

        def capture_loader(key, loader, **kwargs):
            nonlocal stored_data
            stored_data = loader()
            return stored_data

        mock_cache.retrieve.side_effect = capture_loader

        ai_cache = AIDescriptionCache(mock_cache)
        ai_cache.set("myorg", "myrepo", "sha256:abc123", "Test description")

        # Parse the timestamp - should not raise
        from dateutil.parser import parse as parse_date

        generated_at = parse_date(stored_data["generated_at"])
        assert isinstance(generated_at, datetime)


class TestCacheErrorHandling:
    """Tests for cache error handling."""

    def test_get_handles_cache_errors_gracefully(self):
        """Test that get handles cache errors gracefully."""
        mock_cache = MagicMock()
        mock_cache.retrieve.side_effect = Exception("Cache error")

        ai_cache = AIDescriptionCache(mock_cache)
        result = ai_cache.get("myorg", "myrepo", "sha256:abc123")

        # Should return None instead of raising
        assert result is None

    def test_set_handles_cache_errors_gracefully(self):
        """Test that set handles cache errors gracefully."""
        mock_cache = MagicMock()
        mock_cache.retrieve.side_effect = Exception("Cache error")

        ai_cache = AIDescriptionCache(mock_cache)

        # Should not raise
        ai_cache.set("myorg", "myrepo", "sha256:abc123", "Test description")

    def test_invalidate_handles_cache_errors_gracefully(self):
        """Test that invalidate handles cache errors gracefully."""
        mock_cache = MagicMock()
        mock_cache.invalidate.side_effect = Exception("Cache error")

        ai_cache = AIDescriptionCache(mock_cache)

        # Should not raise
        ai_cache.invalidate("myorg", "myrepo", "sha256:abc123")
