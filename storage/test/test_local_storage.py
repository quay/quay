import hashlib
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

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
