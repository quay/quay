"""Mirror Sync Lifecycle E2E Tests (Tier 1 — Mocked Skopeo)."""

import json
from unittest.mock import patch

import mock
import pytest

from data.database import RepoMirrorConfig, RepoMirrorStatus, Tag
from data.model.test.test_repo_mirroring import create_mirror_repo_robot
from test.fixtures import *
from util.repomirror.skopeomirror import SkopeoResults
from workers.repomirrorworker.test.conftest import (
    SKOPEO_BIN,
    alive_tag_names,
    create_tag,
    disable_existing_mirrors,
    make_skopeo_side_effect,
    run_mirror_sync,
)

UPSTREAM_REPO = "docker://registry.example.com/namespace/repository"


def _list_tags_call(tags, success=True, stderr=""):
    """Build a skopeo list-tags call entry."""
    return {
        "args": [
            SKOPEO_BIN,
            "list-tags",
            "--tls-verify=False",
            UPSTREAM_REPO,
        ],
        "results": SkopeoResults(
            success, [], json.dumps({"Tags": tags}) if success else "", stderr
        ),
    }


def _copy_tag_call(tag, repo_name, success=True, stderr=""):
    """Build a skopeo copy call entry for a single tag."""
    return {
        "args": [
            SKOPEO_BIN,
            "copy",
            "--all",
            "--remove-signatures",
            "--src-tls-verify=False",
            "--dest-tls-verify=True",
            f"{UPSTREAM_REPO}:{tag}",
            f"docker://localhost:5000/mirror/{repo_name}:{tag}",
        ],
        "results": SkopeoResults(success, [], f"copied {tag}" if success else "", stderr),
    }


# ===========================================================================
# Full Mirror Sync Lifecycle E2E
# ===========================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_full_sync_lifecycle(run_skopeo_mock, initialized_db, app):
    """
    Full mirror sync lifecycle: create config → trigger sync → verify tags
    appear in Quay → verify mirror status updated to SUCCESS.

    This test validates the complete happy-path through perform_mirror():
      1. Mirror config is claimed
      2. Skopeo list-tags fetches remote tags
      3. Tags matching the rule are copied via skopeo
      4. Tags appear in the local repository
      5. Mirror status transitions to SUCCESS
      6. Retry counter is preserved (not decremented)
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest", "v1.*"],
        repo_name="lifecycle",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["latest", "v1.0", "v1.1"]),
        _copy_tag_call("latest", "lifecycle"),
        _copy_tag_call("v1.0", "lifecycle"),
        _copy_tag_call("v1.1", "lifecycle"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["latest", "v1.0", "v1.1"]

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS
    assert mirror.sync_retries_remaining == 3


# ===========================================================================
# Mirror Sync Retry Logic
# ===========================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_retry_then_recover(run_skopeo_mock, initialized_db, app):
    """
    Mirror sync retry logic: inject failure → verify retry count decrements →
    inject success on later attempt → verify mirror recovers to SUCCESS.

    Validates the retry/recovery path that is missing from existing coverage
    (existing test_inspect_error_mirror only tests exhaustion, not recovery).
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"],
        repo_name="retry_recover",
        external_registry_config={"verify_tls": False},
    )
    assert mirror.sync_retries_remaining == 3

    # --- Attempt 1: list-tags fails → retries decrement to 2 ---
    run_skopeo_mock.side_effect = make_skopeo_side_effect(
        [_list_tags_call([], success=False, stderr="connection refused")]
    )
    from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker

    worker = RepoMirrorWorker()
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_retries_remaining == 2
    assert mirror.sync_status == RepoMirrorStatus.FAIL

    # --- Attempt 2: list-tags fails again → retries decrement to 1 ---
    run_skopeo_mock.side_effect = make_skopeo_side_effect(
        [_list_tags_call([], success=False, stderr="connection refused")]
    )
    worker._process_mirrors()
    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_retries_remaining == 1
    assert mirror.sync_status == RepoMirrorStatus.FAIL

    # --- Attempt 3: succeeds → retries reset, status SUCCESS ---
    skopeo_calls = [
        _list_tags_call(["latest"]),
        _copy_tag_call("latest", "retry_recover"),
    ]
    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS
    assert mirror.sync_retries_remaining == 3
    assert alive_tag_names(repo) == ["latest"]


