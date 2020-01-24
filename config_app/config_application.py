from config_app import config_web
from config_app.c_app import app as application


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=True), disable_existing_loggers=False)
    application.run(port=5000, debug=True, threaded=True, host="0.0.0.0")
