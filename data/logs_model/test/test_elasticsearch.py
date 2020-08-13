# -*- coding: utf-8 -*-

# pylint: disable=redefined-outer-name, wildcard-import

import json
from datetime import datetime, timedelta

import pytest
from mock import patch, Mock
from dateutil.parser import parse

from httmock import urlmatch, HTTMock

from data.model.log import _json_serialize
from data.logs_model.elastic_logs import ElasticsearchLogs, INDEX_NAME_PREFIX, INDEX_DATE_FORMAT
from data.logs_model import configure, LogsModelProxy
from .mock_elasticsearch import *

FAKE_ES_HOST = "fakees"
FAKE_ES_HOST_PATTERN = r"fakees.*"
FAKE_ES_PORT = 443
FAKE_AWS_ACCESS_KEY = None
FAKE_AWS_SECRET_KEY = None
FAKE_AWS_REGION = None


@pytest.fixture()
def logs_model_config():
    conf = {
        "LOGS_MODEL": "elasticsearch",
        "LOGS_MODEL_CONFIG": {
            "producer": "elasticsearch",
            "elasticsearch_config": {
                "host": FAKE_ES_HOST,
                "port": FAKE_ES_PORT,
                "access_key": FAKE_AWS_ACCESS_KEY,
                "secret_key": FAKE_AWS_SECRET_KEY,
                "aws_region": FAKE_AWS_REGION,
            },
        },
    }
    return conf


FAKE_LOG_ENTRY_KINDS = {"push_repo": 1, "pull_repo": 2}
FAKE_NAMESPACES = {
    "user1": Mock(
        id=1,
        organization="user1.organization",
        username="user1.username",
        email="user1.email",
        robot="user1.robot",
    ),
    "user2": Mock(
        id=2,
        organization="user2.organization",
        username="user2.username",
        email="user2.email",
        robot="user2.robot",
    ),
}
FAKE_REPOSITORIES = {
    "user1/repo1": Mock(id=1, namespace_user=FAKE_NAMESPACES["user1"]),
    "user2/repo2": Mock(id=2, namespace_user=FAKE_NAMESPACES["user2"]),
}


@pytest.fixture()
def logs_model():
    # prevent logs model from changing
    logs_model = LogsModelProxy()
    with patch("data.logs_model.logs_model", logs_model):
        yield logs_model


@pytest.fixture(scope="function")
def app_config(logs_model_config):
    fake_config = {}
    fake_config.update(logs_model_config)
    with patch("data.logs_model.document_logs_model.config.app_config", fake_config):
        yield fake_config


@pytest.fixture()
def mock_page_size():
    with patch("data.logs_model.document_logs_model.PAGE_SIZE", 1):
        yield


@pytest.fixture()
def mock_max_result_window():
    with patch("data.logs_model.document_logs_model.DEFAULT_RESULT_WINDOW", 1):
        yield


@pytest.fixture
def mock_random_id():
    mock_random = Mock(return_value=233)
    with patch("data.logs_model.document_logs_model._random_id", mock_random):
        yield


@pytest.fixture()
def mock_db_model():
    def get_user_map_by_ids(namespace_ids):
        mapping = {}
        for i in namespace_ids:
            for name in FAKE_NAMESPACES:
                if FAKE_NAMESPACES[name].id == i:
                    mapping[i] = FAKE_NAMESPACES[name]
        return mapping

    model = Mock(
        user=Mock(
            get_namespace_user=FAKE_NAMESPACES.get,
            get_user_or_org=FAKE_NAMESPACES.get,
            get_user=FAKE_NAMESPACES.get,
            get_user_map_by_ids=get_user_map_by_ids,
        ),
        repository=Mock(
            get_repository=lambda user_name, repo_name: FAKE_REPOSITORIES.get(
                user_name + "/" + repo_name
            ),
        ),
        log=Mock(
            _get_log_entry_kind=lambda name: FAKE_LOG_ENTRY_KINDS[name],
            _json_serialize=_json_serialize,
            get_log_entry_kinds=Mock(return_value=FAKE_LOG_ENTRY_KINDS),
        ),
    )

    with patch("data.logs_model.document_logs_model.model", model), patch(
        "data.logs_model.datatypes.model", model
    ):
        yield


def parse_query(query):
    return {s.split("=")[0]: s.split("=")[1] for s in query.split("&") if s != ""}


