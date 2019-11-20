import logging

from app import namespace_gc_queue, all_queues
from data import model
from workers.queueworker import QueueWorker
from util.log import logfile_path

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 60
NAMESPACE_GC_TIMEOUT = 60 * 15  # 15 minutes


class NamespaceGCWorker(QueueWorker):
    """ Worker which cleans up namespaces enqueued to be GCed.
  """

    def process_queue_item(self, job_details):
        logger.debug("Got namespace GC queue item: %s", job_details)
        marker_id = job_details["marker_id"]
        model.user.delete_namespace_via_marker(marker_id, all_queues)


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    logger.debug("Starting namespace GC worker")
    worker = NamespaceGCWorker(
        namespace_gc_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=NAMESPACE_GC_TIMEOUT,
    )
    worker.start()
