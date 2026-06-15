import json
import logging

from flask import request

import features
from auth.auth_context import get_authenticated_user
from auth.permissions import AdministerOrganizationPermission, SuperUserPermission
from data import model
from data.model import InvalidNotificationException
from endpoints.api import (
    ApiResource,
    InvalidRequest,
    log_action,
    nickname,
    path_param,
    request_error,
    require_user_admin,
    resource,
    show_if,
    validate_json_request,
)
from endpoints.exception import NotFound, Unauthorized
from notifications import build_namespace_event_data, build_notification_data
from notifications.notificationevent import NotificationEvent
from notifications.notificationmethod import (
    InvalidNotificationMethodException,
    NotificationMethod,
)

logger = logging.getLogger(__name__)

VALID_NAMESPACE_EVENTS = {"quota_warning", "quota_error"}


def _notification_view(notification):
    try:
        config = json.loads(notification.config_json)
    except ValueError:
        config = {}

    try:
        event_config = json.loads(notification.event_config_json or "{}")
    except ValueError:
        event_config = {}

    return {
        "uuid": notification.uuid,
        "title": notification.title,
        "event": notification.event.name,
        "method": notification.method.name,
        "config": config,
        "event_config": event_config,
        "number_of_failures": notification.number_of_failures,
    }


def _check_org_admin(orgname):
    permission = AdministerOrganizationPermission(orgname)
    if permission.can() or SuperUserPermission().can():
        return
    raise Unauthorized()


def _validate_create_request(parsed):
    event_name = parsed["event"]
    if event_name not in VALID_NAMESPACE_EVENTS:
        raise request_error(
            message="Invalid event '%s'. Must be one of: %s"
            % (event_name, ", ".join(sorted(VALID_NAMESPACE_EVENTS)))
        )

    try:
        NotificationMethod.get_method(parsed["method"])
    except InvalidNotificationMethodException:
        raise request_error(message="Unknown notification method '%s'" % parsed["method"])


def _get_or_404(uuid):
    try:
        return model.notification.get_namespace_notification(uuid)
    except InvalidNotificationException:
        raise NotFound()


