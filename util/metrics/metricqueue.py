import datetime
import logging
import time

from functools import wraps
from Queue import Queue, Full

from flask import g, request
from trollius import Return


logger = logging.getLogger(__name__)

# Buckets for the API response times.
API_RESPONSE_TIME_BUCKETS = [0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

# Buckets for the builder start times.
BUILDER_START_TIME_BUCKETS = [
    0.5,
    1.0,
    5.0,
    10.0,
    30.0,
    60.0,
    120.0,
    180.0,
    240.0,
    300.0,
    600.0,
]


class MetricQueue(object):
    """ Object to which various metrics are written, for distribution to metrics collection
      system(s) such as Prometheus.
  """

    def __init__(self, prom):
        # Define the various exported metrics.
        self.resp_time = prom.create_histogram(
            "response_time",
            "HTTP response time in seconds",
            labelnames=["endpoint"],
            buckets=API_RESPONSE_TIME_BUCKETS,
        )
        self.resp_code = prom.create_counter(
            "response_code", "HTTP response code", labelnames=["endpoint", "code"]
        )
        self.non_200 = prom.create_counter(
            "response_non200", "Non-200 HTTP response codes", labelnames=["endpoint"]
        )
        self.error_500 = prom.create_counter(
            "response_500", "5XX HTTP response codes", labelnames=["endpoint"]
        )
        self.multipart_upload_start = prom.create_counter(
            "multipart_upload_start", "Multipart upload started"
        )
        self.multipart_upload_end = prom.create_counter(
            "multipart_upload_end", "Multipart upload ends.", labelnames=["type"]
        )
        self.build_capacity_shortage = prom.create_gauge(
            "build_capacity_shortage", "Build capacity shortage."
        )
        self.builder_time_to_start = prom.create_histogram(
            "builder_tts",
            "Time from triggering to starting a builder.",
            labelnames=["builder_type"],
            buckets=BUILDER_START_TIME_BUCKETS,
        )
        self.builder_time_to_build = prom.create_histogram(
            "builder_ttb",
            "Time from triggering to actually starting a build",
            labelnames=["builder_type"],
            buckets=BUILDER_START_TIME_BUCKETS,
        )
        self.build_time = prom.create_histogram(
            "build_time", "Time spent building", labelnames=["builder_type"]
        )
        self.builder_fallback = prom.create_counter(
            "builder_fallback", "Builder fell back to secondary executor"
        )
        self.build_start_success = prom.create_counter(
            "build_start_success",
            "Executor succeeded in starting a build",
            labelnames=["builder_type"],
        )
        self.build_start_failure = prom.create_counter(
            "build_start_failure",
            "Executor failed to start a build",
            labelnames=["builder_type"],
        )
        self.percent_building = prom.create_gauge(
            "build_percent_building", "Percent building."
        )
        self.build_counter = prom.create_counter(
            "builds", "Number of builds", labelnames=["name"]
        )
        self.ephemeral_build_workers = prom.create_counter(
            "ephemeral_build_workers", "Number of started ephemeral build workers"
        )
        self.ephemeral_build_worker_failure = prom.create_counter(
            "ephemeral_build_worker_failure",
            "Number of failed-to-start ephemeral build workers",
        )

        self.work_queue_running = prom.create_gauge(
            "work_queue_running", "Running items in a queue", labelnames=["queue_name"]
        )
        self.work_queue_available = prom.create_gauge(
            "work_queue_available",
            "Available items in a queue",
            labelnames=["queue_name"],
        )

        self.work_queue_available_not_running = prom.create_gauge(
            "work_queue_available_not_running",
            "Available items that are not yet running",
            labelnames=["queue_name"],
        )

        self.repository_pull = prom.create_counter(
            "repository_pull",
            "Repository Pull Count",
            labelnames=["namespace", "repo_name", "protocol", "status"],
        )

        self.repository_push = prom.create_counter(
            "repository_push",
            "Repository Push Count",
            labelnames=["namespace", "repo_name", "protocol", "status"],
        )

        self.repository_build_queued = prom.create_counter(
            "repository_build_queued",
            "Repository Build Queued Count",
            labelnames=["namespace", "repo_name"],
        )

        self.repository_build_completed = prom.create_counter(
            "repository_build_completed",
            "Repository Build Complete Count",
            labelnames=["namespace", "repo_name", "status", "executor"],
        )

        self.chunk_size = prom.create_histogram(
            "chunk_size", "Registry blob chunk size", labelnames=["storage_region"]
        )

        self.chunk_upload_time = prom.create_histogram(
            "chunk_upload_time",
            "Registry blob chunk upload time",
            labelnames=["storage_region"],
        )

        self.authentication_count = prom.create_counter(
            "authentication_count",
            "Authentication count",
            labelnames=["kind", "status"],
        )

        self.repository_count = prom.create_gauge(
            "repository_count", "Number of repositories"
        )
        self.user_count = prom.create_gauge("user_count", "Number of users")
        self.org_count = prom.create_gauge("org_count", "Number of Organizations")
        self.robot_count = prom.create_gauge("robot_count", "Number of robot accounts")

        self.instance_key_renewal_success = prom.create_counter(
            "instance_key_renewal_success",
            "Instance Key Renewal Success Count",
            labelnames=["key_id"],
        )

        self.instance_key_renewal_failure = prom.create_counter(
            "instance_key_renewal_failure",
            "Instance Key Renewal Failure Count",
            labelnames=["key_id"],
        )

        self.invalid_instance_key_count = prom.create_counter(
            "invalid_registry_instance_key_count",
            "Invalid registry instance key count",
            labelnames=["key_id"],
        )

        self.verb_action_passes = prom.create_counter(
            "verb_action_passes", "Verb Pass Count", labelnames=["kind", "pass_count"]
        )

        self.push_byte_count = prom.create_counter(
            "registry_push_byte_count", "Number of bytes pushed to the registry"
        )

        self.pull_byte_count = prom.create_counter(
            "estimated_registry_pull_byte_count",
            "Number of (estimated) bytes pulled from the registry",
            labelnames=["protocol_version"],
        )

        # Deprecated: Define an in-memory queue for reporting metrics to CloudWatch or another
        # provider.
        self._queue = None

    def enable_deprecated(self, maxsize=10000):
        self._queue = Queue(maxsize)

    def put_deprecated(self, name, value, **kwargs):
        if self._queue is None:
            logger.debug("No metric queue %s %s %s", name, value, kwargs)
            return

        try:
            kwargs.setdefault("timestamp", datetime.datetime.now())
            kwargs.setdefault("dimensions", {})
            self._queue.put_nowait((name, value, kwargs))
        except Full:
            logger.error("Metric queue full")

    def get_deprecated(self):
        return self._queue.get()

    def get_nowait_deprecated(self):
        return self._queue.get_nowait()


def duration_collector_async(metric, labelvalues):
    """ Decorates a method to have its duration time logged to the metric. """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            trigger_time = time.time()
            try:
                rv = func(*args, **kwargs)
            except Return as e:
                metric.Observe(time.time() - trigger_time, labelvalues=labelvalues)
                raise e
            return rv

        return wrapper

    return decorator


def time_decorator(name, metric_queue):
    """ Decorates an endpoint method to have its request time logged to the metrics queue. """
    after = _time_after_request(name, metric_queue)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _time_before_request()
            rv = func(*args, **kwargs)
            after(rv)
            return rv

        return wrapper

    return decorator


def time_blueprint(bp, metric_queue):
    """ Decorates a blueprint to have its request time logged to the metrics queue. """
    bp.before_request(_time_before_request)
    bp.after_request(_time_after_request(bp.name, metric_queue))


def _time_before_request():
    g._request_start_time = time.time()


def _time_after_request(name, metric_queue):
    def f(r):
        start = getattr(g, "_request_start_time", None)
        if start is None:
            return r

        dur = time.time() - start

        metric_queue.resp_time.Observe(dur, labelvalues=[request.endpoint])
        metric_queue.resp_code.Inc(labelvalues=[request.endpoint, r.status_code])

        if r.status_code >= 500:
            metric_queue.error_500.Inc(labelvalues=[request.endpoint])
        elif r.status_code < 200 or r.status_code >= 300:
            metric_queue.non_200.Inc(labelvalues=[request.endpoint])

        return r

    return f
