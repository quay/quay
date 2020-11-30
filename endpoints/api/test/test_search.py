import pytest

from playhouse.test_utils import assert_query_count

from data import model, database
from endpoints.api.search import ConductRepositorySearch, ConductSearch, MAX_PER_PAGE
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize(
    "query",
    [
        (""),
        ("simple"),
        ("public"),
        ("repository"),
    ],
)
def test_repository_search(query, client):
    # Prime the caches.
    database.Repository.kind.get_id("image")
    database.Repository.kind.get_name(1)

    with client_with_identity("devtable", client) as cl:
        params = {"query": query}
        with assert_query_count(4):
            result = conduct_api_call(cl, ConductRepositorySearch, "GET", params, None, 200).json
            assert result["start_index"] == 0
            assert result["page"] == 1
            assert len(result["results"])


@pytest.mark.parametrize(
    "query",
    [
        ("simple"),
        ("public"),
        ("repository"),
    ],
)
def test_search_query_count(query, client):
    with client_with_identity("devtable", client) as cl:
        params = {"query": query}
        with assert_query_count(10):
            result = conduct_api_call(cl, ConductSearch, "GET", params, None, 200).json
            assert len(result["results"])


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0,
    reason="MySQL FULLTEXT indexes don't update synchronously",
)
@pytest.mark.parametrize(
    "page_count",
    [
        1,
        2,
        4,
        6,
    ],
)
def test_repository_search_pagination(page_count, client):
    # Create at least a few pages of results.
    all_repositories = set()
    user = model.user.get_user("devtable")
    for index in range(0, MAX_PER_PAGE * page_count):
        repo_name = "somerepo%s" % index
        all_repositories.add(repo_name)
        model.repository.create_repository("devtable", repo_name, user)

    with client_with_identity("devtable", client) as cl:
        for page_index in range(0, page_count):
            params = {"query": "somerepo", "page": page_index + 1}

            repo_results = conduct_api_call(
                cl, ConductRepositorySearch, "GET", params, None, 200
            ).json
            assert len(repo_results["results"]) <= MAX_PER_PAGE
            for repo in repo_results["results"]:
                all_repositories.remove(repo["name"])

            if page_index < page_count - 1:
                assert len(repo_results["results"]) == MAX_PER_PAGE
                assert repo_results["has_additional"]
            else:
                assert not repo_results["has_additional"]

    assert not all_repositories
