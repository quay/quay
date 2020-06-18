import logging
import time

import features

from app import repository_gc_queue, all_queues
from data import model, database
from workers.queueworker import QueueWorker, WorkerSleepException
from util.log import logfile_path
from util.locking import GlobalLock, LockNotAcquiredException

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 60
REPOSITORY_GC_TIMEOUT = 60 * 15  # 15 minutes
LOCK_TIMEOUT_PADDING = 60  # seconds


class RepositoryGCWorker(QueueWorker):
    """
    Worker which cleans up repositories enqueued to be GCed.
    """

    def process_queue_item(self, job_details):
        try:
            with GlobalLock(
                "LARGE_GARBAGE_COLLECTION", lock_ttl=REPOSITORY_GC_TIMEOUT + LOCK_TIMEOUT_PADDING
            ):
                self._perform_gc(job_details)
        except LockNotAcquiredException:
            logger.debug("Could not acquire global lock for garbage collection")
            raise WorkerSleepException

    def _perform_gc(self, job_details):
        logger.debug("Got repository GC queue item: %s", job_details)
        marker_id = job_details["marker_id"]

        try:
            marker = database.DeletedRepository.get(id=marker_id)
        except database.DeletedRepository.DoesNotExist:
            logger.debug("Found no matching delete repo marker: %s", job_details)
            return

        logger.debug("Purging repository %s", marker.repository)
        if not model.gc.purge_repository(marker.repository):
            raise Exception("GC interrupted; will retry")


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.REPOSITORY_GARBAGE_COLLECTION:
        logger.info("Repository garbage collection is disabled; skipping")
        while True:
            time.sleep(100000)

    logger.debug("Starting repository GC worker")
    worker = RepositoryGCWorker(
        repository_gc_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=REPOSITORY_GC_TIMEOUT,
    )
    worker.start()
