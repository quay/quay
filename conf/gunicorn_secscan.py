import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from Crypto import Random
from prometheus_client import Gauge

from util.log import logfile_path
from util.workers import get_worker_count, get_worker_connections_count


logconfig = logfile_path(debug=False)
bind = "unix:/tmp/gunicorn_secscan.sock"
workers = get_worker_count("secscan", 2, minimum=2, maximum=4)
worker_class = "gevent"
worker_connections = get_worker_connections_count("secscan")
pythonpath = "."
preload_app = True


prometheus_workers_gauge = Gauge(
    "quay_gunicorn_workers",
    "number of gunicorn workers handling the security scanning endpoints",
    labelnames=["gunicorn_workers"],
)


def post_fork(server, worker):
    # Reset the Random library to ensure it won't raise the "PID check failed." error after
    # gunicorn forks.
    Random.atfork()


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting secscan gunicorn with %s workers and %s worker class", workers, worker_class
    )


def nworkers_changed(server, new_value, old_value):
    """
    Called when the number of gunicorn workers is changed.
    NOTE: old_value=None the first time this is called.
    """
    prometheus_workers_gauge.labels("secscan").set(new_value)
    logger = logging.getLogger(__name__)
    msg = "Changed gunicorn worker count from %s to %s" % (old_value, new_value)
    logging.debug(msg)
