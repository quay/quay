import copy
import hashlib
import io
import logging
from collections import defaultdict

import pytest
from mock import MagicMock, patch
from swiftclient.client import ClientException, ReadableToIterable
from werkzeug.wsgi import LimitedStream

from storage import StorageContext
from storage.swift import _DEFAULT_RETRY_COUNT, _EMPTY_SEGMENTS_KEY, SwiftStorage
from util.registry import filelike
from util.registry.generatorfile import GeneratorFile

_TEST_LOG_PATH = "exportedactionlogs/"
import datetime
import hashlib
import os
import uuid
from datetime import timedelta

from freezegun import freeze_time

base_args = {
    "context": StorageContext("nyc", None, None, None),
    "swift_container": "container-name",
    "storage_path": "/basepath",
    "auth_url": "https://auth.com",
    "swift_user": "root",
    "swift_password": "password",
}


class MockSwiftStorage(SwiftStorage):
    def __init__(self, *args, **kwargs):
        super(MockSwiftStorage, self).__init__(*args, **kwargs)
        self._connection = MagicMock()

    def _get_connection(self):
        return self._connection


class FakeSwiftStorage(SwiftStorage):
    def __init__(self, fail_checksum=False, connection=None, *args, **kwargs):
        super(FakeSwiftStorage, self).__init__(*args, **kwargs)
        self._retry_count = (
            kwargs.get("retry_count")
            if kwargs.get("retry_count") is not None
            else _DEFAULT_RETRY_COUNT
        )
        self._connection = connection or FakeSwift(
            fail_checksum=fail_checksum, temp_url_key=kwargs.get("temp_url_key")
        )

    def _get_connection(self):
        return self._connection


class FakeSwift(object):
    def __init__(self, fail_checksum=False, temp_url_key=None):
        self.containers = defaultdict(dict)
        self.fail_checksum = fail_checksum
        self.temp_url_key = temp_url_key

    def get_auth(self):
        if self.temp_url_key == "exception":
            raise ClientException("I failed!")

        return "http://fake/swift", None

    def head_object(self, container, path):
        return self.containers.get(container, {}).get(path, {}).get("headers", None)

    def copy_object(self, container, path, target):
        pieces = target.split("/", 2)
        _, content = self.get_object(container, path)
        self.put_object(pieces[1], pieces[2], content)

    def get_container(self, container, prefix=None, full_listing=None):
        container_entries = self.containers[container]
        objs = []
        for path, data in list(container_entries.items()):
            if not prefix or path.startswith(prefix):
                objs.append(
                    {
                        "name": path,
                        "bytes": len(data["content"]),
                        "content-type": data["content_type"],
                        "last-modified": data["upload_time"],
                    }
                )
        return {}, objs

    def put_object(
        self, container, path, content, chunk_size=None, content_type=None, headers=None
    ):
        upload_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")

        digest = None
        if not isinstance(content, bytes):
            if isinstance(content, ReadableToIterable):
                digest = content.get_md5sum()
                if isinstance(content.content, bytes):
                    content = content.content
                else:
                    content = content.content.read()
            elif issubclass(type(content), (io.IOBase, GeneratorFile, filelike.BaseStreamFilelike)):
                content = content.read()
            else:
                raise ValueError("Only bytes or file-like objects yielding bytes are valid")

        self.containers[container][path] = {
            "content": content,
            "chunk_size": chunk_size,
            "content_type": content_type,
            "upload_time": upload_time,
            "headers": headers or {"is": True},
        }

        return digest if not self.fail_checksum else "invalid"

    def get_object(self, container, path, resp_chunk_size=None):
        data = self.containers[container].get(path, {})
        if "X-Object-Manifest" in data["headers"]:
            new_contents = []
            prefix = data["headers"]["X-Object-Manifest"]
            for key, value in self.containers[container].items():
                if ("container-name/" + key).startswith(prefix):
                    new_contents.append((key, value["content"]))

            new_contents.sort(key=lambda value: value[0])

            data = dict(data)
            data["content"] = b"".join([nc[1] for nc in new_contents])
            return bool(data), data.get("content")

        return bool(data), data.get("content")

    def delete_object(self, container, path):
        self.containers[container].pop(path, None)


