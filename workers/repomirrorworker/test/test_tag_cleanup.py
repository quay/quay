"""
Pure unit tests for tag cleanup logic in the mirror worker.

These tests mock the database layer so they run in the unit test environment
(not integration), ensuring codecov patch coverage.
"""

from unittest.mock import MagicMock, patch

import pytest

from workers.repomirrorworker import (
    _delete_obsolete_tags_for_repo,
    delete_obsolete_tags,
)


def _make_tag(name):
    tag = MagicMock()
    tag.name = name
    return tag


class TestDeleteObsoleteTagsForRepo:
    @patch("workers.repomirrorworker.delete_tag")
    @patch("workers.repomirrorworker.lookup_alive_tags_shallow")
    @patch("workers.repomirrorworker.app")
    def test_deletes_tags_not_in_incoming(self, mock_app, mock_lookup, mock_delete):
        mock_app.config.get.return_value = True
        mock_lookup.return_value = ([_make_tag("keep"), _make_tag("stale")], None)
        repo = MagicMock(id=42)

        result = _delete_obsolete_tags_for_repo(repo, ["keep"])

        assert [t.name for t in result] == ["stale"]
        mock_delete.assert_called_once_with(repo, "stale")

    @patch("workers.repomirrorworker.delete_tag")
    @patch("workers.repomirrorworker.lookup_alive_tags_shallow")
    @patch("workers.repomirrorworker.app")
    def test_deletes_all_when_empty_incoming(self, mock_app, mock_lookup, mock_delete):
        mock_app.config.get.return_value = True
        mock_lookup.return_value = ([_make_tag("a"), _make_tag("b")], None)
        repo = MagicMock(id=42)

        result = _delete_obsolete_tags_for_repo(repo, [])

        assert sorted(t.name for t in result) == ["a", "b"]
        assert mock_delete.call_count == 2

    @patch("workers.repomirrorworker.delete_tag")
    @patch("workers.repomirrorworker.lookup_alive_tags_shallow")
    @patch("workers.repomirrorworker.app")
    def test_no_deletions_when_all_match(self, mock_app, mock_lookup, mock_delete):
        mock_app.config.get.return_value = True
        mock_lookup.return_value = ([_make_tag("a"), _make_tag("b")], None)
        repo = MagicMock(id=42)

        result = _delete_obsolete_tags_for_repo(repo, ["a", "b"])

        assert result == []
        mock_delete.assert_not_called()

    @patch("workers.repomirrorworker.delete_tag")
    @patch("workers.repomirrorworker.lookup_alive_tags_shallow")
    @patch("workers.repomirrorworker.app")
    def test_skips_when_config_disabled(self, mock_app, mock_lookup, mock_delete):
        mock_app.config.get.return_value = False
        repo = MagicMock(id=42)

        result = _delete_obsolete_tags_for_repo(repo, [])

        assert result == []
        mock_lookup.assert_not_called()
        mock_delete.assert_not_called()

    @patch("workers.repomirrorworker.delete_tag")
    @patch("workers.repomirrorworker.lookup_alive_tags_shallow")
    @patch("workers.repomirrorworker.app")
    def test_uses_set_for_membership(self, mock_app, mock_lookup, mock_delete):
        """Incoming tags are converted to a set for O(1) lookups."""
        mock_app.config.get.return_value = True
        tags = [_make_tag(f"tag{i}") for i in range(100)]
        mock_lookup.return_value = (tags, None)
        repo = MagicMock(id=42)

        result = _delete_obsolete_tags_for_repo(repo, [f"tag{i}" for i in range(100)])

        assert result == []


class TestDeleteObsoleteTags:
    @patch("workers.repomirrorworker._delete_obsolete_tags_for_repo")
    def test_delegates_to_helper(self, mock_helper):
        mock_helper.return_value = [_make_tag("old")]
        mirror = MagicMock()
        mirror.repository = MagicMock(id=99)

        result = delete_obsolete_tags(mirror, ["new"])

        mock_helper.assert_called_once_with(mirror.repository, ["new"])
        assert [t.name for t in result] == ["old"]
