# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from util.log import logfile_path
from util.workers import get_worker_connections_count, get_worker_count

logconfig = logfile_path(debug=False)
bind = "unix:/tmp/gunicorn_blobstream.sock"
workers = get_worker_count("blobstream", 2, minimum=2, maximum=8)
worker_class = "gevent"
worker_connections = get_worker_connections_count("blobstream")

timeout = 0  # unbounded - dedicated process
pythonpath = "."
preload_app = True


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting blobstream gunicorn with %s workers and %s worker class", workers, worker_class
    )


def post_fork(server, worker):
    import features

    if features.OTEL_TRACING:
        from util.metrics.otel import post_fork_init

        post_fork_init()