class FakeQueue(object):
    def __init__(self):
        self.items = []

    def get(self):
        if not self.items:
            return None

        return self.items.pop()

    def put(self, names, item, available_after=0):
        self.items.append(
            {
                "names": names,
                "item": item,
                "available_after": available_after,
            }
        )


def test_fixed_path_concat():
    swift = MockSwiftStorage(**base_args)
    swift.exists("object/path")
    swift._get_connection().head_object.assert_called_with("container-name", "basepath/object/path")


def test_simple_path_concat():
    simple_concat_args = dict(base_args)
    simple_concat_args["simple_path_concat"] = True
    swift = MockSwiftStorage(**simple_concat_args)
    swift.exists("object/path")
    swift._get_connection().head_object.assert_called_with("container-name", "basepathobject/path")


def test_delete_unknown_path():
    swift = SwiftStorage(**base_args)
    with pytest.raises(IOError):
        swift.remove("someunknownpath")


def test_simple_put_get():
    swift = FakeSwiftStorage(**base_args)
    assert not swift.exists("somepath")

    swift.put_content("somepath", b"hello world!")
    assert swift.exists("somepath")
    assert swift.get_content("somepath") == b"hello world!"

    swift.put_content("someotherpath", LimitedStream(io.BytesIO(b"hello world2"), 12))
    assert swift.exists("someotherpath")
    assert swift.get_content("someotherpath") == b"hello world2"

    swift.put_content("yetsomeotherpath", ReadableToIterable(b"hello world3"))
    assert swift.exists("yetsomeotherpath")
    assert swift.get_content("yetsomeotherpath") == b"hello world3"

    swift.put_content("againsomeotherpath", io.BytesIO(b"hello world4"))
    assert swift.exists("againsomeotherpath")
    assert swift.get_content("againsomeotherpath") == b"hello world4"


def test_put_content_then_list_all():
    """
    Verifies that we can list all content under a specific path.
    """
    swift = FakeSwiftStorage(**base_args)
    assert not swift.exists("somepath")
    now = datetime.datetime.now(datetime.timezone.utc)

    # upload 5 random files
    for i in range(5):
        payload = os.urandom(1024)
        with freeze_time(now):
            upload_path = f"somepath/file-{i}.bin"
            swift.put_content(upload_path, payload)
            assert swift.exists(upload_path)

    # fetch all content
    obj = swift._list_content("somepath")
    assert obj
    assert len(obj) == 5


def test_stream_read_write():
    swift = FakeSwiftStorage(**base_args)
    assert not swift.exists("somepath")

    swift.stream_write("somepath", io.BytesIO(b"some content here"))
    assert swift.exists("somepath")
    assert swift.get_content("somepath") == b"some content here"
    assert b"".join([c for c in swift.stream_read("somepath")]) == b"some content here"


def test_stream_read_write_invalid_checksum():
    swift = FakeSwiftStorage(fail_checksum=True, **base_args)
    assert not swift.exists("somepath")

    with pytest.raises(IOError):
        swift.stream_write("somepath", io.BytesIO(b"some content here"))


def test_remove():
    swift = FakeSwiftStorage(**base_args)
    assert not swift.exists("somepath")

    swift.put_content("somepath", b"hello world!")
    assert swift.exists("somepath")

    swift.remove("somepath")
    assert not swift.exists("somepath")


def test_copy_to():
    swift = FakeSwiftStorage(**base_args)

    modified_args = copy.deepcopy(base_args)
    modified_args["swift_container"] = "another_container"

    another_swift = FakeSwiftStorage(connection=swift._connection, **modified_args)

    swift.put_content("somepath", b"some content here")
    swift.copy_to(another_swift, "somepath")

    assert swift.exists("somepath")
    assert another_swift.exists("somepath")

    assert swift.get_content("somepath") == b"some content here"
    assert another_swift.get_content("somepath") == b"some content here"


