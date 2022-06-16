import logging
import logging.config
from multiprocessing import Process
from typing import Union, TYPE_CHECKING
from util.log import logfile_path

if TYPE_CHECKING:
    from features import FeatureNameValue
    from workers.worker import Worker


class GunicornWorker:
    """
    GunicornWorker allows a Quay worker to run as a Gunicorn worker.
    The Quay worker is launched as a sub-process.

    name:           the quay worker this class delegates for.
    worker:         a quay worker type which implements a .start method.
    feature_flag:   a boolean value determine if the worker thread should be launched
    """

    def __init__(
        self, name: str, worker: "Worker", feature_flag: Union[bool, "FeatureNameValue"]
    ) -> None:
        logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

        self.name = name
        self.worker = worker
        self.feature_flag = feature_flag
        self.logger = logging.getLogger(name)

        if self.feature_flag:
            self.logger.debug("starting {} thread".format(self.name))
            p = Process(target=self.worker.start)
            p.start()

    def __call__(self, environ, start_response):
        raise NotImplementedError()