@resource("/v1/organization/<orgname>/notifications")
@show_if(features.QUOTA_NOTIFICATIONS)
@path_param("orgname", "The name of the organization")
class OrgNamespaceNotificationList(ApiResource):
    schemas = {
        "NotificationCreateRequest": {
            "type": "object",
            "description": "Information for creating a namespace notification",
            "required": ["event", "method", "config", "eventConfig"],
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

    @nickname("listOrgNotifications")
    def get(self, orgname):
        _check_org_admin(orgname)

        try:
            model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        notifications = model.notification.list_namespace_notifications(orgname)
        return {"notifications": [_notification_view(n) for n in notifications]}

    @nickname("createOrgNotification")
    @validate_json_request("NotificationCreateRequest")
    def post(self, orgname):
        _check_org_admin(orgname)

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        parsed = request.get_json()
        _validate_create_request(parsed)

        new_notification = model.notification.create_namespace_notification(
            org,
            parsed["event"],
            parsed["method"],
            parsed["config"],
            parsed["eventConfig"],
            parsed.get("title"),
        )

        log_action(
            "create_namespace_notification",
            orgname,
            {
                "namespace": orgname,
                "notification_id": new_notification.uuid,
                "event": new_notification.event.name,
                "method": new_notification.method.name,
            },
        )
        return _notification_view(new_notification), 201


@resource("/v1/organization/<orgname>/notifications/<uuid>")
@show_if(features.QUOTA_NOTIFICATIONS)
@path_param("orgname", "The name of the organization")
@path_param("uuid", "The UUID of the notification")
class OrgNamespaceNotification(ApiResource):
    @nickname("getOrgNotification")
    def get(self, orgname, uuid):
        _check_org_admin(orgname)
        found = _get_or_404(uuid)
        if found.namespace.username != orgname:
            raise NotFound()
        return _notification_view(found)

    @nickname("deleteOrgNotification")
    def delete(self, orgname, uuid):
        _check_org_admin(orgname)
        try:
            deleted = model.notification.delete_namespace_notification(orgname, uuid)
        except InvalidNotificationException:
            raise NotFound()

        log_action(
            "delete_namespace_notification",
            orgname,
            {
                "namespace": orgname,
                "notification_id": uuid,
                "event": deleted.event.name,
                "method": deleted.method.name,
            },
        )
        return "No Content", 204

    @nickname("resetOrgNotificationFailures")
    def post(self, orgname, uuid):
        _check_org_admin(orgname)
        reset = model.notification.reset_namespace_notification_number_of_failures(orgname, uuid)
        if not reset:
            raise NotFound()

        log_action(
            "reset_namespace_notification",
            orgname,
            {
                "namespace": orgname,
                "notification_id": uuid,
                "event": reset.event.name,
                "method": reset.method.name,
            },
        )
        return "No Content", 204


@resource("/v1/organization/<orgname>/notifications/<uuid>/test")
@show_if(features.QUOTA_NOTIFICATIONS)
@path_param("orgname", "The name of the organization")
@path_param("uuid", "The UUID of the notification")
class TestOrgNamespaceNotification(ApiResource):
    @nickname("testOrgNotification")
    def post(self, orgname, uuid):
        _check_org_admin(orgname)
        found = _get_or_404(uuid)
        if found.namespace.username != orgname:
            raise NotFound()

        event_config = json.loads(found.event_config_json or "{}")
        event_info = NotificationEvent.get_event(found.event.name)
        sample_data = event_info.get_sample_data(orgname, None, event_config)
        notification_data = build_notification_data(found, sample_data)

        from app import notification_queue

        notification_queue.put(
            [orgname, found.uuid, found.event.name],
            json.dumps(notification_data),
        )
        return {}, 200


@resource("/v1/user/notifications")
@show_if(features.QUOTA_NOTIFICATIONS)
class UserNamespaceNotificationList(ApiResource):
    schemas = {
        "NotificationCreateRequest": {
            "type": "object",
            "description": "Information for creating a namespace notification",
            "required": ["event", "method", "config", "eventConfig"],
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

    @require_user_admin()
    @nickname("listUserNamespaceNotifications")
    def get(self):
        user = get_authenticated_user()
        notifications = model.notification.list_namespace_notifications(user.username)
        return {"notifications": [_notification_view(n) for n in notifications]}

    @require_user_admin()
    @nickname("createUserNamespaceNotification")
    @validate_json_request("NotificationCreateRequest")
    def post(self):
        user = get_authenticated_user()
        parsed = request.get_json()
        _validate_create_request(parsed)

        new_notification = model.notification.create_namespace_notification(
            user,
            parsed["event"],
            parsed["method"],
            parsed["config"],
            parsed["eventConfig"],
            parsed.get("title"),
        )

        log_action(
            "create_namespace_notification",
            user.username,
            {
                "namespace": user.username,
                "notification_id": new_notification.uuid,
                "event": new_notification.event.name,
                "method": new_notification.method.name,
            },
        )
        return _notification_view(new_notification), 201


@resource("/v1/user/notifications/<uuid>")
@show_if(features.QUOTA_NOTIFICATIONS)
@path_param("uuid", "The UUID of the notification")
class UserNamespaceNotification(ApiResource):
    @require_user_admin()
    @nickname("getUserNamespaceNotification")
    def get(self, uuid):
        user = get_authenticated_user()
        found = _get_or_404(uuid)
        if found.namespace.username != user.username:
            raise NotFound()
        return _notification_view(found)

    @require_user_admin()
    @nickname("deleteUserNamespaceNotification")
    def delete(self, uuid):
        user = get_authenticated_user()
        try:
            deleted = model.notification.delete_namespace_notification(user.username, uuid)
        except InvalidNotificationException:
            raise NotFound()

        log_action(
            "delete_namespace_notification",
            user.username,
            {
                "namespace": user.username,
                "notification_id": uuid,
                "event": deleted.event.name,
                "method": deleted.method.name,
            },
        )
        return "No Content", 204

    @require_user_admin()
    @nickname("resetUserNamespaceNotificationFailures")
    def post(self, uuid):
        user = get_authenticated_user()
        reset = model.notification.reset_namespace_notification_number_of_failures(
            user.username, uuid
        )
        if not reset:
            raise NotFound()

        log_action(
            "reset_namespace_notification",
            user.username,
            {
                "namespace": user.username,
                "notification_id": uuid,
                "event": reset.event.name,
                "method": reset.method.name,
            },
        )
        return "No Content", 204


@resource("/v1/user/notifications/<uuid>/test")
@show_if(features.QUOTA_NOTIFICATIONS)
@path_param("uuid", "The UUID of the notification")
class TestUserNamespaceNotification(ApiResource):
    @require_user_admin()
    @nickname("testUserNamespaceNotification")
    def post(self, uuid):
        user = get_authenticated_user()
        found = _get_or_404(uuid)
        if found.namespace.username != user.username:
            raise NotFound()

        event_config = json.loads(found.event_config_json or "{}")
        event_info = NotificationEvent.get_event(found.event.name)
        sample_data = event_info.get_sample_data(user.username, None, event_config)
        notification_data = build_notification_data(found, sample_data)

        from app import notification_queue

        notification_queue.put(
            [user.username, found.uuid, found.event.name],
            json.dumps(notification_data),
        )
        return {}, 200
