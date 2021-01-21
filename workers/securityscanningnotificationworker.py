import logging
import time

import features

from app import app, storage, secscan_notification_queue, secscan_model, registry_model
from data.secscan_model.datatypes import PaginatedNotificationStatus
from notifications import notification_batch
from workers.queueworker import QueueWorker, JobException
from util.log import logfile_path
from util.secscan import PRIORITY_LEVELS
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


_POLL_PERIOD_SECONDS = 60
_PROCESSING_SECONDS_EXPIRATION = 60 * 60  # 1 hour
TAG_LIMIT = 100  # tags


class SecurityScanningNotificationWorker(QueueWorker):
    """
    Worker which reads queued notifications from the scanning system and emits notifications
    for repositories.
    """

    _secscan_model = secscan_model

    def process_queue_item(self, job_details):
        self._perform_notification_worker(job_details)

    def _perform_notification_worker(self, job_details):
        """
        Performs the work for handling a security notification as referenced by the given data
        object.

        Returns True on successful handling, False on non-retryable failure and raises a
        JobException on retryable failure.
        """

        logger.debug("Got security scanning notification queue item: %s", job_details)

        notification_id = job_details["notification_id"]
        page_index = job_details.get("current_page_index", None)
        while True:
            page_result = self._secscan_model.lookup_notification_page(notification_id, page_index)
            if page_result is None:
                logger.warning("Got unsupported for notification page")
                return

            logger.debug(
                "Got page result for notification %s: %s", notification_id, page_result.status
            )
            if page_result.status == PaginatedNotificationStatus.RETRYABLE_ERROR:
                logger.warning("Got notification page issue; will retry in the future")
                raise JobException()

            if page_result.status == PaginatedNotificationStatus.FATAL_ERROR:
                logger.error("Got fatal error for notification %s; terminating", notification_id)
                return

            # Update the job details with the current page index and extend processing to ensure
            # we do not timeout during the notification handling.
            job_details["current_page_index"] = page_index
            self.extend_processing(_PROCESSING_SECONDS_EXPIRATION, job_details)

            with notification_batch() as spawn_notification:
                # Process the notification page into notifications.
                for updated_vuln_info in self._secscan_model.process_notification_page(
                    page_result.data
                ):
                    vulnerability = updated_vuln_info.vulnerability

                    # Find all manifests in repositories with configured security notifications that
                    # match that of the vulnerability.
                    for manifest in registry_model.find_manifests_for_sec_notification(
                        updated_vuln_info.manifest_digest
                    ):
                        # Filter any repositories where the notification level is below that of
                        # the vulnerability.
                        found_severity = PRIORITY_LEVELS.get(
                            vulnerability.Severity, PRIORITY_LEVELS["Unknown"]
                        )

                        lowest_severity = PRIORITY_LEVELS["Critical"]
                        for severity_name in registry_model.lookup_secscan_notification_severities(
                            manifest.repository
                        ):
                            severity = PRIORITY_LEVELS.get(
                                severity_name,
                                PRIORITY_LEVELS["Critical"],
                            )

                            if lowest_severity["score"] > severity["score"]:
                                lowest_severity = severity

                        if found_severity["score"] < lowest_severity["score"]:
                            continue

                        # Issue a notification for the repository.
                        tag_names = list(registry_model.tag_names_for_manifest(manifest, TAG_LIMIT))
                        if tag_names:
                            event_data = {
                                "tags": list(tag_names),
                                "vulnerability": {
                                    "id": vulnerability.Name,
                                    "description": vulnerability.Description,
                                    "link": vulnerability.Link,
                                    "priority": found_severity["title"],
                                    "has_fix": bool(vulnerability.FixedBy),
                                },
                            }

                            spawn_notification(
                                manifest.repository, "vulnerability_found", event_data
                            )

            # Mark the job as having completed the page.
            page_index = page_result.next_page_index
            if page_index is None:
                logger.debug("Completed processing of notification %s", notification_id)
                attempt_count = 5
                while not self._secscan_model.mark_notification_handled(notification_id):
                    attempt_count -= 1
                    if attempt_count == 0:
                        break

                return

            job_details["current_page_index"] = page_index
            self.extend_processing(_PROCESSING_SECONDS_EXPIRATION, job_details)


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    feature_flag = features.SECURITY_SCANNER and features.SECURITY_NOTIFICATIONS
    note_worker = SecurityScanningNotificationWorker(
        secscan_notification_queue, poll_period_seconds=_POLL_PERIOD_SECONDS
    )
    worker = GunicornWorker(__name__, app, note_worker, feature_flag)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.SECURITY_SCANNER:
        logger.debug("Security scanner disabled; sleeping")
        while True:
            time.sleep(10000)

    if not features.SECURITY_NOTIFICATIONS:
        logger.debug("Security scanner notifications disabled; sleeping")
        while True:
            time.sleep(10000)

    logger.debug("Starting security scanning notification worker")
    worker = SecurityScanningNotificationWorker(
        secscan_notification_queue, poll_period_seconds=_POLL_PERIOD_SECONDS
    )
    worker.start()