def test_copy_to_different():
    swift = FakeSwiftStorage(**base_args)

    modified_args = copy.deepcopy(base_args)
    modified_args["swift_user"] = "foobarbaz"
    modified_args["swift_container"] = "another_container"

    another_swift = FakeSwiftStorage(**modified_args)

    swift.put_content("somepath", b"some content here")
    swift.copy_to(another_swift, "somepath")

    assert swift.exists("somepath")
    assert another_swift.exists("somepath")

    assert swift.get_content("somepath") == b"some content here"
    assert another_swift.get_content("somepath") == b"some content here"


def test_checksum():
    swift = FakeSwiftStorage(**base_args)
    swift.put_content("somepath", b"hello world!")
    assert swift.get_checksum("somepath") is not None


@pytest.mark.parametrize(
    "read_until_end",
    [
        (True),
        (False),
    ],
)
@pytest.mark.parametrize(
    "max_chunk_size",
    [
        (10000000),
        (10),
        (5),
        (2),
        (1),
    ],
)
@pytest.mark.parametrize(
    "chunks",
    [
        ([b"this", b"is", b"some", b"chunked", b"data", b""]),
        ([b"this is a very large chunk of data", b""]),
        ([b"h", b"e", b"l", b"l", b"o", b""]),
    ],
)
@pytest.mark.parametrize(
    "retry_count",
    [
        (0),
        (5),
    ],
)
def test_chunked_upload(chunks, max_chunk_size, read_until_end, retry_count):
    swift = FakeSwiftStorage(**base_args, retry_count=retry_count)
    uuid, metadata = swift.initiate_chunked_upload()

    offset = 0
    with patch("storage.swift._MAXIMUM_SEGMENT_SIZE", max_chunk_size):
        for chunk in chunks:
            chunk_length = len(chunk) if not read_until_end else -1
            bytes_written, metadata, error = swift.stream_upload_chunk(
                uuid, offset, chunk_length, io.BytesIO(chunk), metadata
            )
            assert error is None
            assert len(chunk) == bytes_written
            offset += len(chunk)

        swift.complete_chunked_upload(uuid, "somepath", metadata)
        assert swift.get_content("somepath") == b"".join(chunks)

        # Ensure each of the segments exist.
        for segment in metadata["segments"]:
            assert swift.exists(segment.path)

        # Delete the file and ensure all of its segments were removed.
        swift.remove("somepath")
        assert not swift.exists("somepath")

        for segment in metadata["segments"]:
            assert not swift.exists(segment.path)


def test_cancel_chunked_upload():
    chunk_cleanup_queue = FakeQueue()

    args = dict(base_args)
    args["context"] = StorageContext("nyc", chunk_cleanup_queue, None, None)

    swift = FakeSwiftStorage(**args)
    uuid, metadata = swift.initiate_chunked_upload()

    chunks = [b"this", b"is", b"some", b"chunked", b"data", b""]
    offset = 0
    for chunk in chunks:
        bytes_written, metadata, error = swift.stream_upload_chunk(
            uuid, offset, len(chunk), io.BytesIO(chunk), metadata
        )
        assert error is None
        assert len(chunk) == bytes_written
        offset += len(chunk)

    swift.cancel_chunked_upload(uuid, metadata)

    found = chunk_cleanup_queue.get()
    assert found is not None


