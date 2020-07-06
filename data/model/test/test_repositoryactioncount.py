from datetime import date, timedelta

import pytest

from data.database import RepositoryActionCount, RepositorySearchScore
from data.model.repository import create_repository, Repository
from data.model.repositoryactioncount import update_repository_score, SEARCH_BUCKETS
from test.fixtures import *


@pytest.mark.parametrize(
    "bucket_sums,expected_score",
    [
        ((0, 0, 0, 0), 0),
        ((1, 6, 24, 152), 100),
        ((2, 6, 24, 152), 101),
        ((1, 6, 24, 304), 171),
        ((100, 480, 24, 152), 703),
        ((1, 6, 24, 15200), 7131),
        ((300, 500, 1000, 0), 1733),
        ((5000, 0, 0, 0), 5434),
    ],
)
def test_update_repository_score(bucket_sums, expected_score, initialized_db):
    # Create a new repository.
    repo = create_repository("devtable", "somenewrepo", None, repo_kind="image")

    # Delete the RAC created in create_repository.
    RepositoryActionCount.delete().where(RepositoryActionCount.repository == repo).execute()

    # Add RAC rows for each of the buckets.
    for index, bucket in enumerate(SEARCH_BUCKETS):
        for day in range(0, bucket.days):
            RepositoryActionCount.create(
                repository=repo,
                count=(bucket_sums[index] / bucket.days * 1.0),
                date=date.today() - bucket.delta + timedelta(days=day),
            )

    assert update_repository_score(repo)
    assert RepositorySearchScore.get(repository=repo).score == expected_score


def test_missing_counts_query(initialized_db):
    # Clear all existing entries.
    RepositoryActionCount.delete().execute()

    # Ensure we find all repositories.
    yesterday = datetime.utcnow() - timedelta(days=1)
    found = list(model.repositoryactioncount.missing_counts_query(yesterday))
    for repository in Repository.select():
        assert repository in found

    # Add an entry for each repository.
    for repository in Repository.select():
        model.repositoryactioncount.store_repository_action_count(repository, yesterday, 1234)

    # Ensure we no longer find the entries.
    found = list(model.repositoryactioncount.missing_counts_query(yesterday))
    assert not found

    # Check another day.
    two_days = datetime.utcnow() - timedelta(days=2)
    found = list(model.repositoryactioncount.missing_counts_query(two_days))
    assert found

    # Add a single entry.
    updated_repo = None
    for repository in Repository.select().limit(1):
        updated_repo = repository
        model.repositoryactioncount.store_repository_action_count(repository, two_days, 1234)

    # Verify we find all repositories but the one updated.
    updated_found = list(model.repositoryactioncount.missing_counts_query(two_days))
    assert updated_found

    assert set(found) - set(updated_found) == {updated_repo}
