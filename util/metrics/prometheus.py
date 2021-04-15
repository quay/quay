import logging
import os
import socket
import sys
import threading
import time
from collections import namedtuple
import urllib.request, urllib.error, urllib.parse

from cachetools.func import lru_cache

from flask import g, request
from prometheus_client import push_to_gateway, REGISTRY, Histogram, Gauge, Counter


logger = logging.getLogger(__name__)


# DB connections
db_pooled_connections_in_use = Gauge(
    "quay_db_pooled_connections_in_use", "number of pooled db connections in use"
)
db_pooled_connections_available = Gauge(
    "quay_db_pooled_connections_available", "number of pooled db connections available"
)
db_connect_calls = Counter(
    "quay_db_connect_calls",
    "number of connect() calls made to db",
)
db_close_calls = Counter(
    "quay_db_close_calls",
    "number of close() calls made to db",
)

request_duration = Histogram(
    "quay_request_duration_seconds",
    "seconds taken to process a request",
    labelnames=["method", "route", "status"],
)

# GC: DB table rows
gc_table_rows_deleted = Counter(
    "quay_gc_table_rows_deleted", "number of table rows deleted by GC", labelnames=["table"]
)

# GC: Storage blob
gc_storage_blobs_deleted = Counter(
    "quay_gc_storage_blobs_deleted", "number of storage blobs deleted"
)

# GC iterations
gc_repos_purged = Counter(
    "quay_gc_repos_purged",
    "number of repositories purged by the RepositoryGCWorker or NamespaceGCWorker",
)
gc_namespaces_purged = Counter(
    "quay_gc_namespaces_purged", "number of namespaces purged by the NamespaceGCWorker"
)
gc_iterations = Counter("quay_gc_iterations", "number of iterations by the GCWorker")


PROMETHEUS_PUSH_INTERVAL_SECONDS = 30
ONE_DAY_IN_SECONDS = 60 * 60 * 24


@lru_cache(maxsize=1)
def process_grouping_key():
    """
    Implements a grouping key based on the last argument used to run the current process.

    https://github.com/prometheus/client_python#exporting-to-a-pushgateway
    """
    return {
        "host": socket.gethostname(),
        "process_name": os.path.basename(sys.argv[-1]),
        "pid": str(os.getpid()),
    }


class PrometheusPlugin(object):
    """
    Application plugin for reporting metrics to Prometheus.
    """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        pusher = ThreadPusher(app)
        pusher.start()

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["prometheus"] = pusher
        return pusher

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class ThreadPusher(threading.Thread):
    def __init__(self, app):
        super(ThreadPusher, self).__init__()
        self.daemon = True
        self._app = app

    def run(self):
        agg_url = self._app.config.get("PROMETHEUS_PUSHGATEWAY_URL")
        while True:
            # Practically disable this worker, if there is no pushgateway.
            if agg_url is None or os.getenv("TEST", "false").lower() == "true":
                time.sleep(ONE_DAY_IN_SECONDS)
                continue

            time.sleep(PROMETHEUS_PUSH_INTERVAL_SECONDS)
            try:
                push_to_gateway(
                    agg_url,
                    job=self._app.config.get("PROMETHEUS_NAMESPACE", "quay"),
                    registry=REGISTRY,
                    grouping_key=process_grouping_key(),
                )
                logger.debug(
                    "pushed registry to pushgateway at %s with grouping key %s",
                    agg_url,
                    process_grouping_key(),
                )
            except urllib.error.URLError:
                # There are many scenarios when the gateway might not be running.
                # These could be testing scenarios or simply processes racing to start.
                # Rather than try to guess all of them, keep it simple and let it fail.
                if os.getenv("DEBUGLOG", "false").lower() == "true":
                    logger.exception(
                        "failed to push registry to pushgateway at %s with grouping key %s",
                        agg_url,
                        process_grouping_key(),
                    )
                else:
                    pass


def timed_blueprint(bp):
    """
    Decorates a blueprint to have its request duration tracked by Prometheus.
    """

    def _time_before_request():
        g._request_start_time = time.time()

    bp.before_request(_time_before_request)

    def _time_after_request():
        def f(r):
            start = getattr(g, "_request_start_time", None)
            if start is None:
                return r
            dur = time.time() - start
            request_duration.labels(request.method, request.endpoint, r.status_code).observe(dur)
            return r

        return f

    bp.after_request(_time_after_request())
    return bp