def test_empty_chunks_queued_for_deletion():
    chunk_cleanup_queue = FakeQueue()
    args = dict(base_args)
    args["context"] = StorageContext("nyc", chunk_cleanup_queue, None, None)

    swift = FakeSwiftStorage(**args)
    uuid, metadata = swift.initiate_chunked_upload()

    chunks = [b"this", b"", b"is", b"some", b"", b"chunked", b"data", b""]
    offset = 0
    for chunk in chunks:
        length = len(chunk)
        if length == 0:
            length = 1

        bytes_written, metadata, error = swift.stream_upload_chunk(
            uuid, offset, length, io.BytesIO(chunk), metadata
        )
        assert error is None
        assert len(chunk) == bytes_written
        offset += len(chunk)

    swift.complete_chunked_upload(uuid, "somepath", metadata)
    assert b"".join(chunks) == swift.get_content("somepath")

    # Check the chunk deletion queue and ensure we have the last chunk queued.
    found = chunk_cleanup_queue.get()
    assert found is not None

    found2 = chunk_cleanup_queue.get()
    assert found2 is None


@pytest.mark.parametrize(
    "temp_url_key, expects_url",
    [
        (None, False),
        ("foobarbaz", True),
        ("exception", False),
    ],
)
def test_get_direct_download_url(temp_url_key, expects_url):
    swift = FakeSwiftStorage(temp_url_key=temp_url_key, **base_args)
    swift.put_content("somepath", b"hello world!")
    assert (swift.get_direct_download_url("somepath") is not None) == expects_url


def test_cleanup_of_orphaned_export_log_files_successful():
    """
    Verifies that the worker can clean up orphaned exported log files.
    """
    storage_engine = FakeSwiftStorage(**base_args)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = ""

    payload = b'{"logs": []}'
    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key = f"{_TEST_LOG_PATH}{logfile}"

    # put blob into the container
    with freeze_time(now):
        storage_engine.put_content(upload_key, payload)

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all container content on that specific path to ensure that the file was removed
    remaining_keys = list(storage_engine._list_content(_TEST_LOG_PATH))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 0


def test_export_log_cleanup_does_not_touch_user_files():
    """
    Verifies that other files in the same path are not picked up by the
    cleanup worker.
    """
    storage_engine = FakeSwiftStorage(**base_args)
    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = ""

    payload1 = b'{"logs": []}'
    payload2 = b"Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"{_TEST_LOG_PATH}{userfile}"

    # put both blobs in the container
    with freeze_time(now):
        storage_engine.put_content(upload_key_logfile, payload1)
        storage_engine.put_content(upload_key_userfile, payload2)

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all content under the specified prefix
    remaining_keys = list(storage_engine._list_content(_TEST_LOG_PATH))
    logging.debug(remaining_keys)

    assert len(remaining_keys) == 1
    assert remaining_keys[0]["name"] == upload_key_userfile


def test_export_log_cleanup_doesnt_touch_other_paths():
    """
    Verifies that all other paths other than the log path are untouched by the
    cleanup worker.
    """
    storage_engine = FakeSwiftStorage(**base_args)

    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = ""

    payload1 = b'{"logs": []}'
    payload2 = b"Hello world!!!"

    logfile = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    upload_key_logfile = f"{_TEST_LOG_PATH}{logfile}"
    userfile = "hello.txt"
    upload_key_userfile = f"different/path/altogether/{userfile}"

    # put both blobs in the container
    with freeze_time(now):
        storage_engine.put_content(upload_key_logfile, payload1)
        storage_engine.put_content(upload_key_userfile, payload2)

    # attempt to clean
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(seconds=0), _TEST_LOG_PATH)

    # list all content in the container
    remaining_keys = list(storage_engine._list_content("/"))
    logging.debug(remaining_keys)

    assert len(remaining_keys) == 1
    assert remaining_keys[0]["name"] == upload_key_userfile


