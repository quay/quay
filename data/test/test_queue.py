import json
import time

import pytest

from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps

from data.database import QueueItem
from data.queue import (
    WorkQueue,
    MINIMUM_EXTENSION,
    queue_items_locked,
    queue_items_available,
    queue_items_available_unlocked,
)

from test.fixtures import *


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


TEST_MESSAGE_1 = json.dumps({"data": 1})
TEST_MESSAGE_2 = json.dumps({"data": 2})
TEST_MESSAGES = [json.dumps({"data": str(i)}) for i in range(1, 101)]


@contextmanager
def fake_transaction(arg):
    yield


@pytest.fixture()
def transaction_factory():
    return fake_transaction


def gauge_value(g):
    return g.collect()[0].samples[0].value


@pytest.fixture()
def queue(transaction_factory, initialized_db):
    return AutoUpdatingQueue(WorkQueue(QUEUE_NAME, transaction_factory))


def test_get_single_item(queue, transaction_factory):
    # Add a single item to the queue.
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)

    # Have two "instances" retrieve an item to claim. Since there is only one, both calls should
    # return the same item.
    now = datetime.utcnow()
    first_item = queue._select_available_item(False, now)
    second_item = queue._select_available_item(False, now)

    assert first_item.id == second_item.id
    assert first_item.state_id == second_item.state_id

    # Have both "instances" now try to claim the item. Only one should succeed.
    first_claimed = queue._attempt_to_claim_item(first_item, now, 300)
    second_claimed = queue._attempt_to_claim_item(first_item, now, 300)

    assert first_claimed
    assert not second_claimed

    # Ensure the item is no longer available.
    assert queue.get() is None

    # Ensure the item's state ID has changed.
    assert first_item.state_id != QueueItem.get().state_id


def test_extend_processing(queue, transaction_factory):
    # Add and retrieve a queue item.
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    queue_item = queue.get(processing_time=10)
    assert queue_item is not None

    existing_db_item = QueueItem.get(id=queue_item.id)

    # Call extend processing with a timedelta less than the minimum and ensure its
    # processing_expires and state_id do not change.
    changed = queue.extend_processing(queue_item, 10 + MINIMUM_EXTENSION.total_seconds() - 1)
    assert not changed

    updated_db_item = QueueItem.get(id=queue_item.id)

    assert existing_db_item.processing_expires == updated_db_item.processing_expires
    assert existing_db_item.state_id == updated_db_item.state_id

    # Call extend processing with a timedelta greater than the minimum and ensure its
    # processing_expires and state_id are changed.
    changed = queue.extend_processing(queue_item, 10 + MINIMUM_EXTENSION.total_seconds() + 1)
    assert changed

    updated_db_item = QueueItem.get(id=queue_item.id)

    assert existing_db_item.processing_expires != updated_db_item.processing_expires
    assert existing_db_item.state_id != updated_db_item.state_id

    # Call extend processing with a timedelta less than the minimum but also with new data and
    # ensure its processing_expires and state_id are changed.
    changed = queue.extend_processing(
        queue_item, 10 + MINIMUM_EXTENSION.total_seconds() - 1, updated_data="newbody"
    )
    assert changed

    updated_db_item = QueueItem.get(id=queue_item.id)

    assert existing_db_item.processing_expires != updated_db_item.processing_expires
    assert existing_db_item.state_id != updated_db_item.state_id
    assert updated_db_item.body == "newbody"


def test_same_canonical_names(queue, transaction_factory):
    queue_items_locked.labels(queue._queue_name).set(0)
    queue_items_available.labels(queue._queue_name).set(0)
    queue_items_available_unlocked.labels(queue._queue_name).set(0)

    id_1 = int(queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1))
    id_2 = int(queue.put(["abc", "def"], TEST_MESSAGE_2, available_after=-1))
    assert id_1 + 1 == id_2
    assert not queue._currently_processing
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    one = queue.get(ordering_required=True)
    assert one is not None
    assert one.body == TEST_MESSAGE_1
    assert queue._currently_processing
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    two_fail = queue.get(ordering_required=True)
    assert two_fail is None
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    queue.complete(one)
    assert not queue._currently_processing
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    two = queue.get(ordering_required=True)
    assert two is not None
    assert queue._currently_processing
    assert two.body == TEST_MESSAGE_2
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1


