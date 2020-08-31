import json

from data import model
from data.database import RepositoryNotification
from workers.notificationworker.models_interface import (
    NotificationWorkerDataInterface,
    Notification,
    Repository,
)


def notification(notification_row):
    """
    Converts the given notification row into a notification tuple.
    """
    return Notification(
        uuid=notification_row.uuid,
        event_name=RepositoryNotification.event.get_name(notification_row.event_id),
        method_name=RepositoryNotification.method.get_name(notification_row.method_id),
        event_config_dict=json.loads(notification_row.event_config_json or "{}"),
        method_config_dict=json.loads(notification_row.config_json or "{}"),
        repository=Repository(
            notification_row.repository.namespace_user.username, notification_row.repository.name
        ),
    )


class PreOCIModel(NotificationWorkerDataInterface):
    def get_enabled_notification(self, notification_uuid):
        try:
            notification_row = model.notification.get_enabled_notification(notification_uuid)
        except model.InvalidNotificationException:
            return None

        return notification(notification_row)

    def reset_number_of_failures_to_zero(self, notification):
        model.notification.reset_notification_number_of_failures(
            notification.repository.namespace_name, notification.repository.name, notification.uuid
        )

    def increment_notification_failure_count(self, notification):
        model.notification.increment_notification_failure_count(notification.uuid)

    def create_notification_for_testing(
        self, target_username, method_name="quay_notification", method_config=None
    ):
        repo = model.repository.get_repository("devtable", "simple")
        method_data = method_config or {
            "target": {
                "kind": "user",
                "name": target_username,
            }
        }
        notification = model.notification.create_repo_notification(
            repo, "repo_push", method_name, method_data, {}
        )
        return notification.uuid

    def user_has_local_notifications(self, target_username):
        user = model.user.get_namespace_user(target_username)
        return bool(list(model.notification.list_notifications(user)))


pre_oci_model = PreOCIModel()
