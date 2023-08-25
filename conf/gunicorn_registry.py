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
bind = "unix:/tmp/gunicorn_registry.sock"
workers = get_worker_count("registry", 4, minimum=8, maximum=64)
worker_class = "gevent"
worker_connections = get_worker_connections_count("registry")
pythonpath = "."
if os.getenv("QUAY_HOTRELOAD", "false") == "true":
    reload = True
    reload_engine = "auto"
else:
    preload_app = True


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting registry gunicorn with %s workers and %s worker class", workers, worker_class
    )
