import os
from datetime import timedelta

import pytest

from data.database import BlobUpload, QuotaRepositorySize, Repository
from data.model.repository import (
    create_repository,
    get_estimated_repository_count,
    get_filtered_matching_repositories,
    get_repository,
    get_repository_sizes,
    get_size_during_upload,
)
from data.model.storage import get_image_location_for_name
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
@pytest.mark.parametrize(
    "query",
    [
        (""),
        ("e"),
    ],
)
@pytest.mark.parametrize(
    "authed_username",
    [
        (None),
        ("devtable"),
    ],
)
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


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0,
    reason="MySQL requires specialized indexing of newly created repos",
)
@pytest.mark.parametrize(
    "query,repo_count",
    [
        ("somenewrepo", 3),
        ("devtable/somenewrepo", 2),
        ("devtable/", 2),
        ("devtable/somenewrepo2", 1),
        ("doesnotexist/somenewrepo", 0),
        ("does/notexist/somenewrepo", 0),
        ("/somenewrepo", 3),
        ("repo/withslash", 0),
        ("/repo/withslash", 1),
    ],
)
def test_search_filtering_complex(query, repo_count, initialized_db):
    # Create some public repos
    repo1 = create_repository(
        "devtable", "somenewrepo", None, repo_kind="image", visibility="public"
    )
    repo2 = create_repository(
        "devtable", "somenewrepo2", None, repo_kind="image", visibility="public"
    )
    repo3 = create_repository(
        "freshuser", "somenewrepo", None, repo_kind="image", visibility="public"
    )
    repo4 = create_repository(
        "freshuser", "repo/withslash", None, repo_kind="image", visibility="public"
    )

    repositories = get_filtered_matching_repositories(query, filter_username=None)
    assert len(repositories) == repo_count


def test_get_estimated_repository_count(initialized_db):
    assert get_estimated_repository_count() >= Repository.select().count()


def test_get_size_during_upload(initialized_db):
    upload_size = 100
    repo1 = create_repository(
        "devtable", "somenewrepo", None, repo_kind="image", visibility="public"
    )
    location = get_image_location_for_name("local_us")
    BlobUpload.create(
        repository=repo1.id,
        uuid="123",
        storage_metadata="{}",
        byte_count=upload_size,
        location=location.id,
    )
    size = get_size_during_upload(repo1.id)
    assert size == upload_size


def test_get_repository_sizes(initialized_db):
    # empty state
    assert get_repository_sizes([]) == {}
    assert get_repository_sizes(None) == {}

    # repos with size entries
    repo1 = get_repository("buynlarge", "orgrepo")
    repo2 = get_repository("devtable", "simple")
    assert get_repository_sizes([repo1.id, repo2.id]) == {repo1.id: 92, repo2.id: 92}

    # some repos without size entries
    repo3 = get_repository("devtable", "building")
    assert (
        QuotaRepositorySize.select().where(QuotaRepositorySize.repository == repo3.id).count() == 0
    )
    assert get_repository_sizes([repo1.id, repo2.id, repo3.id]) == {
        repo1.id: 92,
        repo2.id: 92,
        repo3.id: 0,
    }
