import logging

from datetime import timedelta, datetime

from app import app
from data.database import UseThenDisconnect
from data.queue import delete_expired
from workers.worker import Worker
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


DELETION_DATE_THRESHOLD = timedelta(days=1)
DELETION_COUNT_THRESHOLD = 50
BATCH_SIZE = 500
QUEUE_CLEANUP_FREQUENCY = app.config.get("QUEUE_CLEANUP_FREQUENCY", 60 * 60 * 24)


class QueueCleanupWorker(Worker):
    def __init__(self):
        super(QueueCleanupWorker, self).__init__()
        self.add_operation(self._cleanup_queue, QUEUE_CLEANUP_FREQUENCY)

    def _cleanup_queue(self):
        """
        Performs garbage collection on the queueitem table.
        """
        with UseThenDisconnect(app.config):
            while True:
                # Find all queue items older than the threshold (typically a week) and delete them.
                expiration_threshold = datetime.now() - DELETION_DATE_THRESHOLD
                deleted_count = delete_expired(
                    expiration_threshold, DELETION_COUNT_THRESHOLD, BATCH_SIZE
                )
                if deleted_count == 0:
                    return


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, app, QueueCleanupWorker(), True)
    return worker


if __name__ == "__main__":
    worker = QueueCleanupWorker()
    worker.start()
