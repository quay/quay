# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging


bind = "unix:/tmp/gunicorn_registry.sock"
workers = 1
worker_class = "gevent"
worker_connections = 30
pythonpath = "."
reload = True
reload_engine = "auto"


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting registry gunicorn with %s workers and %s worker class", workers, worker_class
    )
