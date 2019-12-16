import logging
from config_app.c_app import app as application
from util.log import logfile_path

# Bind all of the blueprints
from . import config_web


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=True), disable_existing_loggers=False)
    application.run(port=5000, debug=True, threaded=True, host="0.0.0.0")
