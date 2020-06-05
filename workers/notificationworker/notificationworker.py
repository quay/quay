import logging

from app import notification_queue
from notifications.notificationmethod import NotificationMethod, InvalidNotificationMethodException
from notifications.notificationevent import NotificationEvent, InvalidNotificationEventException
from workers.notificationworker.models_pre_oci import pre_oci_model as model
from workers.queueworker import QueueWorker, JobException

logger = logging.getLogger(__name__)


class NotificationWorker(QueueWorker):
    def process_queue_item(self, job_details):
        notification = model.get_enabled_notification(job_details["notification_uuid"])
        if notification is None:
            return

        event_name = notification.event_name
        method_name = notification.method_name

        try:
            event_handler = NotificationEvent.get_event(event_name)
            method_handler = NotificationMethod.get_method(method_name)
        except InvalidNotificationMethodException as ex:
            logger.exception("Cannot find notification method: %s", str(ex))
            raise JobException("Cannot find notification method: %s" % str(ex))
        except InvalidNotificationEventException as ex:
            logger.exception("Cannot find notification event: %s", str(ex))
            raise JobException("Cannot find notification event: %s" % str(ex))

        if event_handler.should_perform(job_details["event_data"], notification):
            try:
                method_handler.perform(notification, event_handler, job_details)
                model.reset_number_of_failures_to_zero(notification)
            except (JobException, KeyError) as exc:
                model.increment_notification_failure_count(notification)
                raise exc


if __name__ == "__main__":
    worker = NotificationWorker(
        notification_queue, poll_period_seconds=10, reservation_seconds=30, retry_after_seconds=30
    )
    worker.start()
