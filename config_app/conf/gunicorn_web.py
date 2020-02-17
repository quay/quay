import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import logging

from Crypto import Random
from config_app.config_util.log import logfile_path


logconfig = logfile_path(debug=True)

bind = "unix:/tmp/gunicorn_web.sock"
workers = 1
worker_class = "gevent"
pythonpath = "."
preload_app = True


def post_fork(server, worker):
    # Reset the Random library to ensure it won't raise the "PID check failed." error after
    # gunicorn forks.
    Random.atfork()


def when_ready(server):
    logger = logging.getLogger(__name__)
    logger.debug(
        "Starting local gunicorn with %s workers and %s worker class", workers, worker_class
    )