# ===========================================================================
# Tag Glob Filtering During Sync
# ===========================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_glob_wildcard_v_pattern(run_skopeo_mock, initialized_db, app):
    """Pattern 'v*' matches v1.0, v2.0 but not latest, nightly, dev-123."""
    mirror, repo = create_mirror_repo_robot(
        ["v*"],
        repo_name="glob_v_star",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["v1.0", "v2.0", "latest", "nightly", "dev-123"]),
        _copy_tag_call("v1.0", "glob_v_star"),
        _copy_tag_call("v2.0", "glob_v_star"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["v1.0", "v2.0"]

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_glob_multi_pattern_v_star_and_latest(run_skopeo_mock, initialized_db, app):
    """Patterns ['v*', 'latest'] match v1.0, v2.0, latest but not nightly, dev-123."""
    mirror, repo = create_mirror_repo_robot(
        ["v*", "latest"],
        repo_name="glob_multi",
        external_registry_config={"verify_tls": False},
    )

    # tags_to_mirror sorts alphabetically: latest, v1.0, v2.0
    skopeo_calls = [
        _list_tags_call(["v1.0", "v2.0", "latest", "nightly", "dev-123"]),
        _copy_tag_call("latest", "glob_multi"),
        _copy_tag_call("v1.0", "glob_multi"),
        _copy_tag_call("v2.0", "glob_multi"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["latest", "v1.0", "v2.0"]


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_glob_match_all_wildcard(run_skopeo_mock, initialized_db, app):
    """Pattern '*' matches every remote tag."""
    mirror, repo = create_mirror_repo_robot(
        ["*"],
        repo_name="glob_all",
        external_registry_config={"verify_tls": False},
    )

    all_remote_tags = ["alpha", "beta", "gamma"]
    skopeo_calls = [_list_tags_call(all_remote_tags)]
    for tag in sorted(all_remote_tags):
        skopeo_calls.append(_copy_tag_call(tag, "glob_all"))

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["alpha", "beta", "gamma"]


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_glob_no_matching_tags(run_skopeo_mock, initialized_db, app):
    """Pattern 'nonexistent-*' matches nothing → sync succeeds with no copies."""
    mirror, repo = create_mirror_repo_robot(
        ["nonexistent-*"],
        repo_name="glob_none",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [_list_tags_call(["latest", "v1.0", "v2.0"])]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_glob_bracket_pattern(run_skopeo_mock, initialized_db, app):
    """Pattern 'v[12].*' matches v1.0, v2.0 but not v3.0."""
    mirror, repo = create_mirror_repo_robot(
        ["v[12].*"],
        repo_name="glob_bracket",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["v1.0", "v2.0", "v3.0", "latest"]),
        _copy_tag_call("v1.0", "glob_bracket"),
        _copy_tag_call("v2.0", "glob_bracket"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["v1.0", "v2.0"]


# ===========================================================================
# Obsolete Tag Cleanup
# ===========================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_obsolete_tag_cleanup(run_skopeo_mock, initialized_db, app):
    """
    Obsolete tag cleanup: a tag exists locally but is no longer on the
    upstream remote → after sync the local tag is deleted.

    Validates delete_obsolete_tags() through the full perform_mirror() flow
    (existing test_remove_obsolete_tags only tests the function in isolation).
    """
    mirror, repo = create_mirror_repo_robot(
        ["*"],
        repo_name="obsolete",
        external_registry_config={"verify_tls": False},
    )

    create_tag(repo, "v1.0")
    create_tag(repo, "v2.0")
    create_tag(repo, "old-release")
    assert alive_tag_names(repo) == ["old-release", "v1.0", "v2.0"]

    skopeo_calls = [
        _list_tags_call(["v1.0", "v2.0"]),
        _copy_tag_call("v1.0", "obsolete"),
        _copy_tag_call("v2.0", "obsolete"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["v1.0", "v2.0"]

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_obsolete_cleanup_removes_multiple_tags(run_skopeo_mock, initialized_db, app):
    """When multiple local tags are absent from upstream, all are deleted."""
    mirror, repo = create_mirror_repo_robot(
        ["*"],
        repo_name="multi_obsolete",
        external_registry_config={"verify_tls": False},
    )

    create_tag(repo, "keep")
    create_tag(repo, "stale-a")
    create_tag(repo, "stale-b")
    create_tag(repo, "stale-c")
    assert len(alive_tag_names(repo)) == 4

    skopeo_calls = [
        _list_tags_call(["keep"]),
        _copy_tag_call("keep", "multi_obsolete"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls, repo=repo, create_tags_on_copy=True)

    assert alive_tag_names(repo) == ["keep"]


# ===========================================================================
# Mirror + Immutability Interaction
# ===========================================================================


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_immutable_tag_survives_obsolete_cleanup(run_skopeo_mock, initialized_db, app):
    """
    An immutable tag cannot be deleted by the mirror's obsolete-tag cleanup.

    When an immutable tag exists locally but is absent from the upstream tag
    list, delete_obsolete_tags() calls delete_tag() which raises
    ImmutableTagException. The outer except in perform_mirror() catches this,
    setting the mirror to FAIL — but the immutable tag remains alive.
    """
    mirror, repo = create_mirror_repo_robot(
        ["*"],
        repo_name="immutable_cleanup",
        external_registry_config={"verify_tls": False},
    )

    create_tag(repo, "v1.0")
    protected_tag = create_tag(repo, "protected")
    Tag.update(immutable=True).where(Tag.id == protected_tag._db_id).execute()

    assert alive_tag_names(repo) == ["protected", "v1.0"]

    skopeo_calls = [
        _list_tags_call(["v1.0"]),
        _copy_tag_call("v1.0", "immutable_cleanup"),
    ]

    run_skopeo_mock.side_effect = make_skopeo_side_effect(skopeo_calls)

    with patch("features.IMMUTABLE_TAGS", True):
        from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker

        worker = RepoMirrorWorker()
        worker._process_mirrors()

    assert skopeo_calls == []

    names = alive_tag_names(repo)
    assert "protected" in names
    assert "v1.0" in names

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.FAIL


@disable_existing_mirrors
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_immutable_tag_not_affected_when_present_upstream(run_skopeo_mock, initialized_db, app):
    """
    When an immutable tag is also present upstream, sync proceeds normally
    and the tag is simply re-copied (overwrite is handled by the v2 endpoint,
    not by the mirror worker directly).
    """
    mirror, repo = create_mirror_repo_robot(
        ["*"],
        repo_name="immutable_present",
        external_registry_config={"verify_tls": False},
    )

    tag = create_tag(repo, "stable")
    Tag.update(immutable=True).where(Tag.id == tag._db_id).execute()

    skopeo_calls = [
        _list_tags_call(["stable"]),
        _copy_tag_call("stable", "immutable_present"),
    ]

    run_skopeo_mock.side_effect = make_skopeo_side_effect(skopeo_calls)

    with patch("features.IMMUTABLE_TAGS", True):
        from workers.repomirrorworker.repomirrorworker import RepoMirrorWorker

        worker = RepoMirrorWorker()
        worker._process_mirrors()

    assert skopeo_calls == []
    assert "stable" in alive_tag_names(repo)

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.SUCCESS


# ===========================================================================
# Mirror Sync Success Notification Delivery
# ===========================================================================


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.spawn_notification")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_success_notification_delivery(
    run_skopeo_mock, mock_spawn_notification, initialized_db, app
):
    """
    On successful sync, spawn_notification is called with both
    'repo_mirror_sync_started' and 'repo_mirror_sync_success' events.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"],
        repo_name="notify_success",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["latest"]),
        _copy_tag_call("latest", "notify_success"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    event_kinds = [c[0][1] for c in mock_spawn_notification.call_args_list]

    assert "repo_mirror_sync_started" in event_kinds
    assert "repo_mirror_sync_success" in event_kinds
    assert "repo_mirror_sync_failed" not in event_kinds

    for call_args in mock_spawn_notification.call_args_list:
        if call_args[0][1] == "repo_mirror_sync_success":
            payload = call_args[0][2]
            assert "message" in payload
            assert mirror.external_reference in payload["message"]


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.spawn_notification")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_success_notification_on_empty_match(
    run_skopeo_mock, mock_spawn_notification, initialized_db, app
):
    """
    When no tags match the pattern, mirror still succeeds and emits
    repo_mirror_sync_success notification.
    """
    mirror, repo = create_mirror_repo_robot(
        ["nonexistent-*"],
        repo_name="notify_empty",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [_list_tags_call(["latest", "v1.0"])]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    event_kinds = [c[0][1] for c in mock_spawn_notification.call_args_list]
    assert "repo_mirror_sync_success" in event_kinds


# ===========================================================================
# Mirror Sync Failure Notification Delivery
# ===========================================================================


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.spawn_notification")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_failure_notification_on_list_tags_error(
    run_skopeo_mock, mock_spawn_notification, initialized_db, app
):
    """
    When skopeo list-tags fails, spawn_notification is called with
    'repo_mirror_sync_started' and then 'repo_mirror_sync_failed'.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"],
        repo_name="notify_fail_list",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call([], success=False, stderr="unauthorized: authentication required"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    event_kinds = [c[0][1] for c in mock_spawn_notification.call_args_list]

    assert "repo_mirror_sync_started" in event_kinds
    assert "repo_mirror_sync_failed" in event_kinds
    assert "repo_mirror_sync_success" not in event_kinds

    for call_args in mock_spawn_notification.call_args_list:
        if call_args[0][1] == "repo_mirror_sync_failed":
            payload = call_args[0][2]
            assert "message" in payload


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.spawn_notification")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_failure_notification_on_copy_error(
    run_skopeo_mock, mock_spawn_notification, initialized_db, app
):
    """
    When skopeo list-tags succeeds but copy fails for a tag, a
    'repo_mirror_sync_failed' notification is delivered.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"],
        repo_name="notify_fail_copy",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["latest"]),
        _copy_tag_call("latest", "notify_fail_copy", success=False, stderr="manifest unknown"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    event_kinds = [c[0][1] for c in mock_spawn_notification.call_args_list]

    assert "repo_mirror_sync_started" in event_kinds
    assert "repo_mirror_sync_failed" in event_kinds
    assert "repo_mirror_sync_success" not in event_kinds

    mirror = RepoMirrorConfig.get_by_id(mirror.id)
    assert mirror.sync_status == RepoMirrorStatus.FAIL


@disable_existing_mirrors
@mock.patch("workers.repomirrorworker.spawn_notification")
@mock.patch("util.repomirror.skopeomirror.SkopeoMirror.run_skopeo")
def test_notification_ordering_started_before_result(
    run_skopeo_mock, mock_spawn_notification, initialized_db, app
):
    """
    The 'started' notification always fires before the 'success' or 'failed'
    notification, regardless of outcome.
    """
    mirror, repo = create_mirror_repo_robot(
        ["latest"],
        repo_name="notify_order",
        external_registry_config={"verify_tls": False},
    )

    skopeo_calls = [
        _list_tags_call(["latest"]),
        _copy_tag_call("latest", "notify_order"),
    ]

    run_mirror_sync(run_skopeo_mock, skopeo_calls)

    notification_events = [c[0][1] for c in mock_spawn_notification.call_args_list]
    started_idx = notification_events.index("repo_mirror_sync_started")
    success_idx = notification_events.index("repo_mirror_sync_success")
    assert started_idx < success_idx
