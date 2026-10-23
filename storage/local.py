import hashlib
import io
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psutil

from storage.basestorage import _EXPORTED_LOG_FILENAME_RE, BaseStorageV2

logger = logging.getLogger(__name__)


class LocalStorage(BaseStorageV2):
    def __init__(self, context, storage_path):
        super(LocalStorage, self).__init__()
        self._root_path = storage_path

    def _init_path(self, path=None, create=False):
        path = os.path.join(self._root_path, path) if path else self._root_path
        if create is True:
            dirname = os.path.dirname(path)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return path

    def get_content(self, path):
        path = self._init_path(path)
        with open(path, mode="rb") as f:
            return f.read()

    def list_directory(self, path):
        """
        Lists the content of the directory
        """
        path = self._init_path(path, create=False)
        if not os.path.exists(path):
            return []

        files = []
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if not os.path.isfile(full_path):
                continue
            try:
                mtime = os.path.getmtime(full_path)
                files.append(
                    {
                        "filename": full_path,
                        "mtime": mtime,
                    }
                )
            except OSError as e:
                logger.debug("Could not stat file %s: %s", full_path, e)
        return files

    def put_content(self, path, content):
        path = self._init_path(path, create=True)
        with open(path, mode="wb") as f:
            f.write(content)
        return path

    def stream_read(self, path):
        path = self._init_path(path)
        with open(path, mode="rb") as f:
            while True:
                buf = f.read(self.buffer_size)
                if not buf:
                    break
                yield buf

    def stream_read_file(self, path):
        path = self._init_path(path)
        return io.open(path, mode="rb")

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        # Size is mandatory
        path = self._init_path(path, create=True)
        with open(path, mode="wb") as out_fp:
            self.stream_write_to_fp(fp, out_fp)

    def exists(self, path):
        path = self._init_path(path)
        return os.path.exists(path)

    def remove(self, path):
        path = self._init_path(path)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return
        try:
            os.remove(path)
        except OSError:
            pass

    def get_checksum(self, path):
        path = self._init_path(path)
        sha_hash = hashlib.sha256()
        with open(path, "rb") as to_hash:
            while True:
                buf = to_hash.read(self.buffer_size)
                if not buf:
                    break
                sha_hash.update(buf)
        return sha_hash.hexdigest()[:7]

    def _rel_upload_path(self, uuid):
        return "uploads/{0}".format(uuid)

    def initiate_chunked_upload(self):
        new_uuid = str(uuid4())

        # Just create an empty file at the path
        with open(self._init_path(self._rel_upload_path(new_uuid), create=True), "wb"):
            pass

        return new_uuid, {}

    def stream_upload_chunk(self, uuid, offset, length, in_fp, _, content_type=None):
        try:
            with open(self._init_path(self._rel_upload_path(uuid)), "r+b") as upload_storage:
                # Seek to end rather than to offset: cloud backends store each chunk in a
                # separate object (offset is always 0 within each chunk), so all callers
                # that do sequential appending pass offset=0. For blob uploads (blobuploader.py)
                # offset is validated to equal the current file size before this call, making
                # seek-to-end equivalent to seek(offset).
                upload_storage.seek(0, 2)
                return self.stream_write_to_fp(in_fp, upload_storage, length), {}, None
        except IOError as ex:
            return 0, {}, ex

    def complete_chunked_upload(self, uuid, final_path, _):
        content_path = self._rel_upload_path(uuid)
        final_path_abs = self._init_path(final_path, create=True)
        if not self.exists(final_path_abs):
            logger.debug("Moving content into place at path: %s", final_path_abs)
            shutil.move(self._init_path(content_path), final_path_abs)
        else:
            logger.debug("Content already exists at path: %s", final_path_abs)

    def cancel_chunked_upload(self, uuid, _):
        content_path = self._init_path(self._rel_upload_path(uuid))
        os.remove(content_path)

    def validate(self, client):
        super(LocalStorage, self).validate(client)

        # Load the set of disk mounts.
        try:
            mounts = psutil.disk_partitions(all=True)
        except:
            logger.exception("Could not load disk partitions")
            return

        # Verify that the storage's root path is under a mounted Docker volume.
        for mount in mounts:
            if mount.mountpoint != "/" and self._root_path.startswith(mount.mountpoint):
                return

        raise Exception(
            "Storage path %s is not under a mounted volume.\n\n"
            "Registry data must be stored under a mounted volume "
            "to prevent data loss" % self._root_path
        )

    def copy_to(self, destination, path):
        with self.stream_read_file(path) as fp:
            destination.stream_write(path, fp)

    def clean_exported_action_logs(self, deletion_date_threshold, log_path):
        """
        Lists and deletes all exported log files which are older than the
        defined threshold (defaults to 1 hour).
        """
        cutoff = datetime.now(timezone.utc) - deletion_date_threshold
        obj_list = self.list_directory(log_path)

        for obj in obj_list:
            f = obj["filename"].split("/")[-1]
            if datetime.fromtimestamp(
                obj["mtime"], tz=timezone.utc
            ) <= cutoff and _EXPORTED_LOG_FILENAME_RE.fullmatch(f):
                try:
                    os.remove(obj["filename"])
                    logger.debug(
                        "Expired exported log deleted from %s: %s", log_path, obj["filename"]
                    )
                except OSError as e:
                    logger.exception("Could not delete file %s: %s", obj["filename"], e)
