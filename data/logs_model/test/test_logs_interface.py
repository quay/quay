from datetime import datetime, timedelta, date
from data.logs_model.datatypes import AggregatedLogCount
from data.logs_model.table_logs_model import TableLogsModel
from data.logs_model.combined_model import CombinedLogsModel
from data.logs_model.inmemory_model import InMemoryModel
from data.logs_model.combined_model import _merge_aggregated_log_counts
from data.logs_model.document_logs_model import _date_range_in_single_index, DocumentLogsModel
from data.logs_model.interface import LogsIterationTimeout
from data.logs_model.test.fake_elasticsearch import FAKE_ES_HOST, fake_elasticsearch

from data.database import LogEntry, LogEntry2, LogEntry3, LogEntryKind
from data import model

from test.fixtures import *


@pytest.fixture()
def mock_page_size():
    page_size = 2
    with patch("data.logs_model.document_logs_model.PAGE_SIZE", page_size):
        yield page_size


@pytest.fixture()
def clear_db_logs(initialized_db):
    LogEntry.delete().execute()
    LogEntry2.delete().execute()
    LogEntry3.delete().execute()


def combined_model():
    return CombinedLogsModel(TableLogsModel(), InMemoryModel())


def es_model():
    return DocumentLogsModel(
        producer="elasticsearch",
        elasticsearch_config={
            "host": FAKE_ES_HOST,
            "port": 12345,
        },
    )


@pytest.fixture()
def fake_es():
    with fake_elasticsearch():
        yield


@pytest.fixture(params=[TableLogsModel, InMemoryModel, es_model, combined_model])
def logs_model(request, clear_db_logs, fake_es):
    return request.param()


def _lookup_logs(logs_model, start_time, end_time, **kwargs):
    logs_found = []
    page_token = None
    while True:
        found = logs_model.lookup_logs(start_time, end_time, page_token=page_token, **kwargs)
        logs_found.extend(found.logs)
        page_token = found.next_page_token
        if not found.logs or not page_token:
            break

    assert len(logs_found) == len(set(logs_found))
    return logs_found


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0, reason="Flaky on MySQL"
)
@pytest.mark.parametrize(
    "namespace_name, repo_name, performer_name, check_args, expect_results",
    [
        pytest.param("devtable", "simple", "devtable", {}, True, id="no filters"),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "performer_name": "devtable",
            },
            True,
            id="matching performer",
        ),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "namespace_name": "devtable",
            },
            True,
            id="matching namespace",
        ),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "namespace_name": "devtable",
                "repository_name": "simple",
            },
            True,
            id="matching repository",
        ),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "performer_name": "public",
            },
            False,
            id="different performer",
        ),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "namespace_name": "public",
            },
            False,
            id="different namespace",
        ),
        pytest.param(
            "devtable",
            "simple",
            "devtable",
            {
                "namespace_name": "devtable",
                "repository_name": "complex",
            },
            False,
            id="different repository",
        ),
    ],
)
def test_logs(namespace_name, repo_name, performer_name, check_args, expect_results, logs_model):
    # Add some logs.
    kinds = list(LogEntryKind.select())
    user = model.user.get_user(performer_name)

    start_timestamp = datetime.utcnow()
    timestamp = start_timestamp

    for kind in kinds:
        for index in range(0, 3):
            logs_model.log_action(
                kind.name,
                namespace_name=namespace_name,
                repository_name=repo_name,
                performer=user,
                ip="1.2.3.4",
                timestamp=timestamp,
            )
            timestamp = timestamp + timedelta(seconds=1)

    found = _lookup_logs(
        logs_model, start_timestamp, start_timestamp + timedelta(minutes=10), **check_args
    )
    if expect_results:
        assert len(found) == len(kinds) * 3
    else:
        assert not found

    aggregated_counts = logs_model.get_aggregated_log_counts(
        start_timestamp, start_timestamp + timedelta(minutes=10), **check_args
    )
    if expect_results:
        assert len(aggregated_counts) == len(kinds)
        for ac in aggregated_counts:
            assert ac.count == 3
    else:
        assert not aggregated_counts


