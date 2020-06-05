import asyncio

from concurrent.futures import ThreadPoolExecutor
from functools import partial


def wrap_with_threadpool(obj, worker_threads=1):
    """
    Wraps a class in an async executor so that it can be safely used in an event loop like asyncio.
    """
    async_executor = ThreadPoolExecutor(worker_threads)
    return AsyncWrapper(obj, executor=async_executor), async_executor


class AsyncWrapper(object):
    """
    Wrapper class which will transform a syncronous library to one that can be used with asyncio
    coroutines.
    """

    def __init__(self, delegate, loop=None, executor=None):
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._delegate = delegate
        self._executor = executor

    def __getattr__(self, attrib):
        delegate_attr = getattr(self._delegate, attrib)

        if not callable(delegate_attr):
            return delegate_attr

        def wrapper(*args, **kwargs):
            """
            Wraps the delegate_attr with primitives that will transform sync calls to ones shelled
            out to a thread pool.
            """
            callable_delegate_attr = partial(delegate_attr, *args, **kwargs)
            return self._loop.run_in_executor(self._executor, callable_delegate_attr)

        return wrapper

    async def __call__(self, *args, **kwargs):
        callable_delegate_attr = partial(self._delegate, *args, **kwargs)
        return self._loop.run_in_executor(self._executor, callable_delegate_attr)
