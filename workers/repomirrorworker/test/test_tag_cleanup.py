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


class TestPerformMirrorCleanupErrorPath:
    @patch("workers.repomirrorworker.release_mirror")
    @patch("workers.repomirrorworker.emit_log")
    @patch("workers.repomirrorworker.delete_obsolete_tags")
    @patch("workers.repomirrorworker.tags_to_mirror")
    @patch("workers.repomirrorworker.claim_mirror")
    def test_cleanup_error_releases_with_fail(
        self, mock_claim, mock_tags, mock_delete, mock_emit, mock_release
    ):
        from data.database import RepoMirrorStatus

        mirror = MagicMock()
        mirror.root_rule.rule_value = ["latest"]
        mirror.external_reference = "registry.example.com/repo"
        mock_claim.return_value = mirror
        mock_tags.return_value = ([], [])
        mock_delete.side_effect = Exception("db error")

        from workers.repomirrorworker import perform_mirror

        skopeo = MagicMock()
        perform_mirror(skopeo, mirror)

        mock_release.assert_called_with(mirror, RepoMirrorStatus.FAIL)

    @patch("workers.repomirrorworker.release_mirror")
    @patch("workers.repomirrorworker.emit_log")
    @patch("workers.repomirrorworker.delete_obsolete_tags")
    @patch("workers.repomirrorworker.tags_to_mirror")
    @patch("workers.repomirrorworker.claim_mirror")
    def test_cleanup_success_releases_with_success(
        self, mock_claim, mock_tags, mock_delete, mock_emit, mock_release
    ):
        from data.database import RepoMirrorStatus

        mirror = MagicMock()
        mirror.root_rule.rule_value = ["latest"]
        mirror.external_reference = "registry.example.com/repo"
        mock_claim.return_value = mirror
        mock_tags.return_value = ([], [])
        mock_delete.return_value = []

        from workers.repomirrorworker import perform_mirror

        skopeo = MagicMock()
        perform_mirror(skopeo, mirror)

        mock_release.assert_called_with(mirror, RepoMirrorStatus.SUCCESS)


class TestOrgMirrorCleanupErrorPath:
    @patch("workers.repomirrorworker.org_mirror_repo_sync_duration_seconds")
    @patch("workers.repomirrorworker.org_mirror_repo_sync_total")
    @patch("workers.repomirrorworker.release_org_mirror_repo")
    @patch("workers.repomirrorworker.emit_org_mirror_log")
    @patch("workers.repomirrorworker._delete_obsolete_tags_for_repo")
    @patch("workers.repomirrorworker._get_all_tags_for_org_mirror")
    @patch("workers.repomirrorworker.retrieve_robot_token")
    @patch("workers.repomirrorworker.claim_org_mirror_repo")
    def test_empty_tags_cleanup_error_releases_fail(
        self,
        mock_claim,
        mock_token,
        mock_get_tags,
        mock_delete,
        mock_emit,
        mock_release,
        mock_total,
        mock_duration,
    ):
        from data.database import OrgMirrorRepoStatus

        org_mirror_repo = MagicMock()
        org_mirror_repo.org_mirror_config.external_registry_url = "https://registry.example.com"
        org_mirror_repo.org_mirror_config.external_namespace = "ns"
        org_mirror_repo.org_mirror_config.skopeo_timeout = 300
        org_mirror_repo.repository_name = "test-repo"
        org_mirror_repo.repository = MagicMock(id=1)

        mock_claim.return_value = org_mirror_repo
        mock_token.return_value = "token"
        mock_get_tags.return_value = []
        mock_delete.side_effect = Exception("db error")

        from workers.repomirrorworker import perform_org_mirror_repo

        skopeo = MagicMock()
        result = perform_org_mirror_repo(skopeo, org_mirror_repo)

        assert result == OrgMirrorRepoStatus.FAIL
        mock_release.assert_called_once()
        assert mock_release.call_args[0][1] == OrgMirrorRepoStatus.FAIL