@pytest.mark.parametrize(
    "filter_kinds, expect_results",
    [
        pytest.param(None, True),
        pytest.param(["push_repo"], True, id="push_repo filter"),
        pytest.param(["pull_repo"], True, id="pull_repo filter"),
        pytest.param(["push_repo", "pull_repo"], False, id="push and pull filters"),
    ],
)
def test_lookup_latest_logs(filter_kinds, expect_results, logs_model):
    kind_map = model.log.get_log_entry_kinds()
    if filter_kinds:
        ignore_ids = [kind_map[kind_name] for kind_name in filter_kinds if filter_kinds]
    else:
        ignore_ids = []

    now = datetime.now()
    namespace_name = "devtable"
    repo_name = "simple"
    performer_name = "devtable"

    user = model.user.get_user(performer_name)
    size = 3

    # Log some push actions
    logs_model.log_action(
        "push_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=1, seconds=11),
    )
    logs_model.log_action(
        "push_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=7, seconds=33),
    )

    # Log some pull actions
    logs_model.log_action(
        "pull_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=0, seconds=3),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=3, seconds=55),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=5, seconds=3),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name=namespace_name,
        repository_name=repo_name,
        performer=user,
        ip="0.0.0.0",
        timestamp=now - timedelta(days=11, seconds=11),
    )

    # Get the latest logs
    latest_logs = logs_model.lookup_latest_logs(
        performer_name, repo_name, namespace_name, filter_kinds=filter_kinds, size=size
    )

    # Test max lookup size
    assert len(latest_logs) <= size

    # Make sure that the latest logs returned are in decreasing order
    assert all(x >= y for x, y in zip(latest_logs, latest_logs[1:]))

    if expect_results:
        assert latest_logs

        # Lookup all logs filtered by kinds and sort them in reverse chronological order
        all_logs = _lookup_logs(
            logs_model,
            now - timedelta(days=30),
            now + timedelta(days=30),
            filter_kinds=filter_kinds,
            namespace_name=namespace_name,
            repository_name=repo_name,
        )
        all_logs = sorted(all_logs, key=lambda l: l.datetime, reverse=True)

        # Check that querying all logs does not return the filtered kinds
        assert all([log.kind_id not in ignore_ids for log in all_logs])

        # Check that the latest logs contains only th most recent ones
        assert latest_logs == all_logs[: len(latest_logs)]


def test_count_repository_actions(logs_model):
    # Log some actions.
    logs_model.log_action(
        "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )
    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )
    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )

    # Log some actions to a different repo.
    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="complex", ip="1.2.3.4"
    )
    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="complex", ip="1.2.3.4"
    )

    # Count the actions.
    day = date.today()
    simple_repo = model.repository.get_repository("devtable", "simple")

    count = logs_model.count_repository_actions(simple_repo, day)
    assert count == 3

    complex_repo = model.repository.get_repository("devtable", "complex")
    count = logs_model.count_repository_actions(complex_repo, day)
    assert count == 2

    # Try counting actions for a few days in the future to ensure it doesn't raise an error.
    count = logs_model.count_repository_actions(simple_repo, day + timedelta(days=5))
    assert count == 0


def test_yield_log_rotation_context(logs_model):
    cutoff_date = datetime.now()
    min_logs_per_rotation = 3

    # Log some actions to be archived
    # One day
    logs_model.log_action(
        "push_repo",
        namespace_name="devtable",
        repository_name="simple1",
        ip="1.2.3.4",
        timestamp=cutoff_date - timedelta(days=1, seconds=1),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple2",
        ip="5.6.7.8",
        timestamp=cutoff_date - timedelta(days=1, seconds=2),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple3",
        ip="9.10.11.12",
        timestamp=cutoff_date - timedelta(days=1, seconds=3),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple4",
        ip="0.0.0.0",
        timestamp=cutoff_date - timedelta(days=1, seconds=4),
    )
    # Another day
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple5",
        ip="1.1.1.1",
        timestamp=cutoff_date - timedelta(days=2, seconds=1),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple5",
        ip="1.1.1.1",
        timestamp=cutoff_date - timedelta(days=2, seconds=2),
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple5",
        ip="1.1.1.1",
        timestamp=cutoff_date - timedelta(days=2, seconds=3),
    )

    found = _lookup_logs(
        logs_model, cutoff_date - timedelta(days=3), cutoff_date + timedelta(days=1)
    )
    assert found is not None and len(found) == 7

    # Iterate the logs using the log rotation contexts
    all_logs = []
    for log_rotation_context in logs_model.yield_log_rotation_context(
        cutoff_date, min_logs_per_rotation
    ):
        with log_rotation_context as context:
            for logs, _ in context.yield_logs_batch():
                all_logs.extend(logs)

    assert len(all_logs) == 7
    found = _lookup_logs(
        logs_model, cutoff_date - timedelta(days=3), cutoff_date + timedelta(days=1)
    )
    assert not found

    # Make sure all datetimes are monotonically increasing (by datetime) after sorting the lookup
    # to make sure no duplicates were returned
    all_logs.sort(key=lambda d: d.datetime)
    assert all(x.datetime < y.datetime for x, y in zip(all_logs, all_logs[1:]))


