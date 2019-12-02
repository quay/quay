from datetime import date, timedelta

import pytest

from data.database import RepositoryActionCount, RepositorySearchScore
from data.model.repository import create_repository
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
