import os.path

from datetime import datetime, timedelta

from app import storage

from data import model
from data.database import LogEntry, LogEntry2, LogEntry3
from data.logs_model.elastic_logs import INDEX_NAME_PREFIX, INDEX_DATE_FORMAT
from data.logs_model.datatypes import AggregatedLogCount, LogEntriesPage, Log
from data.logs_model.document_logs_model import DocumentLogsModel
from data.logs_model.test.fake_elasticsearch import FAKE_ES_HOST, fake_elasticsearch
from data.logs_model.table_logs_model import TableLogsModel
from data.logs_model.combined_model import CombinedLogsModel
from data.logs_model.inmemory_model import InMemoryModel

from data.logs_model import LogsModelProxy

from util.timedeltastring import convert_to_timedelta
from workers.logrotateworker import LogRotateWorker, SAVE_PATH, SAVE_LOCATION

from test.fixtures import *


@pytest.fixture()
def clear_db_logs(initialized_db):
    LogEntry.delete().execute()
    LogEntry2.delete().execute()
    LogEntry3.delete().execute()


def combined_model():
    return CombinedLogsModel(TableLogsModel(), InMemoryModel())


def es_model():
    return DocumentLogsModel(
        producer="elasticsearch", elasticsearch_config={"host": FAKE_ES_HOST, "port": 12345,}
    )


@pytest.fixture()
def fake_es():
    with fake_elasticsearch():
        yield


@pytest.fixture(params=[TableLogsModel, es_model, InMemoryModel, combined_model])
def logs_model(request, clear_db_logs, fake_es):
    model = request.param()
    with patch("data.logs_model.logs_model", model):
        with patch("workers.logrotateworker.logs_model", model):
            yield model


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


def test_logrotateworker(logs_model):
    worker = LogRotateWorker()
    days = 90
    start_timestamp = datetime(2019, 1, 1)

    # Make sure there are no existing logs
    found = _lookup_logs(
        logs_model, start_timestamp - timedelta(days=1000), start_timestamp + timedelta(days=1000)
    )
    assert not found

    # Create some logs
    for day in range(0, days):
        logs_model.log_action(
            "push_repo",
            namespace_name="devtable",
            repository_name="simple",
            ip="1.2.3.4",
            timestamp=start_timestamp - timedelta(days=day),
        )

    # Ensure there are logs.
    logs = _lookup_logs(
        logs_model, start_timestamp - timedelta(days=1000), start_timestamp + timedelta(days=1000)
    )

    assert len(logs) == days

    # Archive all the logs.
    assert worker._perform_archiving(start_timestamp + timedelta(days=1))

    # Ensure all the logs were archived.
    found = _lookup_logs(
        logs_model, start_timestamp - timedelta(days=1000), start_timestamp + timedelta(days=1000)
    )
    assert not found


def test_logrotateworker_with_cutoff(logs_model):
    days = 60
    start_timestamp = datetime(2019, 1, 1)

    # Make sure there are no existing logs
    found = _lookup_logs(
        logs_model, start_timestamp - timedelta(days=365), start_timestamp + timedelta(days=365)
    )
    assert not found

    # Create a new set of logs/indices.
    for day in range(0, days):
        logs_model.log_action(
            "push_repo",
            namespace_name="devtable",
            repository_name="simple",
            ip="1.2.3.4",
            timestamp=start_timestamp + timedelta(days=day),
        )

    # Get all logs
    logs = _lookup_logs(
        logs_model,
        start_timestamp - timedelta(days=days - 1),
        start_timestamp + timedelta(days=days + 1),
    )

    assert len(logs) == days

    # Set the cutoff datetime to be the midpoint of the logs
    midpoint = logs[0 : len(logs) // 2]
    assert midpoint
    assert len(midpoint) < len(logs)

    worker = LogRotateWorker()
    cutoff_date = midpoint[-1].datetime

    # Archive the indices at or older than the cutoff date
    archived_files = worker._perform_archiving(cutoff_date)

    # Ensure the eariler logs were archived
    found = _lookup_logs(logs_model, start_timestamp, cutoff_date - timedelta(seconds=1))
    assert not found

    # Check that the files were written to storage
    for archived_file in archived_files:
        assert storage.exists([SAVE_LOCATION], os.path.join(SAVE_PATH, archived_file))

    # If current model uses ES, check that the indices were also deleted
    if isinstance(logs_model, DocumentLogsModel):
        assert len(logs_model.list_indices()) == days - (len(logs) // 2)
        for index in logs_model.list_indices():
            dt = datetime.strptime(index[len(INDEX_NAME_PREFIX) :], INDEX_DATE_FORMAT)
            assert dt >= cutoff_date