def test_count_repository_actions_with_wildcard_disabled(initialized_db):
    with fake_elasticsearch(allow_wildcard=False):
        logs_model = es_model()

        # Log some actions.
        logs_model.log_action(
            "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        logs_model.log_action(
            "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )
        logs_model.log_action(
            "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
        )

        # Log some actions to a different repo.
        logs_model.log_action(
            "pull_repo", namespace_name="devtable", repository_name="complex", ip="1.2.3.4"
        )
        logs_model.log_action(
            "pull_repo", namespace_name="devtable", repository_name="complex", ip="1.2.3.4"
        )

        # Count the actions.
        day = date.today()
        simple_repo = model.repository.get_repository("devtable", "simple")

        count = logs_model.count_repository_actions(simple_repo, day)
        assert count == 3

        complex_repo = model.repository.get_repository("devtable", "complex")
        count = logs_model.count_repository_actions(complex_repo, day)
        assert count == 2

        # Try counting actions for a few days in the future to ensure it doesn't raise an error.
        count = logs_model.count_repository_actions(simple_repo, day + timedelta(days=5))
        assert count == 0


@pytest.mark.skipif(
    os.environ.get("TEST_DATABASE_URI", "").find("mysql") >= 0, reason="Flaky on MySQL"
)
def test_yield_logs_for_export(logs_model):
    # Add some logs.
    kinds = list(LogEntryKind.select())
    user = model.user.get_user("devtable")

    start_timestamp = datetime.utcnow()
    timestamp = start_timestamp

    for kind in kinds:
        for index in range(0, 10):
            logs_model.log_action(
                kind.name,
                namespace_name="devtable",
                repository_name="simple",
                performer=user,
                ip="1.2.3.4",
                timestamp=timestamp,
            )
            timestamp = timestamp + timedelta(seconds=1)

    # Yield the logs.
    simple_repo = model.repository.get_repository("devtable", "simple")
    logs_found = []
    for logs in logs_model.yield_logs_for_export(
        start_timestamp, timestamp + timedelta(minutes=10), repository_id=simple_repo.id
    ):
        logs_found.extend(logs)

    # Ensure we found all added logs.
    assert len(logs_found) == len(kinds) * 10

    # Yield the logs via namespace.
    logs_found = []
    for logs in logs_model.yield_logs_for_export(
        start_timestamp,
        timestamp + timedelta(minutes=10),
        namespace_id=simple_repo.namespace_user.id,
    ):
        logs_found.extend(logs)

    # Ensure we found all added logs.
    assert len(logs_found) == len(kinds) * 10


def test_yield_logs_for_export_timeout(logs_model):
    # Add some logs.
    kinds = list(LogEntryKind.select())
    user = model.user.get_user("devtable")

    start_timestamp = datetime.utcnow()
    timestamp = start_timestamp

    for kind in kinds:
        for _ in range(0, 2):
            logs_model.log_action(
                kind.name,
                namespace_name="devtable",
                repository_name="simple",
                performer=user,
                ip="1.2.3.4",
                timestamp=timestamp,
            )
            timestamp = timestamp + timedelta(seconds=1)

    # Yield the logs. Since we set the timeout to nothing, it should immediately fail.
    simple_repo = model.repository.get_repository("devtable", "simple")
    with pytest.raises(LogsIterationTimeout):
        list(
            logs_model.yield_logs_for_export(
                start_timestamp,
                timestamp + timedelta(minutes=1),
                repository_id=simple_repo.id,
                max_query_time=timedelta(seconds=0),
            )
        )


def test_disabled_namespace(clear_db_logs):
    logs_model = TableLogsModel(lambda kind, namespace, is_free: namespace == "devtable")

    # Log some actions.
    logs_model.log_action(
        "push_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )

    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )
    logs_model.log_action(
        "pull_repo", namespace_name="devtable", repository_name="simple", ip="1.2.3.4"
    )

    # Log some actions to a different namespace.
    logs_model.log_action(
        "push_repo", namespace_name="buynlarge", repository_name="orgrepo", ip="1.2.3.4"
    )

    logs_model.log_action(
        "pull_repo", namespace_name="buynlarge", repository_name="orgrepo", ip="1.2.3.4"
    )
    logs_model.log_action(
        "pull_repo", namespace_name="buynlarge", repository_name="orgrepo", ip="1.2.3.4"
    )

    # Count the actions.
    day = datetime.today() - timedelta(minutes=60)
    simple_repo = model.repository.get_repository("devtable", "simple")
    count = logs_model.count_repository_actions(simple_repo, day)
    assert count == 0

    org_repo = model.repository.get_repository("buynlarge", "orgrepo")
    count = logs_model.count_repository_actions(org_repo, day)
    assert count == 3


@pytest.mark.parametrize(
    "aggregated_log_counts1, aggregated_log_counts2, expected_result",
    [
        pytest.param(
            [
                AggregatedLogCount(1, 3, datetime(2019, 6, 6, 0, 0)),  # 1
                AggregatedLogCount(1, 3, datetime(2019, 6, 7, 0, 0)),  # 2
            ],
            [
                AggregatedLogCount(1, 5, datetime(2019, 6, 6, 0, 0)),  # 1
                AggregatedLogCount(1, 7, datetime(2019, 6, 7, 0, 0)),  # 2
                AggregatedLogCount(3, 3, datetime(2019, 6, 1, 0, 0)),  # 3
            ],
            [
                AggregatedLogCount(1, 8, datetime(2019, 6, 6, 0, 0)),  # 1
                AggregatedLogCount(1, 10, datetime(2019, 6, 7, 0, 0)),  # 2
                AggregatedLogCount(3, 3, datetime(2019, 6, 1, 0, 0)),  # 3
            ],
        ),
        pytest.param(
            [
                AggregatedLogCount(1, 3, datetime(2019, 6, 6, 0, 0)),
            ],  # 1
            [
                AggregatedLogCount(1, 7, datetime(2019, 6, 7, 0, 0)),
            ],  # 2
            [
                AggregatedLogCount(1, 3, datetime(2019, 6, 6, 0, 0)),  # 1
                AggregatedLogCount(1, 7, datetime(2019, 6, 7, 0, 0)),  # 2
            ],
        ),
        pytest.param(
            [],
            [AggregatedLogCount(1, 3, datetime(2019, 6, 6, 0, 0))],
            [AggregatedLogCount(1, 3, datetime(2019, 6, 6, 0, 0))],
        ),
    ],
)
def test_merge_aggregated_log_counts(
    aggregated_log_counts1, aggregated_log_counts2, expected_result
):
    assert sorted(
        _merge_aggregated_log_counts(aggregated_log_counts1, aggregated_log_counts2)
    ) == sorted(expected_result)


@pytest.mark.parametrize(
    "dt1, dt2, expected_result",
    [
        # Valid dates
        pytest.param(date(2019, 6, 17), date(2019, 6, 18), True),
        # Invalid dates
        pytest.param(date(2019, 6, 17), date(2019, 6, 17), False),
        pytest.param(date(2019, 6, 17), date(2019, 6, 19), False),
        pytest.param(date(2019, 6, 18), date(2019, 6, 17), False),
        # Valid datetimes
        pytest.param(datetime(2019, 6, 17, 0, 1), datetime(2019, 6, 17, 0, 2), True),
        # Invalid datetimes
        pytest.param(datetime(2019, 6, 17, 0, 2), datetime(2019, 6, 17, 0, 1), False),
        pytest.param(
            datetime(2019, 6, 17, 11), datetime(2019, 6, 17, 11) + timedelta(hours=14), False
        ),
    ],
)
def test_date_range_in_single_index(dt1, dt2, expected_result):
    assert _date_range_in_single_index(dt1, dt2) == expected_result


def test_pagination(logs_model, mock_page_size):
    """
    Make sure that pagination does not stop if searching through multiple indices by day, and the
    current log count matches the page size while there are still indices to be searched.
    """
    day1 = datetime.now()
    day2 = day1 + timedelta(days=1)
    day3 = day2 + timedelta(days=1)

    # Log some actions in day indices
    # One day
    logs_model.log_action(
        "push_repo",
        namespace_name="devtable",
        repository_name="simple1",
        ip="1.2.3.4",
        timestamp=day1,
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple1",
        ip="5.6.7.8",
        timestamp=day1,
    )

    found = _lookup_logs(logs_model, day1 - timedelta(seconds=1), day3 + timedelta(seconds=1))
    assert len(found) == mock_page_size

    # Another day
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple2",
        ip="1.1.1.1",
        timestamp=day2,
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple2",
        ip="0.0.0.0",
        timestamp=day2,
    )

    # Yet another day
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple2",
        ip="1.1.1.1",
        timestamp=day3,
    )
    logs_model.log_action(
        "pull_repo",
        namespace_name="devtable",
        repository_name="simple2",
        ip="0.0.0.0",
        timestamp=day3,
    )

    found = _lookup_logs(logs_model, day1 - timedelta(seconds=1), day3 + timedelta(seconds=1))
    assert len(found) == 6
