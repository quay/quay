# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from Crypto import Random

bind = "unix:/tmp/gunicorn_web.sock"
workers = 1
worker_class = "gevent"
worker_connections = 30
pythonpath = "."
reload = True
reload_engine = "auto"


def post_fork(server, worker):
    # Reset the Random library to ensure it won't raise the "PID check failed." error after
    # gunicorn forks.
    Random.atfork()


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug("Starting web gunicorn with %s workers and %s worker class", workers, worker_class)
