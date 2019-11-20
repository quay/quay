import time

import pytest

from mock import Mock
from trollius import coroutine, Return, get_event_loop, From

from util.metrics.metricqueue import duration_collector_async


mock_histogram = Mock()


class NonReturn(Exception):
    pass


@coroutine
@duration_collector_async(mock_histogram, labelvalues=["testlabel"])
def duration_decorated():
    time.sleep(1)
    raise Return("fin")


@coroutine
@duration_collector_async(mock_histogram, labelvalues=["testlabel"])
def duration_decorated_error():
    raise NonReturn("not a Return error")


@coroutine
def calls_decorated():
    yield From(duration_decorated())


def test_duration_decorator():
    loop = get_event_loop()
    loop.run_until_complete(duration_decorated())
    assert mock_histogram.Observe.called
    assert (
        1 - mock_histogram.Observe.call_args[0][0] < 1
    )  # duration should be close to 1s
    assert mock_histogram.Observe.call_args[1]["labelvalues"] == ["testlabel"]


def test_duration_decorator_error():
    loop = get_event_loop()
    mock_histogram.reset_mock()

    with pytest.raises(NonReturn):
        loop.run_until_complete(duration_decorated_error())
    assert not mock_histogram.Observe.called


def test_duration_decorator_caller():
    mock_histogram.reset_mock()

    loop = get_event_loop()
    loop.run_until_complete(calls_decorated())
    assert mock_histogram.Observe.called
    assert (
        1 - mock_histogram.Observe.call_args[0][0] < 1
    )  # duration should be close to 1s
    assert mock_histogram.Observe.call_args[1]["labelvalues"] == ["testlabel"]
