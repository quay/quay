import logging.config
import threading
from multiprocessing import Process
from util.log import logfile_path


class GunicornWorker:
    """
    GunicornWorker allows a quay worker to run as a Gunicorn worker.
    The Quay worker is launched as a sub-process and this class serves as a delegate
    for the wsgi app.

    name:           the quay worker this class delegates for.
    app:            a uwsgi framework application object.
    worker:         a quay worker type which implements a .start method.
    feature_flag:   a boolean value determine if the worker thread should be launched
    """

    def __init__(self, name, app, worker, feature_flag):
        logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

        self.app = app
        self.name = name
        self.worker = worker
        self.feature_flag = feature_flag
        self.logger = logging.getLogger(name)

        if self.feature_flag:
            self.logger.debug("starting {} thread".format(self.name))
            p = Process(target=self.worker.start)
            p = p.start()

    def __call__(environ, start_response):
        return self.app(environ, start_response)
