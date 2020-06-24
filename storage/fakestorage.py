from typing import DefaultDict, Any
from io import BytesIO
import hashlib

from collections import defaultdict
from uuid import uuid4

from storage.basestorage import BaseStorageV2

_GLOBAL_FAKE_STORAGE_MAP = defaultdict(BytesIO)  # type: DefaultDict[Any, BytesIO]


class FakeStorage(BaseStorageV2):
    def __init__(self, context):
        super(FakeStorage, self).__init__()
        self._fake_storage_map = (
            defaultdict(BytesIO) if context == "local" else _GLOBAL_FAKE_STORAGE_MAP
        )

    def _init_path(self, path=None, create=False):
        return path

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False
    ):
        try:
            if self.get_content("supports_direct_download") == b"true":
                return "http://somefakeurl?goes=here"
        except:
            pass

        return None

    def get_content(self, path):
        if not path in self._fake_storage_map:
            raise IOError(
                "Fake file %s not found. Exist: %s" % (path, list(self._fake_storage_map.keys()))
            )

        self._fake_storage_map.get(path).seek(0)
        return self._fake_storage_map.get(path).read()

    def put_content(self, path, content):
        self._fake_storage_map.pop(path, None)
        self._fake_storage_map[path].write(content)

    def stream_read(self, path):
        io_obj = self._fake_storage_map[path]
        io_obj.seek(0)
        while True:
            buf = io_obj.read(self.buffer_size)
            if not buf:
                break
            yield buf

    def stream_read_file(self, path):
        return BytesIO(self.get_content(path))

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        out_fp = self._fake_storage_map[path]
        out_fp.seek(0)
        self.stream_write_to_fp(fp, out_fp)

    def remove(self, path):
        self._fake_storage_map.pop(path, None)

    def exists(self, path):
        if self._fake_storage_map.get("all_files_exist", None):
            return True
        return path in self._fake_storage_map

    def get_checksum(self, path):
        return hashlib.sha256(self._fake_storage_map[path].read()).hexdigest()[:7]

    def initiate_chunked_upload(self):
        new_uuid = str(uuid4())
        self._fake_storage_map[new_uuid].seek(0)
        return new_uuid, {}

    def stream_upload_chunk(self, uuid, offset, length, in_fp, _, content_type=None):
        if self.exists("except_upload"):
            return 0, {}, IOError("I'm an exception!")

        upload_storage = self._fake_storage_map[uuid]
        try:
            return self.stream_write_to_fp(in_fp, upload_storage, length), {}, None
        except IOError as ex:
            return 0, {}, ex

    def complete_chunked_upload(self, uuid, final_path, _):
        self._fake_storage_map[final_path] = self._fake_storage_map[uuid]
        self._fake_storage_map.pop(uuid, None)

    def cancel_chunked_upload(self, uuid, _):
        self._fake_storage_map.pop(uuid, None)

    def copy_to(self, destination, path):
        if self.exists("break_copying"):
            raise IOError("Broken!")

        if self.exists("fake_copying"):
            return

        if self.exists("except_copying"):
            raise Exception("I'm an exception!")

        content = self.get_content(path)
        destination.put_content(path, content)
