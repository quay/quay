import json
import os

from datetime import datetime, timedelta

import boto

from httmock import urlmatch, HTTMock
from moto import mock_s3_deprecated as mock_s3

from app import storage as test_storage
from data import model, database
from data.logs_model import logs_model
from storage import S3Storage, StorageContext, DistributedStorage
from workers.exportactionlogsworker import ExportActionLogsWorker, POLL_PERIOD_SECONDS

from test.fixtures import *


_TEST_CONTENT = os.urandom(1024)
_TEST_BUCKET = "some_bucket"
_TEST_USER = "someuser"
_TEST_PASSWORD = "somepassword"
_TEST_PATH = "some/cool/path"
_TEST_CONTEXT = StorageContext("nyc", None, None, None)


@pytest.fixture(params=["test", "mock_s3"])
def storage_engine(request):
    if request.param == "test":
        yield test_storage
    else:
        with mock_s3():
            # Create a test bucket and put some test content.
            boto.connect_s3().create_bucket(_TEST_BUCKET)
            engine = DistributedStorage(
                {
                    "foo": S3Storage(
                        _TEST_CONTEXT, "some/path", _TEST_BUCKET, _TEST_USER, _TEST_PASSWORD
                    )
                },
                ["foo"],
            )
            yield engine


def test_export_logs_failure(initialized_db):
    # Make all uploads fail.
    test_storage.put_content("local_us", "except_upload", b"true")

    repo = model.repository.get_repository("devtable", "simple")
    user = model.user.get_user("devtable")

    worker = ExportActionLogsWorker(None)
    called = [{}]

    @urlmatch(netloc=r"testcallback")
    def handle_request(url, request):
        called[0] = json.loads(request.body)
        return {"status_code": 200, "content": "{}"}

    def format_date(datetime):
        return datetime.strftime("%m/%d/%Y")

    now = datetime.now()
    with HTTMock(handle_request):
        with pytest.raises(IOError):
            worker._process_queue_item(
                {
                    "export_id": "someid",
                    "repository_id": repo.id,
                    "namespace_id": repo.namespace_user.id,
                    "namespace_name": "devtable",
                    "repository_name": "simple",
                    "start_time": format_date(now + timedelta(days=-10)),
                    "end_time": format_date(now + timedelta(days=10)),
                    "callback_url": "http://testcallback/",
                    "callback_email": None,
                },
                test_storage,
            )

    test_storage.remove("local_us", "except_upload")

    assert called[0]
    assert called[0]["export_id"] == "someid"
    assert called[0]["status"] == "failed"


@pytest.mark.parametrize(
    "has_logs",
    [
        True,
        False,
    ],
)
def test_export_logs(initialized_db, storage_engine, has_logs):
    # Delete all existing logs.
    database.LogEntry3.delete().execute()

    repo = model.repository.get_repository("devtable", "simple")
    user = model.user.get_user("devtable")

    now = datetime.now()
    if has_logs:
        # Add new logs over a multi-day period.
        for index in range(-10, 10):
            logs_model.log_action(
                "push_repo",
                "devtable",
                user,
                "0.0.0.0",
                {"index": index},
                repo,
                timestamp=now + timedelta(days=index),
            )

    worker = ExportActionLogsWorker(None)
    called = [{}]

    @urlmatch(netloc=r"testcallback")
    def handle_request(url, request):
        called[0] = json.loads(request.body)
        return {"status_code": 200, "content": "{}"}

    def format_date(datetime):
        return datetime.strftime("%m/%d/%Y")

    with HTTMock(handle_request):
        worker._process_queue_item(
            {
                "export_id": "someid",
                "repository_id": repo.id,
                "namespace_id": repo.namespace_user.id,
                "namespace_name": "devtable",
                "repository_name": "simple",
                "start_time": format_date(now + timedelta(days=-10)),
                "end_time": format_date(now + timedelta(days=10)),
                "callback_url": "http://testcallback/",
                "callback_email": None,
            },
            storage_engine,
        )

    assert called[0]
    assert called[0]["export_id"] == "someid"
    assert called[0]["status"] == "success"

    url = called[0]["exported_data_url"]

    if url.find("http://localhost:5000/exportedlogs/") == 0:
        storage_id = url[len("http://localhost:5000/exportedlogs/") :]
    else:
        assert (
            url.find("https://some_bucket.s3.amazonaws.com:443/some/path/exportedactionlogs/") == 0
        )
        storage_id, _ = url[
            len("https://some_bucket.s3.amazonaws.com:443/some/path/exportedactionlogs/") :
        ].split("?")

    created = storage_engine.get_content(
        storage_engine.preferred_locations, "exportedactionlogs/" + storage_id
    )
    created_json = json.loads(created)

    if has_logs:
        found = set()
        for log in created_json["logs"]:
            if log.get("terminator"):
                continue

            found.add(log["metadata"]["index"])

        for index in range(-10, 10):
            assert index in found
    else:
        assert created_json["logs"] == [{"terminator": True}]
