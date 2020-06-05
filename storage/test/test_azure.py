import base64
from hashlib import md5
import pytest
import io

from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse
from httmock import urlmatch, HTTMock
from xml.dom import minidom

from azure.storage.blob import BlockBlobService

from storage.azurestorage import AzureStorage


@contextmanager
def fake_azure_storage(files=None):
    service = BlockBlobService(is_emulated=True)
    endpoint = service.primary_endpoint.split("/")
    container_name = "somecontainer"
    files = files if files is not None else {}

    container_prefix = "/" + endpoint[1] + "/" + container_name

    @urlmatch(netloc=endpoint[0], path=container_prefix + "$")
    def get_container(url, request):
        return {"status_code": 200, "content": "{}"}

    @urlmatch(netloc=endpoint[0], path=container_prefix + "/.+")
    def container_file(url, request):
        filename = url.path[len(container_prefix) + 1 :]

        if request.method == "GET" or request.method == "HEAD":
            return {
                "status_code": 200 if filename in files else 404,
                "content": files.get(filename),
                "headers": {"ETag": "foobar",},
            }

        if request.method == "DELETE":
            files.pop(filename)
            return {
                "status_code": 201,
                "content": "",
                "headers": {"ETag": "foobar",},
            }

        if request.method == "PUT":
            query_params = parse_qs(url.query)
            if query_params.get("comp") == ["properties"]:
                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "x-ms-request-server-encrypted": "false",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    },
                }

            if query_params.get("comp") == ["block"]:
                block_id = query_params["blockid"][0]
                files[filename] = files.get(filename) or {}
                files[filename][block_id] = request.body
                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "Content-MD5": base64.b64encode(md5(request.body).digest()),
                        "ETag": "foo",
                        "x-ms-request-server-encrypted": "false",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    },
                }

            if query_params.get("comp") == ["blocklist"]:
                parsed = minidom.parseString(request.body)
                latest = parsed.getElementsByTagName("Latest")
                combined = []
                for latest_block in latest:
                    combined.append(files[filename][latest_block.childNodes[0].data])

                files[filename] = b"".join(combined)
                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "Content-MD5": base64.b64encode(md5(files[filename]).digest()),
                        "ETag": "foo",
                        "x-ms-request-server-encrypted": "false",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    },
                }

            if request.headers.get("x-ms-copy-source"):
                copy_source = request.headers["x-ms-copy-source"]
                copy_path = urlparse(copy_source).path[len(container_prefix) + 1 :]
                files[filename] = files[copy_path]
                return {
                    "status_code": 201,
                    "content": "{}",
                    "headers": {
                        "x-ms-request-server-encrypted": "false",
                        "x-ms-copy-status": "success",
                        "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                    },
                }

            files[filename] = request.body

            return {
                "status_code": 201,
                "content": "{}",
                "headers": {
                    "Content-MD5": base64.b64encode(md5(request.body).digest()),
                    "ETag": "foo",
                    "x-ms-request-server-encrypted": "false",
                    "last-modified": "Wed, 21 Oct 2015 07:28:00 GMT",
                },
            }

        return {"status_code": 405, "content": ""}

    @urlmatch(netloc=endpoint[0], path=".+")
    def catchall(url, request):
        return {"status_code": 405, "content": ""}

    with HTTMock(get_container, container_file, catchall):
        yield AzureStorage(None, "somecontainer", "", "someaccount", is_emulated=True)


def test_validate():
    with fake_azure_storage() as s:
        s.validate(None)


def test_basics():
    with fake_azure_storage() as s:
        s.put_content("hello", b"hello world")
        assert s.exists("hello")
        assert s.get_content("hello") == b"hello world"
        assert s.get_checksum("hello")
        assert b"".join(list(s.stream_read("hello"))) == b"hello world"
        assert s.stream_read_file("hello").read() == b"hello world"

        s.remove("hello")
        assert not s.exists("hello")


def test_does_not_exist():
    with fake_azure_storage() as s:
        assert not s.exists("hello")

        with pytest.raises(IOError):
            s.get_content("hello")

        with pytest.raises(IOError):
            s.get_checksum("hello")

        with pytest.raises(IOError):
            list(s.stream_read("hello"))

        with pytest.raises(IOError):
            s.stream_read_file("hello")


def test_stream_write():
    fp = io.BytesIO()
    fp.write(b"hello world!")
    fp.seek(0)

    with fake_azure_storage() as s:
        s.stream_write("hello", fp)

        assert s.get_content("hello") == b"hello world!"


@pytest.mark.parametrize("chunk_size", [(1), (5), (10),])
def test_chunked_uploading(chunk_size):
    with fake_azure_storage() as s:
        string_data = b"hello world!"
        chunks = [
            string_data[index : index + chunk_size]
            for index in range(0, len(string_data), chunk_size)
        ]

        uuid, metadata = s.initiate_chunked_upload()
        start_index = 0

        for chunk in chunks:
            fp = io.BytesIO()
            fp.write(chunk)
            fp.seek(0)

            total_bytes_written, metadata, error = s.stream_upload_chunk(
                uuid, start_index, -1, fp, metadata
            )
            assert total_bytes_written == len(chunk)
            assert metadata
            assert not error

            start_index += total_bytes_written

        s.complete_chunked_upload(uuid, "chunked", metadata)
        assert s.get_content("chunked") == string_data


def test_get_direct_download_url():
    with fake_azure_storage() as s:
        s.put_content("hello", b"world")
        assert "sig" in s.get_direct_download_url("hello")


def test_copy_to():
    files = {}

    with fake_azure_storage(files=files) as s:
        s.put_content("hello", b"hello world")
        with fake_azure_storage(files=files) as s2:
            s.copy_to(s2, "hello")
            assert s2.exists("hello")
