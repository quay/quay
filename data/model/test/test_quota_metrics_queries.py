from data.database import QuotaNamespaceSize, QuotaRepositorySize
from data.model.namespacequota import create_namespace_quota
from data.model.organization import create_organization
from data.model.quota import get_all_namespace_quota_data, get_all_repository_sizes
from data.model.repository import create_repository
from data.model.user import get_user
from test.fixtures import *


def test_get_all_namespace_quota_data_includes_size_and_quota_only(initialized_db):
    user = get_user("devtable")
    size_only = create_organization("sizeonly", "sizeonly@example.com", user)
    quota_only = create_organization("quotaonly", "quotaonly@example.com", user)
    both = create_organization("bothns", "bothns@example.com", user)

    # pylint: disable-next=no-value-for-parameter
    QuotaNamespaceSize.insert(
        namespace_user_id=size_only.id,
        size_bytes=111,
        backfill_complete=True,
        backfill_start_ms=0,
    ).execute()
    # pylint: disable-next=no-value-for-parameter
    QuotaNamespaceSize.insert(
        namespace_user_id=both.id,
        size_bytes=222,
        backfill_complete=True,
        backfill_start_ms=0,
    ).execute()
    create_namespace_quota(quota_only, 50000)
    create_namespace_quota(both, 60000)

    by_name = {
        row["username"]: row
        for row in get_all_namespace_quota_data()
        if row["username"] in {"sizeonly", "quotaonly", "bothns"}
    }

    assert set(by_name) == {"sizeonly", "quotaonly", "bothns"}
    assert by_name["sizeonly"]["size_bytes"] == 111
    assert by_name["sizeonly"]["limit_bytes"] is None
    assert by_name["quotaonly"]["size_bytes"] is None
    assert by_name["quotaonly"]["limit_bytes"] == 50000
    assert by_name["bothns"]["size_bytes"] == 222
    assert by_name["bothns"]["limit_bytes"] == 60000


def test_get_all_namespace_quota_data_respects_max_rows(initialized_db):
    user = get_user("devtable")
    orgs = []
    for i in range(5):
        org = create_organization(f"maxns{i}", f"maxns{i}@example.com", user)
        orgs.append(org)
        # pylint: disable-next=no-value-for-parameter
        QuotaNamespaceSize.insert(
            namespace_user_id=org.id,
            size_bytes=100 * i,
            backfill_complete=True,
            backfill_start_ms=0,
        ).execute()

    rows = list(get_all_namespace_quota_data(batch_size=2, max_rows=3))
    assert len(rows) == 3
    assert [row["id"] for row in rows] == sorted(row["id"] for row in rows)


def test_get_all_repository_sizes_bounded(initialized_db):
    user = get_user("devtable")
    org = create_organization("reposizeorg", "reposizeorg@example.com", user)
    created_ids = []
    for i in range(4):
        repo = create_repository("reposizeorg", f"repo{i}", user)
        created_ids.append(repo.id)
        # pylint: disable-next=no-value-for-parameter
        QuotaRepositorySize.insert(
            repository_id=repo.id,
            size_bytes=1000 * (i + 1),
            backfill_complete=True,
            backfill_start_ms=0,
        ).execute()

    all_for_org = [row for row in get_all_repository_sizes() if row["namespace"] == "reposizeorg"]
    assert len(all_for_org) == 4
    assert {row["id"] for row in all_for_org} == set(created_ids)

    bounded = list(get_all_repository_sizes(batch_size=2, max_rows=2))
    assert len(bounded) == 2
    assert bounded[0]["id"] < bounded[1]["id"]


def test_get_all_namespace_quota_data_stops_on_empty_join(initialized_db):
    """Orphan candidate IDs should not hang the generator."""
    from unittest.mock import patch

    with patch(
        "data.model.quota._next_namespace_quota_candidate_ids",
        return_value=[99999999],
    ):
        assert list(get_all_namespace_quota_data(max_rows=10)) == []


def test_get_all_namespace_quota_data_excludes_incomplete_backfill(initialized_db):
    """Namespaces with backfill_complete=False should have size_bytes=None."""
    user = get_user("devtable")
    incomplete = create_organization("incomplete_ns", "incomplete_ns@example.com", user)
    complete = create_organization("complete_ns", "complete_ns@example.com", user)

    # Incomplete backfill: size_bytes=0, backfill_complete=False
    # pylint: disable-next=no-value-for-parameter
    QuotaNamespaceSize.insert(
        namespace_user_id=incomplete.id,
        size_bytes=0,
        backfill_complete=False,
        backfill_start_ms=None,
    ).execute()
    create_namespace_quota(incomplete, 50000)

    # Complete backfill
    # pylint: disable-next=no-value-for-parameter
    QuotaNamespaceSize.insert(
        namespace_user_id=complete.id,
        size_bytes=7777,
        backfill_complete=True,
        backfill_start_ms=0,
    ).execute()
    create_namespace_quota(complete, 60000)

    by_name = {
        row["username"]: row
        for row in get_all_namespace_quota_data()
        if row["username"] in {"incomplete_ns", "complete_ns"}
    }

    assert set(by_name) == {"incomplete_ns", "complete_ns"}
    # Incomplete backfill: size_bytes should be None (treated as absent)
    assert by_name["incomplete_ns"]["size_bytes"] is None
    assert by_name["incomplete_ns"]["limit_bytes"] == 50000
    # Complete backfill: size_bytes should be present
    assert by_name["complete_ns"]["size_bytes"] == 7777
    assert by_name["complete_ns"]["limit_bytes"] == 60000


def test_get_all_repository_sizes_excludes_incomplete_backfill(initialized_db):
    """Repos with backfill_complete=False should be excluded entirely."""
    user = get_user("devtable")
    org = create_organization("bf_repo_org", "bf_repo_org@example.com", user)

    repo_complete = create_repository("bf_repo_org", "repo_done", user)
    repo_incomplete = create_repository("bf_repo_org", "repo_pending", user)

    # pylint: disable-next=no-value-for-parameter
    QuotaRepositorySize.insert(
        repository_id=repo_complete.id,
        size_bytes=5000,
        backfill_complete=True,
        backfill_start_ms=0,
    ).execute()
    # pylint: disable-next=no-value-for-parameter
    QuotaRepositorySize.insert(
        repository_id=repo_incomplete.id,
        size_bytes=0,
        backfill_complete=False,
        backfill_start_ms=None,
    ).execute()

    results = [row for row in get_all_repository_sizes() if row["namespace"] == "bf_repo_org"]
    assert len(results) == 1
    assert results[0]["name"] == "repo_done"
    assert results[0]["size_bytes"] == 5000
