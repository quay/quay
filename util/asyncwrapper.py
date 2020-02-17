import queue

from functools import wraps

from concurrent.futures import Executor, Future, CancelledError


class AsyncExecutorWrapper(object):
    """
    This class will wrap a syncronous library transparently in a way which will move all calls off
    to an asynchronous Executor, and will change all returned values to be Future objects.
    """

    SYNC_FLAG_FIELD = "__AsyncExecutorWrapper__sync__"

    def __init__(self, delegate, executor):
        """
        Wrap the specified synchronous delegate instance, and submit() all method calls to the
        specified Executor instance.
        """
        self._delegate = delegate
        self._executor = executor

    def __getattr__(self, attr_name):
        maybe_callable = getattr(self._delegate, attr_name)  # Will raise proper attribute error
        if callable(maybe_callable):
            # Build a callable which when executed places the request
            # onto a queue
            @wraps(maybe_callable)
            def wrapped_method(*args, **kwargs):
                if getattr(maybe_callable, self.SYNC_FLAG_FIELD, False):
                    sync_result = Future()
                    try:
                        sync_result.set_result(maybe_callable(*args, **kwargs))
                    except Exception as ex:
                        sync_result.set_exception(ex)
                    return sync_result

                try:
                    return self._executor.submit(maybe_callable, *args, **kwargs)
                except queue.Full as ex:
                    queue_full = Future()
                    queue_full.set_exception(ex)
                    return queue_full

            return wrapped_method
        else:
            return maybe_callable

    @classmethod
    def sync(cls, f):
        """
        Annotate the given method to flag it as synchronous so that AsyncExecutorWrapper will return
        the result immediately without submitting it to the executor.
        """
        setattr(f, cls.SYNC_FLAG_FIELD, True)
        return f


class NullExecutorCancelled(CancelledError):
    def __init__(self):
        super(NullExecutorCancelled, self).__init__("Null executor always fails.")


class NullExecutor(Executor):
    """
    Executor instance which always returns a Future completed with a CancelledError exception.
    """

    def submit(self, _, *args, **kwargs):
        always_fail = Future()
        always_fail.set_exception(NullExecutorCancelled())
        return always_fail
