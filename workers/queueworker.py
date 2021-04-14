import logging
import json
import time

from threading import Event, Lock

from app import app
from data.database import CloseForLongOperation
from workers.worker import Worker


logger = logging.getLogger(__name__)

QUEUE_WORKER_SLEEP_DURATION = 5


class JobException(Exception):
    """
    A job exception is an exception that is caused by something being malformed in the job.

    When a worker raises this exception the job will be terminated and the retry will not be
    returned to the queue.
    """

    pass


class WorkerUnhealthyException(Exception):
    """
    When this exception is raised, the worker is no longer healthy and will not accept any more
    work.

    When this is raised while processing a queue item, the item should be returned to the queue
    along with another retry.
    """

    pass


class WorkerSleepException(Exception):
    """
    When this exception is raised, the worker is told to go to sleep, as another worker is doing
    work.

    When this is raised while processing a queue item, the item should be returned to the queue
    along with another retry.
    """

    pass


class QueueWorker(Worker):
    def __init__(
        self,
        queue,
        poll_period_seconds=30,
        reservation_seconds=300,
        watchdog_period_seconds=60,
        retry_after_seconds=300,
    ):
        super(QueueWorker, self).__init__()

        self._poll_period_seconds = poll_period_seconds
        self._reservation_seconds = reservation_seconds
        self._watchdog_period_seconds = watchdog_period_seconds
        self._retry_after_seconds = retry_after_seconds
        self._stop = Event()
        self._terminated = Event()
        self._queue = queue
        self._current_item_lock = Lock()
        self.current_queue_item = None

        # Add the various operations.
        self.add_operation(self.poll_queue, self._poll_period_seconds)
        self.add_operation(
            self.update_queue_metrics, app.config["QUEUE_WORKER_METRICS_REFRESH_SECONDS"]
        )
        self.add_operation(self.run_watchdog, self._watchdog_period_seconds)

    def process_queue_item(self, job_details):
        """
        Processes the work for the given job.

        If the job fails and should be retried, this method should raise a WorkerUnhealthyException.
        If the job should be marked as permanently failed, it should raise a JobException.
        Otherwise, a successful return of this method will remove the job from the queue as
        completed.
        """
        raise NotImplementedError("Workers must implement run.")

    def watchdog(self):
        """
        Function that gets run once every watchdog_period_seconds.
        """
        pass

    def extend_processing(self, seconds_from_now, updated_data=None):
        with self._current_item_lock:
            if self.current_queue_item is not None:
                self._queue.extend_processing(
                    self.current_queue_item, seconds_from_now, updated_data=updated_data
                )

    def run_watchdog(self):
        logger.debug("Running watchdog.")
        try:
            self.watchdog()
        except WorkerUnhealthyException as exc:
            logger.error(
                "The worker has encountered an error via watchdog and will not take new jobs"
            )
            logger.error(str(exc))
            self.mark_current_incomplete(restore_retry=True)
            self._stop.set()

    def poll_queue(self):
        logger.debug("Getting work item from queue.")

        with self._current_item_lock:
            self.current_queue_item = self._queue.get(processing_time=self._reservation_seconds)

        while True:
            # Retrieve the current item in the queue over which to operate. We do so under
            # a lock to make sure we are always retrieving an item when in a healthy state.
            current_queue_item = None
            with self._current_item_lock:
                current_queue_item = self.current_queue_item
                if current_queue_item is None:
                    break

            logger.debug("Queue gave us some work: %s", current_queue_item.body)
            job_details = json.loads(current_queue_item.body)

            try:
                with CloseForLongOperation(app.config):
                    self.process_queue_item(job_details)

                self.mark_current_complete()

            except JobException as jex:
                logger.warning("An error occurred processing request: %s", current_queue_item.body)
                logger.warning("Job exception: %s", jex)
                self.mark_current_incomplete(restore_retry=False)

            except WorkerSleepException as exc:
                logger.debug("Worker has been requested to go to sleep")
                self.mark_current_incomplete(restore_retry=True)
                time.sleep(QUEUE_WORKER_SLEEP_DURATION)

            except WorkerUnhealthyException as exc:
                logger.error(
                    "The worker has encountered an error via the job and will not take new jobs"
                )
                logger.error(str(exc))
                self.mark_current_incomplete(restore_retry=True)
                self._stop.set()

            if not self._stop.is_set():
                with self._current_item_lock:
                    self.current_queue_item = self._queue.get(
                        processing_time=self._reservation_seconds
                    )

        if not self._stop.is_set():
            logger.debug("No more work.")

    def update_queue_metrics(self):
        self._queue.update_metrics()

    def mark_current_incomplete(self, restore_retry=False):
        with self._current_item_lock:
            if self.current_queue_item is not None:
                self._queue.incomplete(
                    self.current_queue_item,
                    restore_retry=restore_retry,
                    retry_after=self._retry_after_seconds,
                )
                self.current_queue_item = None

    def mark_current_complete(self):
        with self._current_item_lock:
            if self.current_queue_item is not None:
                self._queue.complete(self.current_queue_item)
                self.current_queue_item = None

    def ungracefully_terminated(self):
        # Give back the retry that we took for this queue item so that if it were down to zero
        # retries it will still be picked up by another worker
        self.mark_current_incomplete()
