import multiprocessing
import time
import socket

from contextlib import contextmanager
from .data.database import LogEntryKind, LogEntry3


class assert_action_logged(object):
    """
    Specialized assertion for ensuring that a log entry of a particular kind was added under the
    context of this call.
    """

    def __init__(self, log_kind):
        self.log_kind = log_kind
        self.existing_count = 0

    def _get_log_count(self):
        return (
            LogEntry3.select().where(LogEntry3.kind == LogEntryKind.get(name=self.log_kind)).count()
        )

    def __enter__(self):
        self.existing_count = self._get_log_count()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            updated_count = self._get_log_count()
            error_msg = "Missing new log entry of kind %s" % self.log_kind
            assert self.existing_count == (updated_count - 1), error_msg


_LIVESERVER_TIMEOUT = 5


@contextmanager
def liveserver_app(flask_app, port):
    """
    Based on https://github.com/jarus/flask-testing/blob/master/flask_testing/utils.py.

    Runs the given Flask app as a live web server locally, on the given port, starting it
    when called and terminating after the yield.

    Usage:
    with liveserver_app(flask_app, port):
      # Code that makes use of the app.
    """
    shared = {}

    def _can_ping_server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            sock.connect(("localhost", port))
        except socket.error:
            success = False
        else:
            success = True
        finally:
            sock.close()

        return success

    def _spawn_live_server():
        worker = lambda app, port: app.run(port=port, use_reloader=False)
        shared["process"] = multiprocessing.Process(target=worker, args=(flask_app, port))
        shared["process"].start()

        start_time = time.time()
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > _LIVESERVER_TIMEOUT:
                _terminate_live_server()
                raise RuntimeError(
                    "Failed to start the server after %d seconds. " % _LIVESERVER_TIMEOUT
                )

            if _can_ping_server():
                break

    def _terminate_live_server():
        if shared.get("process"):
            shared.get("process").terminate()
            shared.pop("process")

    try:
        _spawn_live_server()
        yield
    finally:
        _terminate_live_server()
