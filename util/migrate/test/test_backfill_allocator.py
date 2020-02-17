import random

import pytest

from datetime import datetime, timedelta
from util.migrate.allocator import CompletedKeys, NoAvailableKeysError, yield_random_entries


def test_merge_blocks_operations():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10
    candidates.mark_completed(1, 5)

    assert candidates.is_available(5)
    assert candidates.is_available(0)
    assert not candidates.is_available(1)
    assert not candidates.is_available(4)
    assert not candidates.is_available(11)
    assert not candidates.is_available(10)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 6

    candidates.mark_completed(5, 6)
    assert not candidates.is_available(5)
    assert candidates.is_available(6)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 5

    candidates.mark_completed(3, 8)
    assert candidates.is_available(9)
    assert candidates.is_available(8)
    assert not candidates.is_available(7)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 3


def test_adjust_max():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10
    assert len(candidates._slabs) == 0

    assert candidates.is_available(9)
    candidates.mark_completed(5, 12)
    assert len(candidates._slabs) == 0
    assert candidates.num_remaining == 5

    assert not candidates.is_available(9)
    assert candidates.is_available(4)


def test_adjust_min():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10
    assert len(candidates._slabs) == 0

    assert candidates.is_available(2)
    candidates.mark_completed(0, 3)
    assert len(candidates._slabs) == 0
    assert candidates.num_remaining == 7

    assert not candidates.is_available(2)
    assert candidates.is_available(4)


def test_inside_block():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10
    candidates.mark_completed(1, 8)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 3

    candidates.mark_completed(2, 5)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 3
    assert not candidates.is_available(1)
    assert not candidates.is_available(5)


def test_wrap_block():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10
    candidates.mark_completed(2, 5)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 7

    candidates.mark_completed(1, 8)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 3
    assert not candidates.is_available(1)
    assert not candidates.is_available(5)


def test_non_contiguous():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10

    candidates.mark_completed(1, 5)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 6
    assert candidates.is_available(5)
    assert candidates.is_available(6)

    candidates.mark_completed(6, 8)
    assert len(candidates._slabs) == 2
    assert candidates.num_remaining == 4
    assert candidates.is_available(5)
    assert not candidates.is_available(6)


def test_big_merge():
    candidates = CompletedKeys(10)
    assert candidates.num_remaining == 10

    candidates.mark_completed(1, 5)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 6

    candidates.mark_completed(6, 8)
    assert len(candidates._slabs) == 2
    assert candidates.num_remaining == 4

    candidates.mark_completed(5, 6)
    assert len(candidates._slabs) == 1
    assert candidates.num_remaining == 3


def test_range_limits():
    candidates = CompletedKeys(10)
    assert not candidates.is_available(-1)
    assert not candidates.is_available(10)

    assert candidates.is_available(9)
    assert candidates.is_available(0)


def test_random_saturation():
    candidates = CompletedKeys(100)
    with pytest.raises(NoAvailableKeysError):
        for _ in range(101):
            start = candidates.get_block_start_index(10)
            assert candidates.is_available(start)
            candidates.mark_completed(start, start + 10)

    assert candidates.num_remaining == 0


def test_huge_dataset():
    candidates = CompletedKeys(1024 * 1024)
    start_time = datetime.now()
    iterations = 0
    with pytest.raises(NoAvailableKeysError):
        while (datetime.now() - start_time) < timedelta(seconds=10):
            start = candidates.get_block_start_index(1024)
            assert candidates.is_available(start)
            candidates.mark_completed(start, start + random.randint(512, 1024))
            iterations += 1

    assert iterations > 1024
    assert candidates.num_remaining == 0


class FakeQuery(object):
    def __init__(self, result_list):
        self._result_list = result_list

    def limit(self, *args, **kwargs):
        return self

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def __iter__(self):
        return self._result_list.__iter__()


FAKE_PK_FIELD = 10  # Must be able to compare to integers


def test_no_work():
    def create_empty_query():
        return FakeQuery([])

    for _ in yield_random_entries(create_empty_query, FAKE_PK_FIELD, 1, 10):
        assert False, "There should never be any actual work!"