@pytest.fixture()
def mock_elasticsearch():
    mock = Mock()
    mock.template.side_effect = NotImplementedError
    mock.index.side_effect = NotImplementedError
    mock.count.side_effect = NotImplementedError
    mock.scroll_get.side_effect = NotImplementedError
    mock.scroll_delete.side_effect = NotImplementedError
    mock.search_scroll_create.side_effect = NotImplementedError
    mock.search_aggs.side_effect = NotImplementedError
    mock.search_after.side_effect = NotImplementedError
    mock.list_indices.side_effect = NotImplementedError

    @urlmatch(netloc=r".*", path=r".*")
    def default(url, req):
        raise Exception(
            "\nurl={}\nmethod={}\nreq.url={}\nheaders={}\nbody={}".format(
                url, req.method, req.url, req.headers, req.body
            )
        )

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/_template/.*")
    def template(url, req):
        return mock.template(url.query.split("/")[-1], req.body)

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/logentry_(\*|[0-9\-]+)")
    def list_indices(url, req):
        return mock.list_indices()

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/logentry_[0-9\-]*/_doc")
    def index(url, req):
        index = url.path.split("/")[1]
        body = json.loads(req.body)

        return mock.index(index, body)

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/logentry_([0-9\-]*|\*)/_count")
    def count(_, req):
        return mock.count(json.loads(req.body))

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/_search/scroll")
    def scroll(url, req):
        if req.method == "DELETE":
            return mock.scroll_delete(json.loads(req.body))
        elif req.method == "GET":
            request_obj = json.loads(req.body)
            return mock.scroll_get(request_obj)
        raise NotImplementedError()

    @urlmatch(netloc=FAKE_ES_HOST_PATTERN, path=r"/logentry_(\*|[0-9\-]*)/_search")
    def search(url, req):
        if "scroll" in url.query:
            query = parse_query(url.query)
            window_size = query["scroll"]
            maximum_result_size = int(query["size"])
            return mock.search_scroll_create(window_size, maximum_result_size, json.loads(req.body))
        elif b"aggs" in req.body:
            return mock.search_aggs(json.loads(req.body))
        else:
            return mock.search_after(json.loads(req.body))

    with HTTMock(scroll, count, search, index, template, list_indices, default):
        yield mock


@pytest.mark.parametrize(
    """
  unlogged_pulls_ok, kind_name, namespace_name, repository, repository_name,
  timestamp,
  index_response, expected_request, throws
  """,
    [
        # Invalid inputs
        pytest.param(
            False, "non-existing", None, None, None, None, None, None, True, id="Invalid Kind"
        ),
        pytest.param(
            False,
            "pull_repo",
            "user1",
            Mock(id=1),
            "repo1",
            None,
            None,
            None,
            True,
            id="Invalid Parameters",
        ),
        # Remote exceptions
        pytest.param(
            False,
            "pull_repo",
            "user1",
            Mock(id=1),
            None,
            None,
            FAILURE_400,
            None,
            True,
            id="Throw on pull log failure",
        ),
        pytest.param(
            True,
            "pull_repo",
            "user1",
            Mock(id=1),
            None,
            parse("2017-03-08T03:30"),
            FAILURE_400,
            INDEX_REQUEST_2017_03_08,
            False,
            id="Ok on pull log failure",
        ),
        # Success executions
        pytest.param(
            False,
            "pull_repo",
            "user1",
            Mock(id=1),
            None,
            parse("2017-03-08T03:30"),
            INDEX_RESPONSE_2017_03_08,
            INDEX_REQUEST_2017_03_08,
            False,
            id="Log with namespace name and repository",
        ),
        pytest.param(
            False,
            "push_repo",
            "user1",
            None,
            "repo1",
            parse("2019-01-01T03:30"),
            INDEX_RESPONSE_2019_01_01,
            INDEX_REQUEST_2019_01_01,
            False,
            id="Log with namespace name and repository name",
        ),
    ],
)
def test_log_action(
    unlogged_pulls_ok,
    kind_name,
    namespace_name,
    repository,
    repository_name,
    timestamp,
    index_response,
    expected_request,
    throws,
    app_config,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
    mock_random_id,
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)
    mock_elasticsearch.index = Mock(return_value=index_response)
    app_config["ALLOW_PULLS_WITHOUT_STRICT_LOGGING"] = unlogged_pulls_ok
    configure(app_config)

    performer = Mock(id=1)
    ip = "192.168.1.1"
    metadata = {"key": "value", "time": parse("2018-03-08T03:30"), "😂": "😂👌👌👌👌"}
    if throws:
        with pytest.raises(Exception):
            logs_model.log_action(
                kind_name,
                namespace_name,
                performer,
                ip,
                metadata,
                repository,
                repository_name,
                timestamp,
            )
    else:
        logs_model.log_action(
            kind_name,
            namespace_name,
            performer,
            ip,
            metadata,
            repository,
            repository_name,
            timestamp,
        )

        mock_elasticsearch.index.assert_called_with(expected_request[0], expected_request[1])


