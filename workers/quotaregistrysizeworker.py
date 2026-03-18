import logging.config

import features
from app import app
from data.model.quota import calculate_registry_size
from util.locking import GlobalLock
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)
POLL_PERIOD = app.config.get("QUOTA_REGISTRY_SIZE_POLL_PERIOD", 60)


class QuotaRegistrySizeWorker(Worker):
    def __init__(self):
        super(QuotaRegistrySizeWorker, self).__init__()
        self.add_operation(self._calculate_registry_size, POLL_PERIOD)

    def _calculate_registry_size(self):
        calculate_registry_size()


def create_gunicorn_worker():
    worker = GunicornWorker(__name__, app, QuotaRegistrySizeWorker(), features.QUOTA_MANAGEMENT)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = QuotaRegistrySizeWorker()
    worker.start()