def test_different_canonical_names(queue, transaction_factory):
    queue_items_locked.labels(queue._queue_name).set(0)
    queue_items_available.labels(queue._queue_name).set(0)
    queue_items_available_unlocked.labels(queue._queue_name).set(0)

    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    queue.put(["abc", "ghi"], TEST_MESSAGE_2, available_after=-1)

    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 2

    one = queue.get(ordering_required=True)
    assert one is not None
    assert one.body == TEST_MESSAGE_1
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 2

    two = queue.get(ordering_required=True)
    assert two is not None
    assert two.body == TEST_MESSAGE_2
    assert gauge_value(queue_items_locked) == 2
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 2


def test_canonical_name(queue, transaction_factory):
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    queue.put(["abc", "def", "ghi"], TEST_MESSAGE_1, available_after=-1)

    one = queue.get(ordering_required=True)
    assert QUEUE_NAME + "/abc/def/" != one

    two = queue.get(ordering_required=True)
    assert QUEUE_NAME + "/abc/def/ghi/" != two


def test_expiration(queue, transaction_factory):
    queue_items_locked.labels(queue._queue_name).set(0)
    queue_items_available.labels(queue._queue_name).set(0)
    queue_items_available_unlocked.labels(queue._queue_name).set(0)

    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    one = queue.get(processing_time=0.5, ordering_required=True)
    assert one is not None
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    one_fail = queue.get(ordering_required=True)
    assert one_fail is None

    time.sleep(1)
    queue.update_metrics()
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    one_again = queue.get(ordering_required=True)
    assert one_again is not None
    assert gauge_value(queue_items_locked) == 1
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1


def test_alive(queue, transaction_factory):
    # No queue item = not alive.
    assert not queue.alive(["abc", "def"])

    # Add a queue item.
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    assert queue.alive(["abc", "def"])

    # Retrieve the queue item.
    queue_item = queue.get()
    assert queue_item is not None
    assert queue.alive(["abc", "def"])

    # Make sure it is running by trying to retrieve it again.
    assert queue.get() is None

    # Delete the queue item.
    queue.complete(queue_item)
    assert not queue.alive(["abc", "def"])


def test_specialized_queue(queue, transaction_factory):
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
    queue.put(["def", "def"], TEST_MESSAGE_2, available_after=-1)

    my_queue = AutoUpdatingQueue(WorkQueue(QUEUE_NAME, transaction_factory, ["def"]))

    two = my_queue.get(ordering_required=True)
    assert two is not None
    assert two.body == TEST_MESSAGE_2

    one_fail = my_queue.get(ordering_required=True)
    assert one_fail is None

    one = queue.get(ordering_required=True)
    assert one is not None
    assert one.body == TEST_MESSAGE_1


def test_random_queue_no_duplicates(queue, transaction_factory):
    for msg in TEST_MESSAGES:
        queue.put(["abc", "def"], msg, available_after=-1)
    seen = set()

    for _ in range(1, 101):
        item = queue.get()
        json_body = json.loads(item.body)
        msg = str(json_body["data"])
        assert msg not in seen
        seen.add(msg)

    for body in TEST_MESSAGES:
        json_body = json.loads(body)
        msg = str(json_body["data"])
        assert msg in seen


def test_bulk_insert(queue, transaction_factory):
    queue_items_locked.labels(queue._queue_name).set(0)
    queue_items_available.labels(queue._queue_name).set(0)
    queue_items_available_unlocked.labels(queue._queue_name).set(0)

    with queue.batch_insert() as queue_put:
        queue_put(["abc", "def"], TEST_MESSAGE_1, available_after=-1)
        queue_put(["abc", "def"], TEST_MESSAGE_2, available_after=-1)

    queue.update_metrics()
    assert not queue._currently_processing
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 1

    with queue.batch_insert() as queue_put:
        queue_put(["abd", "def"], TEST_MESSAGE_1, available_after=-1)
        queue_put(["abd", "ghi"], TEST_MESSAGE_2, available_after=-1)

    queue.update_metrics()
    assert not queue._currently_processing
    assert gauge_value(queue_items_locked) == 0
    assert gauge_value(queue_items_locked) + gauge_value(queue_items_available_unlocked) == 3