@pytest.mark.parametrize(
    """
  start_datetime, end_datetime,
  performer_name, repository_name, namespace_name,
  filter_kinds,
  page_token,
  max_page_count,
  search_response,
  list_indices_response,
  expected_request,
  expected_page,
  throws
  """,
    [
        # 1st page
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-08T03:30"),
            "user1",
            "repo1",
            "user1",
            None,
            None,
            None,
            SEARCH_RESPONSE_START,
            INDEX_LIST_RESPONSE_HIT1_HIT2,
            SEARCH_REQUEST_START,
            SEARCH_PAGE_START,
            False,
            id="1st page",
        ),
        # Last page
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-08T03:30"),
            "user1",
            "repo1",
            "user1",
            None,
            SEARCH_PAGE_TOKEN,
            None,
            SEARCH_RESPONSE_END,
            INDEX_LIST_RESPONSE_HIT1_HIT2,
            SEARCH_REQUEST_END,
            SEARCH_PAGE_END,
            False,
            id="Search using pagination token",
        ),
        # Filter
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-08T03:30"),
            "user1",
            "repo1",
            "user1",
            ["push_repo"],
            None,
            None,
            SEARCH_RESPONSE_END,
            INDEX_LIST_RESPONSE_HIT2,
            SEARCH_REQUEST_FILTER,
            SEARCH_PAGE_END,
            False,
            id="Filtered search",
        ),
        # Max page count
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-08T03:30"),
            "user1",
            "repo1",
            "user1",
            None,
            SEARCH_PAGE_TOKEN,
            1,
            AssertionError,  # Assert that it should not reach the ES server
            None,
            None,
            SEARCH_PAGE_EMPTY,
            False,
            id="Page token reaches maximum page count",
        ),
    ],
)
def test_lookup_logs(
    start_datetime,
    end_datetime,
    performer_name,
    repository_name,
    namespace_name,
    filter_kinds,
    page_token,
    max_page_count,
    search_response,
    list_indices_response,
    expected_request,
    expected_page,
    throws,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
    mock_page_size,
    app_config,
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)
    mock_elasticsearch.search_after = Mock(return_value=search_response)
    mock_elasticsearch.list_indices = Mock(return_value=list_indices_response)

    configure(app_config)
    if throws:
        with pytest.raises(Exception):
            logs_model.lookup_logs(
                start_datetime,
                end_datetime,
                performer_name,
                repository_name,
                namespace_name,
                filter_kinds,
                page_token,
                max_page_count,
            )
    else:
        page = logs_model.lookup_logs(
            start_datetime,
            end_datetime,
            performer_name,
            repository_name,
            namespace_name,
            filter_kinds,
            page_token,
            max_page_count,
        )
        assert page == expected_page
        if expected_request:
            mock_elasticsearch.search_after.assert_called_with(expected_request)


@pytest.mark.parametrize(
    """
  start_datetime, end_datetime,
  performer_name, repository_name, namespace_name,
  filter_kinds, search_response, expected_request, expected_counts, throws
  """,
    [
        # Valid
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-08T03:30"),
            "user1",
            "repo1",
            "user1",
            ["pull_repo"],
            AGGS_RESPONSE,
            AGGS_REQUEST,
            AGGS_COUNT,
            False,
            id="Valid Counts",
        ),
        # Invalid case: date range too big
        pytest.param(
            parse("2018-03-08T03:30"),
            parse("2018-04-09T03:30"),
            "user1",
            "repo1",
            "user1",
            [],
            None,
            None,
            None,
            True,
            id="Throw on date range too big",
        ),
    ],
)
def test_get_aggregated_log_counts(
    start_datetime,
    end_datetime,
    performer_name,
    repository_name,
    namespace_name,
    filter_kinds,
    search_response,
    expected_request,
    expected_counts,
    throws,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
    app_config,
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)
    mock_elasticsearch.search_aggs = Mock(return_value=search_response)

    configure(app_config)
    if throws:
        with pytest.raises(Exception):
            logs_model.get_aggregated_log_counts(
                start_datetime,
                end_datetime,
                performer_name,
                repository_name,
                namespace_name,
                filter_kinds,
            )
    else:
        counts = logs_model.get_aggregated_log_counts(
            start_datetime,
            end_datetime,
            performer_name,
            repository_name,
            namespace_name,
            filter_kinds,
        )
        assert set(counts) == set(expected_counts)
        if expected_request:
            mock_elasticsearch.search_aggs.assert_called_with(expected_request)


