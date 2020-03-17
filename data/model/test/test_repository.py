from datetime import timedelta

import pytest

from data.database import Repository
from data.model.gc import purge_repository
from data.model.repository import create_repository
from data.model.repository import get_filtered_matching_repositories, get_estimated_repository_count
from test.fixtures import *


def test_duplicate_repository_different_kinds(initialized_db):
    # Create an image repo.
    assert create_repository("devtable", "somenewrepo", None, repo_kind="image")

    # Try to create an app repo with the same name, which should fail.
    assert not create_repository("devtable", "somenewrepo", None, repo_kind="application")


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0,
    reason="MySQL requires specialized indexing of newly created repos",
)
@pytest.mark.parametrize("query", [(""), ("e"),])
@pytest.mark.parametrize("authed_username", [(None), ("devtable"),])
def test_search_pagination(query, authed_username, initialized_db):
    # Create some public repos.
    repo1 = create_repository(
        "devtable", "somenewrepo", None, repo_kind="image", visibility="public"
    )
    repo2 = create_repository(
        "devtable", "somenewrepo2", None, repo_kind="image", visibility="public"
    )
    repo3 = create_repository(
        "devtable", "somenewrepo3", None, repo_kind="image", visibility="public"
    )

    repositories = get_filtered_matching_repositories(query, filter_username=authed_username)
    assert len(repositories) > 3

    next_repos = get_filtered_matching_repositories(
        query, filter_username=authed_username, offset=1
    )
    assert repositories[0].id != next_repos[0].id
    assert repositories[1].id == next_repos[0].id


def test_get_estimated_repository_count(initialized_db):
    assert get_estimated_repository_count() >= Repository.select().count()
