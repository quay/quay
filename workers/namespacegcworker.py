import logging
import time

import features

from app import app, namespace_gc_queue, all_queues
from data import model
from workers.queueworker import QueueWorker, WorkerSleepException
from util.log import logfile_path
from util.locking import GlobalLock, LockNotAcquiredException
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 60
NAMESPACE_GC_TIMEOUT = 60 * 60  # 60 minutes
LOCK_TIMEOUT_PADDING = 60  # seconds


class NamespaceGCWorker(QueueWorker):
    """
    Worker which cleans up namespaces enqueued to be GCed.
    """

    def process_queue_item(self, job_details):
        try:
            with GlobalLock(
                "LARGE_GARBAGE_COLLECTION", lock_ttl=NAMESPACE_GC_TIMEOUT + LOCK_TIMEOUT_PADDING
            ):
                self._perform_gc(job_details)
        except LockNotAcquiredException:
            logger.debug("Could not acquire global lock for garbage collection")
            raise WorkerSleepException

    def _perform_gc(self, job_details):
        logger.debug("Got namespace GC queue item: %s", job_details)
        marker_id = job_details["marker_id"]
        if not model.user.delete_namespace_via_marker(marker_id, all_queues):
            raise Exception("GC interrupted; will retry")


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    gc_worker = NamespaceGCWorker(
        namespace_gc_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=NAMESPACE_GC_TIMEOUT,
    )
    worker = GunicornWorker(__name__, app, gc_worker, features.NAMESPACE_GARBAGE_COLLECTION)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.NAMESPACE_GARBAGE_COLLECTION:
        logger.debug("Namespace garbage collection is disabled; skipping")
        while True:
            time.sleep(100000)

    logger.debug("Starting namespace GC worker")
    worker = NamespaceGCWorker(
        namespace_gc_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=NAMESPACE_GC_TIMEOUT,
    )
    worker.start()