@pytest.mark.parametrize(
    """
  repository,
  day,
  count_response, expected_request, expected_count, throws
  """,
    [
        pytest.param(
            FAKE_REPOSITORIES["user1/repo1"],
            parse("2018-03-08").date(),
            COUNT_RESPONSE,
            COUNT_REQUEST,
            1,
            False,
            id="Valid Count with 1 as result",
        ),
    ],
)
def test_count_repository_actions(
    repository,
    day,
    count_response,
    expected_request,
    expected_count,
    throws,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
    app_config,
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)
    mock_elasticsearch.count = Mock(return_value=count_response)
    mock_elasticsearch.list_indices = Mock(return_value=INDEX_LIST_RESPONSE)

    configure(app_config)
    if throws:
        with pytest.raises(Exception):
            logs_model.count_repository_actions(repository, day)
    else:
        count = logs_model.count_repository_actions(repository, day)
        assert count == expected_count
        if expected_request:
            mock_elasticsearch.count.assert_called_with(expected_request)


@pytest.mark.parametrize(
    """
  start_datetime, end_datetime,
  repository_id, namespace_id,
  max_query_time, scroll_responses, expected_requests, expected_logs, throws
  """,
    [
        pytest.param(
            parse("2018-03-08"),
            parse("2018-04-02"),
            1,
            1,
            timedelta(seconds=10),
            SCROLL_RESPONSES,
            SCROLL_REQUESTS,
            SCROLL_LOGS,
            False,
            id="Scroll 3 pages with page size = 1",
        ),
    ],
)
def test_yield_logs_for_export(
    start_datetime,
    end_datetime,
    repository_id,
    namespace_id,
    max_query_time,
    scroll_responses,
    expected_requests,
    expected_logs,
    throws,
    logs_model,
    mock_elasticsearch,
    mock_db_model,
    mock_max_result_window,
    app_config,
):
    mock_elasticsearch.template = Mock(return_value=DEFAULT_TEMPLATE_RESPONSE)
    mock_elasticsearch.search_scroll_create = Mock(return_value=scroll_responses[0])
    mock_elasticsearch.scroll_get = Mock(side_effect=scroll_responses[1:-1])
    mock_elasticsearch.scroll_delete = Mock(return_value=scroll_responses[-1])

    configure(app_config)
    if throws:
        with pytest.raises(Exception):
            logs_model.yield_logs_for_export(
                start_datetime, end_datetime, max_query_time=max_query_time
            )
    else:
        log_generator = logs_model.yield_logs_for_export(
            start_datetime, end_datetime, max_query_time=max_query_time
        )
        counter = 0
        for logs in log_generator:
            if counter == 0:
                mock_elasticsearch.search_scroll_create.assert_called_with(
                    *expected_requests[counter]
                )
            else:
                mock_elasticsearch.scroll_get.assert_called_with(*expected_requests[counter])
            assert expected_logs[counter] == logs
            counter += 1
        # the last two requests must be
        # 1. get with response scroll with 0 hits, which indicates the termination condition
        # 2. delete scroll request
        mock_elasticsearch.scroll_get.assert_called_with(*expected_requests[-2])
        mock_elasticsearch.scroll_delete.assert_called_with(*expected_requests[-1])


@pytest.mark.parametrize(
    "prefix, is_valid",
    [
        pytest.param("..", False, id="Invalid `..`"),
        pytest.param(".", False, id="Invalid `.`"),
        pytest.param("-prefix", False, id="Invalid prefix start -"),
        pytest.param("_prefix", False, id="Invalid prefix start _"),
        pytest.param("+prefix", False, id="Invalid prefix start +"),
        pytest.param("prefix_with_UPPERCASES", False, id="Invalid uppercase"),
        pytest.param("valid_index", True, id="Valid prefix"),
        pytest.param("valid_index_with_numbers1234", True, id="Valid prefix with numbers"),
        pytest.param("a" * 256, False, id="Prefix too long"),
    ],
)
def test_valid_index_prefix(prefix, is_valid):
    assert ElasticsearchLogs._valid_index_prefix(prefix) == is_valid


@pytest.mark.parametrize(
    "index, cutoff_date, expected_result",
    [
        pytest.param(
            INDEX_NAME_PREFIX + "2019-06-06",
            datetime(2019, 6, 8),
            True,
            id="Index older than cutoff",
        ),
        pytest.param(
            INDEX_NAME_PREFIX + "2019-06-06",
            datetime(2019, 6, 4),
            False,
            id="Index younger than cutoff",
        ),
        pytest.param(
            INDEX_NAME_PREFIX + "2019-06-06",
            datetime(2019, 6, 6, 23),
            False,
            id="Index older than cutoff but timedelta less than 1 day",
        ),
        pytest.param(
            INDEX_NAME_PREFIX + "2019-06-06",
            datetime(2019, 6, 7),
            True,
            id="Index older than cutoff by exactly one day",
        ),
    ],
)
def test_can_delete_index(index, cutoff_date, expected_result):
    es = ElasticsearchLogs(index_prefix=INDEX_NAME_PREFIX)
    assert datetime.strptime(index.split(es._index_prefix, 1)[-1], INDEX_DATE_FORMAT)
    assert es.can_delete_index(index, cutoff_date) == expected_result