def test_num_available_between(queue, transaction_factory):
    now = datetime.utcnow()
    queue.put(["abc", "def"], TEST_MESSAGE_1, available_after=-10)
    queue.put(["abc", "ghi"], TEST_MESSAGE_2, available_after=-5)

    # Partial results
    count = queue.num_available_jobs_between(now - timedelta(seconds=8), now, ["abc"])
    assert count == 1

    # All results
    count = queue.num_available_jobs_between(now - timedelta(seconds=20), now, ["/abc"])
    assert count == 2

    # No results
    count = queue.num_available_jobs_between(now, now, "abc")
    assert count == 0


def test_incomplete(queue, transaction_factory):
    # Add an item.
    queue.put(["somenamespace", "abc", "def"], TEST_MESSAGE_1, available_after=-10)

    now = datetime.utcnow()
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 1

    # Retrieve it.
    item = queue.get()
    assert item is not None
    assert queue._currently_processing

    # Mark it as incomplete.
    queue.incomplete(item, retry_after=-1)
    assert not queue._currently_processing

    # Retrieve again to ensure it is once again available.
    same_item = queue.get()
    assert same_item is not None
    assert queue._currently_processing

    assert item.id == same_item.id


def test_complete(queue, transaction_factory):
    # Add an item.
    queue.put(["somenamespace", "abc", "def"], TEST_MESSAGE_1, available_after=-10)

    now = datetime.utcnow()
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 1

    # Retrieve it.
    item = queue.get()
    assert item is not None
    assert queue._currently_processing

    # Mark it as complete.
    queue.complete(item)
    assert not queue._currently_processing


def test_cancel(queue, transaction_factory):
    # Add an item.
    queue.put(["somenamespace", "abc", "def"], TEST_MESSAGE_1, available_after=-10)
    queue.put(["somenamespace", "abc", "def"], TEST_MESSAGE_2, available_after=-5)

    now = datetime.utcnow()
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 2

    # Retrieve it.
    item = queue.get()
    assert item is not None

    # Make sure we can cancel it.
    assert queue.cancel(item.id)

    now = datetime.utcnow()
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 1

    # Make sure it is gone.
    assert not queue.cancel(item.id)


def test_deleted_namespaced_items(queue, transaction_factory):
    queue = AutoUpdatingQueue(WorkQueue(QUEUE_NAME, transaction_factory, has_namespace=True))

    queue.put(["somenamespace", "abc", "def"], TEST_MESSAGE_1, available_after=-10)
    queue.put(["somenamespace", "abc", "ghi"], TEST_MESSAGE_2, available_after=-5)
    queue.put(["anothernamespace", "abc", "def"], TEST_MESSAGE_1, available_after=-10)

    # Ensure we have 2 items under `somenamespace` and 1 item under `anothernamespace`.
    now = datetime.utcnow()
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 2

    count = queue.num_available_jobs_between(
        now - timedelta(seconds=60), now, ["/anothernamespace"]
    )
    assert count == 1

    # Delete all `somenamespace` items.
    queue.delete_namespaced_items("somenamespace")

    # Check the updated counts.
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 0

    count = queue.num_available_jobs_between(
        now - timedelta(seconds=60), now, ["/anothernamespace"]
    )
    assert count == 1

    # Delete all `anothernamespace` items.
    queue.delete_namespaced_items("anothernamespace")

    # Check the updated counts.
    count = queue.num_available_jobs_between(now - timedelta(seconds=60), now, ["/somenamespace"])
    assert count == 0

    count = queue.num_available_jobs_between(
        now - timedelta(seconds=60), now, ["/anothernamespace"]
    )
    assert count == 0
