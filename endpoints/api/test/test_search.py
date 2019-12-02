import pytest

from playhouse.test_utils import assert_query_count

from data import model, database
from endpoints.api.search import ConductRepositorySearch, ConductSearch
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


@pytest.mark.parametrize("query", [(""), ("simple"), ("public"), ("repository"),])
def test_repository_search(query, client):
    # Prime the caches.
    database.Repository.kind.get_id("image")
    database.Repository.kind.get_name(1)

    with client_with_identity("devtable", client) as cl:
        params = {"query": query}
        with assert_query_count(7):
            result = conduct_api_call(cl, ConductRepositorySearch, "GET", params, None, 200).json
            assert result["start_index"] == 0
            assert result["page"] == 1
            assert len(result["results"])


@pytest.mark.parametrize("query", [("simple"), ("public"), ("repository"),])
def test_search_query_count(query, client):
    with client_with_identity("devtable", client) as cl:
        params = {"query": query}
        with assert_query_count(10):
            result = conduct_api_call(cl, ConductSearch, "GET", params, None, 200).json
            assert len(result["results"])
