"""
List, create and manage repository events/notifications.
"""

import logging
from flask import request

from endpoints.api import (
    RepositoryParamResource,
    nickname,
    resource,
    require_repo_admin,
    log_action,
    validate_json_request,
    request_error,
    path_param,
    disallow_for_app_repositories,
    InvalidRequest,
)
from endpoints.exception import NotFound
from notifications.models_interface import Repository
from notifications.notificationevent import NotificationEvent
from notifications.notificationmethod import (
    NotificationMethod,
    CannotValidateNotificationMethodException,
)
from endpoints.api.repositorynotification_models_pre_oci import pre_oci_model as model

logger = logging.getLogger(__name__)


@resource("/v1/repository/<apirepopath:repository>/notification/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryNotificationList(RepositoryParamResource):
    """
    Resource for dealing with listing and creating notifications on a repository.
    """

    schemas = {
        "NotificationCreateRequest": {
            "type": "object",
            "description": "Information for creating a notification on a repository",
            "required": [
                "event",
                "method",
                "config",
                "eventConfig",
            ],
            "properties": {
                "event": {
                    "type": "string",
                    "description": "The event on which the notification will respond",
                },
                "method": {
                    "type": "string",
                    "description": "The method of notification (such as email or web callback)",
                },
                "config": {
                    "type": "object",
                    "description": "JSON config information for the specific method of notification",
                },
                "eventConfig": {
                    "type": "object",
                    "description": "JSON config information for the specific event of notification",
                },
                "title": {
                    "type": "string",
                    "description": "The human-readable title of the notification",
                },
            },
        },
    }

    @require_repo_admin
    @nickname("createRepoNotification")
    @disallow_for_app_repositories
    @validate_json_request("NotificationCreateRequest")
    def post(self, namespace_name, repository_name):
        parsed = request.get_json()

        method_handler = NotificationMethod.get_method(parsed["method"])
        try:
            method_handler.validate(namespace_name, repository_name, parsed["config"])
        except CannotValidateNotificationMethodException as ex:
            raise request_error(message=str(ex))

        new_notification = model.create_repo_notification(
            namespace_name,
            repository_name,
            parsed["event"],
            parsed["method"],
            parsed["config"],
            parsed["eventConfig"],
            parsed.get("title"),
        )

        log_action(
            "add_repo_notification",
            namespace_name,
            {
                "repo": repository_name,
                "namespace": namespace_name,
                "notification_id": new_notification.uuid,
                "event": new_notification.event_name,
                "method": new_notification.method_name,
            },
            repo_name=repository_name,
        )
        return new_notification.to_dict(), 201

    @require_repo_admin
    @nickname("listRepoNotifications")
    @disallow_for_app_repositories
    def get(self, namespace_name, repository_name):
        """
        List the notifications for the specified repository.
        """
        notifications = model.list_repo_notifications(namespace_name, repository_name)
        return {"notifications": [n.to_dict() for n in notifications]}


@resource("/v1/repository/<apirepopath:repository>/notification/<uuid>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("uuid", "The UUID of the notification")
class RepositoryNotification(RepositoryParamResource):
    """
    Resource for dealing with specific notifications.
    """

    @require_repo_admin
    @nickname("getRepoNotification")
    @disallow_for_app_repositories
    def get(self, namespace_name, repository_name, uuid):
        """
        Get information for the specified notification.
        """
        found = model.get_repo_notification(uuid)
        if not found:
            raise NotFound()
        return found.to_dict()

    @require_repo_admin
    @nickname("deleteRepoNotification")
    @disallow_for_app_repositories
    def delete(self, namespace_name, repository_name, uuid):
        """
        Deletes the specified notification.
        """
        deleted = model.delete_repo_notification(namespace_name, repository_name, uuid)
        if not deleted:
            raise InvalidRequest(
                "No repository notification found for: %s, %s, %s"
                % (namespace_name, repository_name, uuid)
            )

        log_action(
            "delete_repo_notification",
            namespace_name,
            {
                "repo": repository_name,
                "namespace": namespace_name,
                "notification_id": uuid,
                "event": deleted.event_name,
                "method": deleted.method_name,
            },
            repo_name=repository_name,
        )

        return "No Content", 204

    @require_repo_admin
    @nickname("resetRepositoryNotificationFailures")
    @disallow_for_app_repositories
    def post(self, namespace_name, repository_name, uuid):
        """
        Resets repository notification to 0 failures.
        """
        reset = model.reset_notification_number_of_failures(namespace_name, repository_name, uuid)
        if not reset:
            raise InvalidRequest(
                "No repository notification found for: %s, %s, %s"
                % (namespace_name, repository_name, uuid)
            )

        log_action(
            "reset_repo_notification",
            namespace_name,
            {
                "repo": repository_name,
                "namespace": namespace_name,
                "notification_id": uuid,
                "event": reset.event_name,
                "method": reset.method_name,
            },
            repo_name=repository_name,
        )

        return "No Content", 204


@resource("/v1/repository/<apirepopath:repository>/notification/<uuid>/test")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("uuid", "The UUID of the notification")
class TestRepositoryNotification(RepositoryParamResource):
    """
    Resource for queuing a test of a notification.
    """

    @require_repo_admin
    @nickname("testRepoNotification")
    @disallow_for_app_repositories
    def post(self, namespace_name, repository_name, uuid):
        """
        Queues a test notification for this repository.
        """
        test_note = model.queue_test_notification(uuid)
        if not test_note:
            raise InvalidRequest(
                "No repository notification found for: %s, %s, %s"
                % (namespace_name, repository_name, uuid)
            )

        return {}, 200
