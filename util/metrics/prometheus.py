import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import namedtuple

from cachetools.func import lru_cache
from flask import g, request
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, push_to_gateway

logger = logging.getLogger(__name__)

def get_namespace_bucket_mapping():
    """
    Get namespace to bucket mapping from config.
    Supports two formats:
    1. List format: ["namespace1", "namespace2"] -> maps each to its own name
    2. Dict format: {"bucket1": ["namespace1", "namespace2"], "bucket2": ["namespace3"]}
    Returns a dict mapping namespace -> bucket_name.
    """
    try:
        from app import app
        if app and hasattr(app, "config"):
            tracked = app.config.get("TRACKED_NAMESPACES", [])
            if not tracked:
                return {}
            
            # If it's a dict, use it directly (namespace -> bucket mapping)
            if isinstance(tracked, dict):
                mapping = {}
                for bucket_name, namespaces in tracked.items():
                    if isinstance(namespaces, (list, tuple)):
                        for ns in namespaces:
                            mapping[ns] = bucket_name
                    else:
                        # Single namespace string
                        mapping[namespaces] = bucket_name
                return mapping
            
            # If it's a list, map each namespace to itself (backward compatibility)
            elif isinstance(tracked, (list, tuple)):
                return {ns: ns for ns in tracked}
            
            # Single string value
            elif isinstance(tracked, str):
                return {tracked: tracked}
    except:
        pass
    return {}


def get_namespace_label_for_counter(namespace_name):
    """
    Get namespace label (bucket) for high-frequency counter metrics.
    Returns bucket name if namespace is tracked, None otherwise.
    Multiple namespaces can map to the same bucket.
    """
    if not namespace_name:
        return None
    mapping = get_namespace_bucket_mapping()
    return mapping.get(namespace_name)


def get_namespace_label_for_gauge(namespace_name):
    """
    Get namespace label for low-frequency gauge metrics.
    Returns namespace name directly (safe for gauges updated infrequently).
    """
    return namespace_name if namespace_name else "unknown"


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
    labelnames=["method", "route", "status", "namespace"],
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

secscan_request_duration = Histogram(
    "quay_secscan_request_duration_seconds",
    "seconds taken to make an index request to the secscan service",
    labelnames=["method", "action", "status"],
)

secscan_index_layer_size = Histogram(
    "quay_secscan_index_layer_size_bytes",
    "bytes submitted to index to the secscan service",
)

INF = float("inf")
SECSCAN_RESULT_BUCKETS = (60, 300, 600, 900, 1200, 1500, 1800, 2100, 2400, INF)

secscan_result_duration = Histogram(
    "quay_secscan_result_duration_seconds",
    "how long it takes to receive scan results after pushing an image",
    buckets=SECSCAN_RESULT_BUCKETS,
)


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


def _extract_namespace_from_request():
    """
    Extract namespace from Flask request.
    Checks route parameters first, then tries to parse from path.
    """
    # Try to get namespace from route parameters (most common case)
    if hasattr(request, "view_args") and request.view_args:
        namespace = request.view_args.get("namespace_name") or request.view_args.get("namespace")
        if namespace:
            return namespace
    
    # Try to parse from request path
    try:
        path = request.path.strip("/")
        if "/" in path:
            # Try to parse as namespace/repository
            parts = path.split("/", 1)
            if len(parts) >= 1:
                potential_namespace = parts[0]
                # Basic validation: namespace should be alphanumeric with dashes/underscores
                if potential_namespace and all(c.isalnum() or c in "-_" for c in potential_namespace):
                    return potential_namespace
    except:
        pass
    
    return None


def timed_blueprint(bp):
    """
    Decorates a blueprint to have its request duration tracked by Prometheus.
    Includes namespace label for tracked namespaces.
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
            
            # Extract namespace from request
            namespace_name = _extract_namespace_from_request()
            namespace_label = get_namespace_label_for_counter(namespace_name)
            # Use "other" for untracked namespaces to keep cardinality low
            label_value = namespace_label if namespace_label else "other"
            
            request_duration.labels(
                request.method, 
                request.endpoint, 
                r.status_code,
                label_value
            ).observe(dur)
            return r

        return f

    bp.after_request(_time_after_request())
    return bp
