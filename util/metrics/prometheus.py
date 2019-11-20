import datetime
import json
import logging

from Queue import Queue, Full, Empty
from threading import Thread

import requests


logger = logging.getLogger(__name__)

QUEUE_MAX = 1000
MAX_BATCH_SIZE = 100
REGISTER_WAIT = datetime.timedelta(hours=1)


class PrometheusPlugin(object):
    """ Application plugin for reporting metrics to Prometheus. """

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        prom_url = app.config.get("PROMETHEUS_AGGREGATOR_URL")
        prom_namespace = app.config.get("PROMETHEUS_NAMESPACE")
        logger.debug("Initializing prometheus with aggregator url: %s", prom_url)
        prometheus = Prometheus(prom_url, prom_namespace)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["prometheus"] = prometheus
        return prometheus

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class Prometheus(object):
    """ Aggregator for collecting stats that are reported to Prometheus. """

    def __init__(self, url=None, namespace=None):
        self._metric_collectors = []
        self._url = url
        self._namespace = namespace or ""

        if url is not None:
            self._queue = Queue(QUEUE_MAX)
            self._sender = _QueueSender(self._queue, url, self._metric_collectors)
            self._sender.start()
            logger.debug("Prometheus aggregator sending to %s", url)
        else:
            self._queue = None
            logger.debug("Prometheus aggregator disabled")

    def enqueue(self, call, data):
        if not self._queue:
            return

        v = json.dumps({"Call": call, "Data": data})

        if call == "register":
            self._metric_collectors.append(v)
            return

        try:
            self._queue.put_nowait(v)
        except Full:
            # If the queue is full, it is because 1) no aggregator was enabled or 2)
            # the aggregator is taking a long time to respond to requests. In the case
            # of 1, it's probably enterprise mode and we don't care. In the case of 2,
            # the response timeout error is printed inside the queue handler. In either case,
            # we don't need to print an error here.
            pass

    def create_gauge(self, *args, **kwargs):
        return self._create_collector("Gauge", args, kwargs)

    def create_counter(self, *args, **kwargs):
        return self._create_collector("Counter", args, kwargs)

    def create_summary(self, *args, **kwargs):
        return self._create_collector("Summary", args, kwargs)

    def create_histogram(self, *args, **kwargs):
        return self._create_collector("Histogram", args, kwargs)

    def create_untyped(self, *args, **kwargs):
        return self._create_collector("Untyped", args, kwargs)

    def _create_collector(self, collector_type, args, kwargs):
        kwargs["namespace"] = kwargs.get("namespace", self._namespace)
        return _Collector(self.enqueue, collector_type, *args, **kwargs)


class _QueueSender(Thread):
    """ Helper class which uses a thread to asynchronously send metrics to the local Prometheus
      aggregator. """

    def __init__(self, queue, url, metric_collectors):
        Thread.__init__(self)
        self.daemon = True
        self.next_register = datetime.datetime.now()
        self._queue = queue
        self._url = url
        self._metric_collectors = metric_collectors

    def run(self):
        while True:
            reqs = []
            reqs.append(self._queue.get())

            while len(reqs) < MAX_BATCH_SIZE:
                try:
                    req = self._queue.get_nowait()
                    reqs.append(req)
                except Empty:
                    break

            try:
                resp = requests.post(self._url + "/call", "\n".join(reqs))
                if (
                    resp.status_code == 500
                    and self.next_register <= datetime.datetime.now()
                ):
                    resp = requests.post(
                        self._url + "/call", "\n".join(self._metric_collectors)
                    )
                    self.next_register = datetime.datetime.now() + REGISTER_WAIT
                    logger.debug(
                        "Register returned %s for %s metrics; setting next to %s",
                        resp.status_code,
                        len(self._metric_collectors),
                        self.next_register,
                    )
                elif resp.status_code != 200:
                    logger.debug(
                        "Failed sending to prometheus: %s: %s: %s",
                        resp.status_code,
                        resp.text,
                        ", ".join(reqs),
                    )
                else:
                    logger.debug("Sent %d prometheus metrics", len(reqs))
            except:
                logger.exception("Failed to write to prometheus aggregator: %s", reqs)


class _Collector(object):
    """ Collector for a Prometheus metric. """

    def __init__(
        self,
        enqueue_method,
        collector_type,
        collector_name,
        collector_help,
        namespace="",
        subsystem="",
        **kwargs
    ):
        self._enqueue_method = enqueue_method
        self._base_args = {
            "Name": collector_name,
            "Namespace": namespace,
            "Subsystem": subsystem,
            "Type": collector_type,
        }

        registration_params = dict(kwargs)
        registration_params.update(self._base_args)
        registration_params["Help"] = collector_help

        self._enqueue_method("register", registration_params)

    def __getattr__(self, method):
        def f(value=0, labelvalues=()):
            data = dict(self._base_args)
            data.update(
                {
                    "Value": value,
                    "LabelValues": [str(i) for i in labelvalues],
                    "Method": method,
                }
            )

            self._enqueue_method("put", data)

        return f