def test_export_log_cleanup_doesnt_pick_up_files_that_are_inside_the_timedelta():
    """
    Verifies that we only delete files that are older than 1 hour and not any other files that are in the same path
    """
    storage_engine = FakeSwiftStorage(**base_args)

    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = ""

    # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now + timedelta(hours=i)):
            storage_engine.put_content(path=k, content=payload)

    # list all content on that specific path and confirm that there are 5 blobs present
    remaining_keys = list(storage_engine._list_content(path=_TEST_LOG_PATH))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 5

    # add 6th file only 30 minutes *after* the last file was uploaded
    final_key = f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    payload = os.urandom(1024)
    with freeze_time(now + timedelta(hours=5.5)):
        storage_engine.put_content(path=final_key, content=payload)

    # at 6th hour do cleanup
    with freeze_time(
        now + timedelta(hours=6)
    ):  # Changed from 5 to 6 so it occurs after the 5.5h upload
        storage_engine.clean_exported_action_logs(timedelta(hours=1), _TEST_LOG_PATH)

    # only one file should remain
    remaining_keys = list(storage_engine._list_content(path=_TEST_LOG_PATH))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 1
    assert remaining_keys[0]["name"] == final_key


def test_export_log_cleanup_correctly_identifies_storage_path():
    """
    Verifies that the root path (defined through storage_path in the driver) is
    properly taken into account during wiping.
    """

    storage_engine = FakeSwiftStorage(**base_args)

    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = "datastorage/registry"

    # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now):
            storage_engine.put_content(path=k, content=payload)

    # add a specific file with a SHA digest to mimick real storage
    payload = os.urandom(1024)
    filename = hashlib.sha256(payload).hexdigest()
    final_key = f"sha256/{filename[:2]}/{filename}"

    # upload the final key
    with freeze_time(now):
        storage_engine.put_content(path=final_key, content=payload)

    # verify all blobs are uploaded properly and are visible
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 6

    # attempt to clean up expired logs
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # only one file should remain
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 1
    assert remaining_keys[0]["name"].endswith(final_key)


def test_export_log_cleanup_does_not_return_error_on_empty_directory():
    """
    Verifies that cleanup does not error when nothing is cleaned. Simple regression test.
    """
    storage_engine = FakeSwiftStorage(**base_args)

    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = "datastorage/registry"

    # add a specific file with a SHA digest to mimick real storage
    payload = os.urandom(1024)
    filename = hashlib.sha256(payload).hexdigest()
    keyname = f"sha256/{filename[:2]}/{filename}"

    # upload the key
    with freeze_time(now):
        storage_engine.put_content(path=keyname, content=payload)

    # assert that we only have one key under datastorage/registry path
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 1

    # call cleanup on real directory
    with freeze_time(now + timedelta(hours=2)):
        storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # assert that we still have only one file under storage path
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 1


def test_cleanup_of_expired_logs_gracefully_handles_errors():
    """
    Asserts that the ClientException is caught by the code and not raised.
    """
    storage_engine = FakeSwiftStorage(**base_args)
    err = IOError("Simulated deletion error")

    now = datetime.datetime.now(datetime.timezone.utc)
    storage_engine._storage_path = "datastorage/registry"

    # create a list of files
    keys = [f"{_TEST_LOG_PATH}{str(uuid.uuid4())}-{str(uuid.uuid4())}" for i in range(5)]
    for i, k in enumerate(keys):
        payload = os.urandom(1024)
        with freeze_time(now):
            storage_engine.put_content(path=k, content=payload)

    # verify we have content under the path
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 5

    orig_delete = FakeSwift.delete_object

    def mock_delete(self, container, path):
        if path.endswith(keys[2]):
            raise ClientException("Simulated deletion error")
        return orig_delete(self, container, path)

    with patch.object(FakeSwift, "delete_object", new=mock_delete):
        # attempt to delete all logs
        with freeze_time(now + timedelta(hours=2)):
            storage_engine.clean_exported_action_logs(timedelta(hours=0), _TEST_LOG_PATH)

    # list all files in the directory, there should be one
    remaining_keys = list(storage_engine._list_content(""))
    logging.debug(remaining_keys)
    assert len(remaining_keys) == 1
    assert remaining_keys[0]["name"].endswith(keys[2])
