from unittest.mock import MagicMock, call

import pytest
import redis

from data.cache.repo_modification_tracker import KEY_PREFIX, RepoModificationTracker


@pytest.fixture
def mock_redis():
    client = MagicMock()
    client.time.return_value = (1000, 500000)  # 1000.5 seconds
    return client


@pytest.fixture
def tracker(mock_redis):
    return RepoModificationTracker(mock_redis)


class TestInit:
    def test_none_client(self):
        tracker = RepoModificationTracker(None)
        assert tracker.redis is None

    def test_with_client(self, mock_redis):
        tracker = RepoModificationTracker(mock_redis)
        assert tracker.redis is mock_redis


class TestGetRedisTime:
    def test_returns_float_timestamp(self, tracker, mock_redis):
        result = tracker._get_redis_time()
        assert result == 1000.5
        mock_redis.time.assert_called_once()

    def test_no_redis(self):
        tracker = RepoModificationTracker(None)
        assert tracker._get_redis_time() is None

    def test_redis_error_returns_none(self, tracker, mock_redis):
        mock_redis.time.side_effect = redis.RedisError("connection lost")
        assert tracker._get_redis_time() is None


class TestMarkRepoModified:
    def test_sets_key_with_ttl(self, tracker, mock_redis):
        result = tracker.mark_repo_modified("myns", "myrepo")

        assert result == 1000.5
        mock_redis.set.assert_called_once_with(
            f"{KEY_PREFIX}repo_modified:myns:myrepo", 1000.5, ex=300
        )

    def test_no_redis(self):
        tracker = RepoModificationTracker(None)
        assert tracker.mark_repo_modified("ns", "repo") is None

    def test_redis_error_returns_none(self, tracker, mock_redis):
        mock_redis.set.side_effect = redis.RedisError("write error")
        assert tracker.mark_repo_modified("ns", "repo") is None


class TestMarkPermissionRevoked:
    def test_sets_key_with_ttl(self, tracker, mock_redis):
        result = tracker.mark_permission_revoked(42, "myns", "myrepo")

        assert result == 1000.5
        mock_redis.set.assert_called_once_with(
            f"{KEY_PREFIX}permission_revoked:42:myns:myrepo", 1000.5, ex=300
        )

    def test_no_redis(self):
        tracker = RepoModificationTracker(None)
        assert tracker.mark_permission_revoked(1, "ns", "repo") is None

    def test_redis_error_returns_none(self, tracker, mock_redis):
        mock_redis.set.side_effect = redis.RedisError("write error")
        assert tracker.mark_permission_revoked(1, "ns", "repo") is None


class TestMarkPermissionsRevokedBatch:
    def test_uses_pipeline(self, tracker, mock_redis):
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        result = tracker.mark_permissions_revoked_batch([1, 2, 3], "ns", "repo")

        assert result == 1000.5
        mock_redis.pipeline.assert_called_once()
        assert mock_pipe.set.call_count == 3
        mock_pipe.set.assert_any_call(f"{KEY_PREFIX}permission_revoked:1:ns:repo", 1000.5, ex=300)
        mock_pipe.set.assert_any_call(f"{KEY_PREFIX}permission_revoked:2:ns:repo", 1000.5, ex=300)
        mock_pipe.set.assert_any_call(f"{KEY_PREFIX}permission_revoked:3:ns:repo", 1000.5, ex=300)
        mock_pipe.execute.assert_called_once()

    def test_empty_user_ids(self, tracker, mock_redis):
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        result = tracker.mark_permissions_revoked_batch([], "ns", "repo")

        assert result == 1000.5
        mock_pipe.set.assert_not_called()
        mock_pipe.execute.assert_called_once()

    def test_no_redis(self):
        tracker = RepoModificationTracker(None)
        assert tracker.mark_permissions_revoked_batch([1], "ns", "repo") is None

    def test_pipeline_error_returns_none(self, tracker, mock_redis):
        mock_redis.pipeline.side_effect = redis.RedisError("pipeline error")
        assert tracker.mark_permissions_revoked_batch([1], "ns", "repo") is None


class TestShouldBlockReadAccess:
    def test_no_redis_returns_false(self):
        tracker = RepoModificationTracker(None)
        assert tracker.should_block_read_access(1, "ns", "repo") is False

    def test_no_revocation_returns_false(self, tracker, mock_redis):
        mock_redis.get.return_value = None

        assert tracker.should_block_read_access(1, "ns", "repo") is False
        mock_redis.get.assert_called_once_with(f"{KEY_PREFIX}permission_revoked:1:ns:repo")

    def test_revocation_but_no_modification_returns_false(self, tracker, mock_redis):
        mock_redis.get.side_effect = [b"1000.0", None]

        assert tracker.should_block_read_access(1, "ns", "repo") is False

    def test_modification_before_revocation_returns_false(self, tracker, mock_redis):
        # revoked at 1000.0, modified at 999.0 (before revocation)
        mock_redis.get.side_effect = [b"1000.0", b"999.0"]

        assert tracker.should_block_read_access(1, "ns", "repo") is False

    def test_modification_after_revocation_returns_true(self, tracker, mock_redis):
        # revoked at 1000.0, modified at 1001.0 (after revocation)
        mock_redis.get.side_effect = [b"1000.0", b"1001.0"]

        assert tracker.should_block_read_access(1, "ns", "repo") is True

    def test_equal_timestamps_returns_false(self, tracker, mock_redis):
        # modified at exact same time as revocation — not strictly "after"
        mock_redis.get.side_effect = [b"1000.0", b"1000.0"]

        assert tracker.should_block_read_access(1, "ns", "repo") is False

    def test_redis_error_propagates(self, tracker, mock_redis):
        """Redis errors must propagate so callers can fall back to primary DB."""
        mock_redis.get.side_effect = redis.RedisError("connection lost")

        with pytest.raises(redis.RedisError):
            tracker.should_block_read_access(1, "ns", "repo")

    def test_reads_correct_keys(self, tracker, mock_redis):
        mock_redis.get.side_effect = [b"1000.0", b"999.0"]

        tracker.should_block_read_access(42, "myorg", "myrepo")

        mock_redis.get.assert_any_call(f"{KEY_PREFIX}permission_revoked:42:myorg:myrepo")
        mock_redis.get.assert_any_call(f"{KEY_PREFIX}repo_modified:myorg:myrepo")


class TestKeyPrefix:
    def test_keys_use_prefix(self, tracker, mock_redis):
        """All keys must use the quay:repo_content_tracker: prefix to avoid collisions."""
        tracker.mark_repo_modified("ns", "repo")
        key = mock_redis.set.call_args[0][0]
        assert key.startswith("quay:repo_content_tracker:")

    def test_different_repos_different_keys(self, tracker, mock_redis):
        tracker.mark_repo_modified("ns", "repo1")
        key1 = mock_redis.set.call_args[0][0]

        tracker.mark_repo_modified("ns", "repo2")
        key2 = mock_redis.set.call_args[0][0]

        assert key1 != key2
