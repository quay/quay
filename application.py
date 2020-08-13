# NOTE: Must be before we import or call anything that may be synchronous.
from gevent import monkey

monkey.patch_all()

import os
import logging
import logging.config

from util.log import logfile_path
from app import app as application


# Bind all of the blueprints
import web
import registry
import secscan


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=True), disable_existing_loggers=False)
    application.run(port=5000, debug=True, threaded=True, host="0.0.0.0")
