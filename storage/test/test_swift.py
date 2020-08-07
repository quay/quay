import _pyio as io
import pytest
import hashlib
import copy

from collections import defaultdict
from mock import MagicMock, patch

from swiftclient.client import ClientException, ReadableToIterable

from storage import StorageContext
from storage.swift import SwiftStorage, _EMPTY_SEGMENTS_KEY, _DEFAULT_RETRY_COUNT

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
        self._retry_count = kwargs.get("retry_count") or _DEFAULT_RETRY_COUNT
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
                    {"name": path, "bytes": len(data["content"]),}
                )
        return {}, objs

    def put_object(
        self, container, path, content, chunk_size=None, content_type=None, headers=None
    ):
        digest = None
        if not isinstance(content, bytes):
            if isinstance(content, ReadableToIterable):
                digest = content.get_md5sum()
                if isinstance(content.content, bytes):
                    content = content.content
                else:
                    content = content.content.read()
            else:
                raise ValueError("Only bytes or file-like objects yielding bytes are valid")

        self.containers[container][path] = {
            "content": content,
            "chunk_size": chunk_size,
            "content_type": content_type,
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
            {"names": names, "item": item, "available_after": available_after,}
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


@pytest.mark.parametrize("read_until_end", [(True,), (False,),])
@pytest.mark.parametrize("max_chunk_size", [(10000000), (10), (5), (2), (1),])
@pytest.mark.parametrize(
    "chunks",
    [
        ([b"this", b"is", b"some", b"chunked", b"data", b""]),
        ([b"this is a very large chunk of data", b""]),
        ([b"h", b"e", b"l", b"l", b"o", b""]),
    ],
)
def test_chunked_upload(chunks, max_chunk_size, read_until_end):
    swift = FakeSwiftStorage(**base_args)
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
    "temp_url_key, expects_url", [(None, False), ("foobarbaz", True), ("exception", False),]
)
def test_get_direct_download_url(temp_url_key, expects_url):
    swift = FakeSwiftStorage(temp_url_key=temp_url_key, **base_args)
    swift.put_content("somepath", b"hello world!")
    assert (swift.get_direct_download_url("somepath") is not None) == expects_url
