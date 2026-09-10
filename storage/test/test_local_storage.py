import hashlib
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from storage import StorageContext
from storage.local import LocalStorage

_TEST_LOG_PATH = "exportedactionlogs/"


@pytest.fixture
def temp_storage_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class FakeLocalStorage(LocalStorage):
    def __init__(self, storage_path):
        context = StorageContext("nyc", None, None, None)
        super().__init__(context, storage_path)
        self._root_path = storage_path


def test_put_content_successful(tmpdir):
    """
    Verifies that putting of content is successful to a
    temporary directory.
    """
    store_path = os.path.join(tmpdir, "datastorage/registry")
    storage_engine = FakeLocalStorage(store_path)

    logging.debug("TMPDIR: %s", tmpdir)
    logging.debug("STORE PATH: %s", store_path)

    payload = os.urandom(1024)
    digest = hashlib.sha256(payload).hexdigest()
    key = f"sha256/{digest[:2]}/{digest}"
    full_path = os.path.join(store_path, key)

    logging.debug(full_path)

    storage_engine.put_content(path=key, content=payload)

    assert os.path.exists(full_path)
    logging.debug(os.stat(full_path))

def test_cleanup_of_orphaned_export_log_files_successful(tmpdir):
    """
    Verifies that the worker can clean up orphaned exported log files.
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage/registry")

    storage_engine = FakeLocalStorage(store_path)

    logging.debug("TMPDIR: %s", tmpdir)
    logging.debug("STORE PATH: %s", store_path)

    payload = b'{"logs": []}'
    upload_key = f"{_TEST_LOG_PATH}/{str(uuid.uuid4())}-{str(uuid.uuid4())}"

    # put file on path
    storage_engine.put_content(path=upload_key, content=payload)

    # assert file is uploaded
    full_path = os.path.join(store_path, upload_key)
    logging.debug("FULL PATH: %s", full_path)
    directory_content = storage_engine.list_directory(os.path.join(store_path, _TEST_LOG_PATH))
    logging.debug("DIRECTORY CONTENT: %s", directory_content)
    assert os.path.exists(full_path)

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # assert that path was deleted
    assert os.path.exists(full_path) is False

def test_export_log_cleanup_does_not_touch_user_files(tmpdir):
    """
    Verifies that other files in the same path are not picked up by the
    cleanup worker.
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage_registry")
    storage_engine = FakeLocalStorage(store_path)

    payload1 = b'{"logs": []}'
    payload2 = b"Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"{_TEST_LOG_PATH}{userfile}"

    # upload both files
    storage_engine.put_content(path=upload_key_logfile, content=payload1)
    storage_engine.put_content(path=upload_key_userfile, content=payload2)

    # verify that the files are there
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST: %s", files)
    assert len(files) == 2

    # clean up files
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # traverse the directory once again, verify that only one file is present
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST: %s", files)
    assert len(files) == 1
    assert files[0].endswith("hello.txt")

def test_export_log_cleanup_doesnt_touch_other_paths(tmpdir):
    """
    Verifies that all other paths other than the log path are untouched by the
    cleanup worker.
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage_registry")
    storage_engine = FakeLocalStorage(store_path)

    payload1 = b'{"logs": []}'
    payload2 = b"Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"different/path/altogether/{userfile}"

    # upload both files
    storage_engine.put_content(path=upload_key_logfile, content=payload1)
    storage_engine.put_content(path=upload_key_userfile, content=payload2)

    # verify that the files are there
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST: %s", files)
    assert len(files) == 2

    # clean up files
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)       

    # traverse the directory once again, verify that only one file is present
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST: %s", files)
    assert len(files) == 1
    assert files[0].endswith("hello.txt")   

def test_export_log_cleanup_doesnt_pick_up_files_that_are_inside_the_timedelta(tmpdir):
    """
    Verifies that we only delete files that are older than 1 hour and not any other files that are in the same path
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage_registry")
    storage_engine = FakeLocalStorage(store_path)

    # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        # save current mock time
        mocked_time = now + timedelta(hours=i)

        with freeze_time(mocked_time):
            storage_engine.put_content(path=k, content=payload)
            full_file_path = os.path.join(store_path, k)
            fake_epoch = mocked_time.timestamp()
            os.utime(full_file_path, (fake_epoch, fake_epoch))

    # verify that the files are there
    dir_path = Path(store_path)
    logging.debug("FILE LIST:")
    for f in dir_path.rglob('*'):
        if f.is_file():
            stats = f.stat()
            logging.debug("%s", stats)

    # add 6th file only 30 minutes *after* the last file was uploaded
    final_key = f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    payload = os.urandom(1024)
    mocked_time_6 = now + timedelta(hours=5.5)
    with freeze_time(mocked_time_6):
        storage_engine.put_content(path=final_key, content=payload)
        fake_epoch = mocked_time_6.timestamp()
        full_file_path = os.path.join(store_path, final_key)
        os.utime(full_file_path, (fake_epoch, fake_epoch))

    # verify that there are 6 files in the directory
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    assert len(files) == 6

    # at 6th hour do cleanup
    with freeze_time(
        now + timedelta(hours=6)
    ):  # Changed from 5 to 6 so it occurs after the 5.5h upload
        storage_engine.clean_exported_action_logs(timedelta(hours=1), _TEST_LOG_PATH)   

    # list files to make sure that only one remains
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST: %s", files)
    assert len(files) == 1
    assert files[0].endswith(final_key)

def test_export_log_cleanup_does_not_return_error_on_empty_directory(tmpdir):
    """
    Verifies that cleanup does not error when nothing is cleaned. Simple regression test.
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage_registry")
    storage_engine = FakeLocalStorage(store_path)

    payload = os.urandom(1024)
    digest = hashlib.sha256(payload).hexdigest()
    key = f"sha256/{digest[:2]}/{digest}"
    full_path = os.path.join(store_path, key)

    # upload file
    storage_engine.put_content(full_path, content=payload)

    # assert the file is there
    assert os.path.exists(full_path)

    # attempt cleanup on empty directory
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # assert that the previous file still exists
    assert os.path.exists(full_path)

def test_cleanup_of_expired_logs_gracefully_handles_errors(tmpdir):
    """
    Asserts that the OSError exception does not terminate cleanup of files.
    """
    now = datetime.now(timezone.utc)
    store_path = os.path.join(tmpdir, "datastorage_registry")
    storage_engine = FakeLocalStorage(store_path)

        # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        storage_engine.put_content(path=k, content=payload)

    # verify that there are 5 files in the directory
    dir_path = Path(store_path)
    logging.debug("FILE LIST:")
    for f in dir_path.rglob('*'):
        if f.is_file():
            stats = f.stat()
            logging.debug("%s", stats)

    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    assert len(files) == 5

    # mock original remove
    orig_remove = os.remove

    def mock_remove_file(filename):
        if filename.endswith(keys[2]):
            raise OSError("File not found")
        return orig_remove(filename)

    # conduct deletion using the interceptor
    with patch.object(os, "remove", new=mock_remove_file):
        with freeze_time(timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # check files in the directory, ensure only one remains
    dir_path = Path(store_path)
    files = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    logging.debug("FILE LIST AFTER DELETION: %s", files)
    assert len(files) == 1
    assert files[0].endswith(keys[2])

