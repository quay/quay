import logging
import time

from workers.gunicorn_worker import GunicornWorker
from app import app, storage, chunk_cleanup_queue
from workers.queueworker import QueueWorker, JobException
from util.log import logfile_path

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 10


class ChunkCleanupWorker(QueueWorker):
    """
    Worker which cleans up chunks enqueued by the storage engine(s).

    This is typically used to cleanup empty chunks which are no longer needed.
    """

    def process_queue_item(self, job_details):
        logger.debug("Got chunk cleanup queue item: %s", job_details)
        storage_location = job_details["location"]
        storage_path = job_details["path"]

        if not storage.exists([storage_location], storage_path):
            logger.debug("Chunk already deleted")
            return

        try:
            storage.remove([storage_location], storage_path)
        except IOError:
            raise JobException()


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    engines = set(
        [config[0] for config in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG", {}).values())]
    )
    feature_flag = "SwiftStorage" in engines
    worker = GunicornWorker(
        __name__,
        app,
        ChunkCleanupWorker(chunk_cleanup_queue, poll_period_seconds=POLL_PERIOD_SECONDS),
        feature_flag,
    )
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    engines = set(
        [config[0] for config in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG", {}).values())]
    )
    if "SwiftStorage" not in engines:
        logger.debug("Swift storage not detected; sleeping")
        while True:
            time.sleep(10000)

    logger.debug("Starting chunk cleanup worker")
    worker = ChunkCleanupWorker(chunk_cleanup_queue, poll_period_seconds=POLL_PERIOD_SECONDS)
    worker.start()
