import unittest
import json
import time

from functools import wraps
from threading import Thread, Lock

from app import app
from data.queue import WorkQueue
from initdb import wipe_database, initialize_database, populate_database


QUEUE_NAME = "testqueuename"


class AutoUpdatingQueue(object):
    def __init__(self, queue_to_wrap):
        self._queue = queue_to_wrap

    def _wrapper(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            to_return = func(*args, **kwargs)
            self._queue.update_metrics()
            return to_return

        return wrapper

    def __getattr__(self, attr_name):
        method_or_attr = getattr(self._queue, attr_name)
        if callable(method_or_attr):
            return self._wrapper(method_or_attr)
        else:
            return method_or_attr


class QueueTestCase(unittest.TestCase):
    TEST_MESSAGE_1 = json.dumps({"data": 1})

    def setUp(self):
        self.transaction_factory = app.config["DB_TRANSACTION_FACTORY"]
        self.queue = AutoUpdatingQueue(WorkQueue(QUEUE_NAME, self.transaction_factory))
        wipe_database()
        initialize_database()
        populate_database()


class TestQueueThreads(QueueTestCase):
    def test_queue_threads(self):
        count = [20]
        for i in range(count[0]):
            self.queue.put([str(i)], self.TEST_MESSAGE_1)

        lock = Lock()

        def get(lock, count, queue):
            item = queue.get()
            if item is None:
                return
            self.assertEqual(self.TEST_MESSAGE_1, item.body)
            with lock:
                count[0] -= 1

        threads = []
        # The thread count needs to be a few times higher than the queue size
        # count because some threads will get a None and thus won't decrement
        # the counter.
        for i in range(100):
            t = Thread(target=get, args=(lock, count, self.queue))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(count[0], 0)


if __name__ == "__main__":
    unittest.main()
