import logging
import time
import json

import features

from app import secscan_notification_queue, secscan_api
from workers.queueworker import QueueWorker, JobException
from util.secscan.notifier import SecurityNotificationHandler, ProcessNotificationPageResult


logger = logging.getLogger(__name__)


_PROCESSING_SECONDS = 60 * 60  # 1 hour
_LAYER_LIMIT = 1000  # The number of layers to request on each page.


class SecurityNotificationWorker(QueueWorker):
    def process_queue_item(self, data):
        self.perform_notification_work(data)

    def perform_notification_work(self, data, layer_limit=_LAYER_LIMIT):
        """ Performs the work for handling a security notification as referenced by the given data
        object. Returns True on successful handling, False on non-retryable failure and raises
        a JobException on retryable failure.
    """

        notification_name = data["Name"]
        current_page = data.get("page", None)
        handler = SecurityNotificationHandler(layer_limit)

        while True:
            # Retrieve the current page of notification data from the security scanner.
            (response_data, should_retry) = secscan_api.get_notification(
                notification_name, layer_limit=layer_limit, page=current_page
            )

            # If no response, something went wrong.
            if response_data is None:
                if should_retry:
                    raise JobException()
                else:
                    # Remove the job from the API.
                    logger.error("Failed to handle security notification %s", notification_name)
                    secscan_api.mark_notification_read(notification_name)

                    # Return to mark the job as "complete", as we'll never be able to finish it.
                    return False

            # Extend processing on the queue item so it doesn't expire while we're working.
            self.extend_processing(_PROCESSING_SECONDS, json.dumps(data))

            # Process the notification data.
            notification_data = response_data["Notification"]
            result = handler.process_notification_page_data(notification_data)

            # Possible states after processing: failed to process, finished processing entirely
            # or finished processing the page.
            if result == ProcessNotificationPageResult.FAILED:
                # Something went wrong.
                raise JobException

            if result == ProcessNotificationPageResult.FINISHED_PROCESSING:
                # Mark the notification as read.
                if not secscan_api.mark_notification_read(notification_name):
                    # Return to mark the job as "complete", as we'll never be able to finish it.
                    logger.error("Failed to mark notification %s as read", notification_name)
                    return False

                # Send the generated Quay notifications.
                handler.send_notifications()
                return True

            if result == ProcessNotificationPageResult.FINISHED_PAGE:
                # Continue onto the next page.
                current_page = notification_data["NextPage"]
                continue


if __name__ == "__main__":
    if not features.SECURITY_SCANNER or not features.SECURITY_NOTIFICATIONS:
        logger.debug("Security scanner disabled; skipping SecurityNotificationWorker")
        while True:
            time.sleep(100000)

    worker = SecurityNotificationWorker(
        secscan_notification_queue,
        poll_period_seconds=30,
        reservation_seconds=30,
        retry_after_seconds=30,
    )
    worker.start()
