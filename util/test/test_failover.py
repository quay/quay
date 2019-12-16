import pytest

from util.failover import failover, FailoverException


class FinishedException(Exception):
    """
    Exception raised at the end of every iteration to force failover.
    """


class Counter(object):
    """
    Wraps a counter in an object so that it'll be passed by reference.
    """

    def __init__(self):
        self.calls = 0

    def increment(self):
        self.calls += 1


@failover
def my_failover_func(i, should_raise=None):
    """
    Increments a counter and raises an exception when told.
    """
    i.increment()
    if should_raise is not None:
        raise should_raise()
    raise FailoverException(FinishedException())


@pytest.mark.parametrize("stop_on,exception", [(10, None), (5, IndexError),])
def test_readonly_failover(stop_on, exception):
    """
    Generates failover arguments and checks against a counter to ensure that the failover function
    has been called the proper amount of times and stops at unhandled exceptions.
    """
    counter = Counter()
    arg_sets = []
    for i in range(stop_on):
        should_raise = exception if exception is not None and i == stop_on - 1 else None
        arg_sets.append(((counter,), {"should_raise": should_raise}))

    if exception is not None:
        with pytest.raises(exception):
            my_failover_func(*arg_sets)
    else:
        with pytest.raises(FinishedException):
            my_failover_func(*arg_sets)
        assert counter.calls == stop_on
