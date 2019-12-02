import json

from app import notification_queue
from data import model
from data.model import InvalidNotificationException
from endpoints.api.repositorynotification_models_interface import (
    RepoNotificationInterface,
    RepositoryNotification,
)
from notifications import build_notification_data
from notifications.notificationevent import NotificationEvent


class RepoNotificationPreOCIModel(RepoNotificationInterface):
    def create_repo_notification(
        self,
        namespace_name,
        repository_name,
        event_name,
        method_name,
        method_config,
        event_config,
        title=None,
    ):
        repository = model.repository.get_repository(namespace_name, repository_name)
        return self._notification(
            model.notification.create_repo_notification(
                repository, event_name, method_name, method_config, event_config, title
            )
        )

    def list_repo_notifications(self, namespace_name, repository_name, event_name=None):
        return [
            self._notification(n)
            for n in model.notification.list_repo_notifications(
                namespace_name, repository_name, event_name
            )
        ]

    def get_repo_notification(self, uuid):
        try:
            found = model.notification.get_repo_notification(uuid)
        except InvalidNotificationException:
            return None
        return self._notification(found)

    def delete_repo_notification(self, namespace_name, repository_name, uuid):
        try:
            found = model.notification.delete_repo_notification(
                namespace_name, repository_name, uuid
            )
        except InvalidNotificationException:
            return None
        return self._notification(found)

    def reset_notification_number_of_failures(self, namespace_name, repository_name, uuid):
        return self._notification(
            model.notification.reset_notification_number_of_failures(
                namespace_name, repository_name, uuid
            )
        )

    def queue_test_notification(self, uuid):
        try:
            notification = model.notification.get_repo_notification(uuid)
        except InvalidNotificationException:
            return None

        event_config = json.loads(notification.event_config_json or "{}")
        event_info = NotificationEvent.get_event(notification.event.name)
        sample_data = event_info.get_sample_data(
            notification.repository.namespace_user.username,
            notification.repository.name,
            event_config,
        )
        notification_data = build_notification_data(notification, sample_data)
        notification_queue.put(
            [
                notification.repository.namespace_user.username,
                notification.uuid,
                notification.event.name,
            ],
            json.dumps(notification_data),
        )
        return self._notification(notification)

    def _notification(self, notification):
        if not notification:
            return None

        return RepositoryNotification(
            uuid=notification.uuid,
            title=notification.title,
            event_name=notification.event.name,
            method_name=notification.method.name,
            config_json=notification.config_json,
            event_config_json=notification.event_config_json,
            number_of_failures=notification.number_of_failures,
        )


pre_oci_model = RepoNotificationPreOCIModel()
