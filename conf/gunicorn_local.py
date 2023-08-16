import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from util.log import logfile_path
from util.workers import get_worker_connections_count, get_worker_count

logconfig = logfile_path(debug=True)
bind = "0.0.0.0:5000"
workers = get_worker_count("local", 2, minimum=2, maximum=8)
worker_class = "gevent"
worker_connections = get_worker_connections_count("local")
daemon = False
pythonpath = "."
if os.getenv("QUAY_HOTRELOAD", "false") == "true":
    reload = True
    reload_engine = "auto"
else:
    preload_app = True


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting local gunicorn with %s workers and %s worker class", workers, worker_class
    )
