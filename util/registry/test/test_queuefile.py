import os

import pytest

from util.registry.queueprocess import QueueResult
from util.registry.queuefile import QueueFile


class FakeQueue(object):
    def __init__(self):
        self.items = []

    def get(self, block, timeout=None):
        return self.items.pop(0)

    def put(self, data):
        self.items.append(data)


def test_basic():
    queue = FakeQueue()
    queue.put(QueueResult(b"hello world", None))
    queue.put(QueueResult(b"! how goes there?", None))
    queue.put(QueueResult(None, None))

    queuefile = QueueFile(queue)
    assert queuefile.read() == b"hello world! how goes there?"


def test_chunk_reading():
    queue = FakeQueue()
    queue.put(QueueResult(b"hello world", None))
    queue.put(QueueResult(b"! how goes there?", None))
    queue.put(QueueResult(None, None))

    queuefile = QueueFile(queue)
    data = b""

    while True:
        result = queuefile.read(size=2)
        if not result:
            break

        data += result

    assert data == b"hello world! how goes there?"


def test_unhandled_exception():
    queue = FakeQueue()
    queue.put(QueueResult(b"hello world", None))
    queue.put(QueueResult(None, IOError("some exception")))
    queue.put(QueueResult(b"! how goes there?", None))
    queue.put(QueueResult(None, None))

    queuefile = QueueFile(queue)

    with pytest.raises(IOError):
        queuefile.read(size=12)


def test_handled_exception():
    queue = FakeQueue()
    queue.put(QueueResult(b"hello world", None))
    queue.put(QueueResult(None, IOError("some exception")))
    queue.put(QueueResult(b"! how goes there?", None))
    queue.put(QueueResult(None, None))

    ex_found = [None]

    def handler(ex):
        ex_found[0] = ex

    queuefile = QueueFile(queue)
    queuefile.add_exception_handler(handler)
    queuefile.read(size=12)

    assert ex_found[0] is not None


def test_binary_data():
    queue = FakeQueue()

    # Generate some binary data.
    binary_data = os.urandom(1024)
    queue.put(QueueResult(binary_data, None))
    queue.put(QueueResult(None, None))

    queuefile = QueueFile(queue)
    found_data = b""
    while True:
        current_data = queuefile.read(size=37)
        if len(current_data) == 0:
            break

        found_data = found_data + current_data

    assert found_data == binary_data


def test_empty_data():
    queue = FakeQueue()

    # Generate some empty binary data.
    binary_data = b"\0" * 1024
    queue.put(QueueResult(binary_data, None))
    queue.put(QueueResult(None, None))

    queuefile = QueueFile(queue)
    found_data = b""
    while True:
        current_data = queuefile.read(size=37)
        if len(current_data) == 0:
            break

        found_data = found_data + current_data

    assert found_data == binary_data
