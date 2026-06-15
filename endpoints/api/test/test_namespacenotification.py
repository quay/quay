from unittest.mock import patch

import pytest

from data import model
from endpoints.api.namespacenotification import (
    OrgNamespaceNotification,
    OrgNamespaceNotificationList,
    TestOrgNamespaceNotification,
    UserNamespaceNotification,
    UserNamespaceNotificationList,
    TestUserNamespaceNotification,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _create_notification(namespace_name, event_name="quota_warning"):
    ns_user = model.user.get_namespace_user(namespace_name)
    return model.notification.create_namespace_notification(
        ns_user,
        event_name,
        "email",
        {"email": "test@example.com"},
        {},
        title="Test Notification",
    )


class TestOrgNotificationList:
    def test_list_empty(self, app):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, OrgNamespaceNotificationList, "GET", {"orgname": "buynlarge"}, None, 200
            )
            assert resp.json["notifications"] == []

    def test_list_with_notifications(self, app):
        notif = _create_notification("buynlarge")
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, OrgNamespaceNotificationList, "GET", {"orgname": "buynlarge"}, None, 200
            )
            notifications = resp.json["notifications"]
            assert len(notifications) >= 1
            uuids = [n["uuid"] for n in notifications]
            assert notif.uuid in uuids
        notif.delete_instance()

    def test_create_notification(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "quota_warning",
                "method": "email",
                "config": {"email": "test@example.com"},
                "eventConfig": {},
                "title": "Quota Warning Alert",
            }
            resp = conduct_api_call(
                cl, OrgNamespaceNotificationList, "POST", {"orgname": "buynlarge"}, body, 201
            )
            data = resp.json
            assert data["event"] == "quota_warning"
            assert data["method"] == "email"
            assert data["title"] == "Quota Warning Alert"
            assert "uuid" in data

            model.notification.delete_namespace_notification("buynlarge", data["uuid"])

    def test_create_quota_error_notification(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "quota_error",
                "method": "email",
                "config": {"email": "admin@example.com"},
                "eventConfig": {},
            }
            resp = conduct_api_call(
                cl, OrgNamespaceNotificationList, "POST", {"orgname": "buynlarge"}, body, 201
            )
            data = resp.json
            assert data["event"] == "quota_error"

            model.notification.delete_namespace_notification("buynlarge", data["uuid"])

    def test_create_invalid_event(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "repo_push",
                "method": "email",
                "config": {"email": "test@example.com"},
                "eventConfig": {},
            }
            conduct_api_call(
                cl, OrgNamespaceNotificationList, "POST", {"orgname": "buynlarge"}, body, 400
            )

    def test_create_invalid_org(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "quota_warning",
                "method": "email",
                "config": {"email": "test@example.com"},
                "eventConfig": {},
            }
            conduct_api_call(
                cl,
                OrgNamespaceNotificationList,
                "POST",
                {"orgname": "nonexistent_org_xyz"},
                body,
                404,
            )

    def test_unauthorized_user(self, app):
        with client_with_identity("freshuser", app) as cl:
            conduct_api_call(
                cl, OrgNamespaceNotificationList, "GET", {"orgname": "buynlarge"}, None, 403
            )


class TestOrgNotification:
    def test_get_notification(self, app):
        notif = _create_notification("buynlarge")
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                OrgNamespaceNotification,
                "GET",
                {"orgname": "buynlarge", "uuid": notif.uuid},
                None,
                200,
            )
            assert resp.json["uuid"] == notif.uuid
            assert resp.json["event"] == "quota_warning"
        notif.delete_instance()

    def test_get_nonexistent(self, app):
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrgNamespaceNotification,
                "GET",
                {"orgname": "buynlarge", "uuid": "nonexistent-uuid"},
                None,
                404,
            )

    def test_delete_notification(self, app):
        notif = _create_notification("buynlarge")
        uuid = notif.uuid
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrgNamespaceNotification,
                "DELETE",
                {"orgname": "buynlarge", "uuid": uuid},
                None,
                204,
            )

            # Verify deleted
            conduct_api_call(
                cl,
                OrgNamespaceNotification,
                "GET",
                {"orgname": "buynlarge", "uuid": uuid},
                None,
                404,
            )

    def test_reset_failures(self, app):
        notif = _create_notification("buynlarge")
        model.notification.increment_namespace_notification_failure_count(notif.uuid)
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                OrgNamespaceNotification,
                "POST",
                {"orgname": "buynlarge", "uuid": notif.uuid},
                None,
                204,
            )
        notif.delete_instance()


class TestOrgNotificationTest:
    def test_queue_test_notification(self, app):
        notif = _create_notification("buynlarge")
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                TestOrgNamespaceNotification,
                "POST",
                {"orgname": "buynlarge", "uuid": notif.uuid},
                None,
                200,
            )
        notif.delete_instance()


class TestUserNotificationList:
    def test_list_empty(self, app):
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl, UserNamespaceNotificationList, "GET", {}, None, 200
            )
            assert resp.json["notifications"] == []

    def test_create_notification(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "quota_warning",
                "method": "email",
                "config": {"email": "user@example.com"},
                "eventConfig": {},
                "title": "User Quota Warning",
            }
            resp = conduct_api_call(
                cl, UserNamespaceNotificationList, "POST", {}, body, 201
            )
            data = resp.json
            assert data["event"] == "quota_warning"
            assert data["method"] == "email"
            assert data["title"] == "User Quota Warning"

            model.notification.delete_namespace_notification("devtable", data["uuid"])

    def test_create_invalid_event(self, app):
        with client_with_identity("devtable", app) as cl:
            body = {
                "event": "build_success",
                "method": "email",
                "config": {"email": "user@example.com"},
                "eventConfig": {},
            }
            conduct_api_call(
                cl, UserNamespaceNotificationList, "POST", {}, body, 400
            )


class TestUserNotification:
    def test_get_notification(self, app):
        notif = _create_notification("devtable")
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                UserNamespaceNotification,
                "GET",
                {"uuid": notif.uuid},
                None,
                200,
            )
            assert resp.json["uuid"] == notif.uuid
        notif.delete_instance()

    def test_get_other_users_notification(self, app):
        notif = _create_notification("freshuser")
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                UserNamespaceNotification,
                "GET",
                {"uuid": notif.uuid},
                None,
                404,
            )
        notif.delete_instance()

    def test_delete_notification(self, app):
        notif = _create_notification("devtable")
        uuid = notif.uuid
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                UserNamespaceNotification,
                "DELETE",
                {"uuid": uuid},
                None,
                204,
            )

    def test_reset_failures(self, app):
        notif = _create_notification("devtable")
        model.notification.increment_namespace_notification_failure_count(notif.uuid)
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                UserNamespaceNotification,
                "POST",
                {"uuid": notif.uuid},
                None,
                204,
            )
        notif.delete_instance()


class TestAuditLogging:
    def test_create_logs_action(self, app):
        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacenotification.log_action") as mock_log:
                body = {
                    "event": "quota_warning",
                    "method": "email",
                    "config": {"email": "test@example.com"},
                    "eventConfig": {},
                }
                resp = conduct_api_call(
                    cl,
                    OrgNamespaceNotificationList,
                    "POST",
                    {"orgname": "buynlarge"},
                    body,
                    201,
                )

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "create_namespace_notification"
                assert call_args[0][1] == "buynlarge"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "buynlarge"
                assert metadata["event"] == "quota_warning"
                assert metadata["method"] == "email"

                model.notification.delete_namespace_notification(
                    "buynlarge", resp.json["uuid"]
                )

    def test_delete_logs_action(self, app):
        notif = _create_notification("buynlarge")
        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacenotification.log_action") as mock_log:
                conduct_api_call(
                    cl,
                    OrgNamespaceNotification,
                    "DELETE",
                    {"orgname": "buynlarge", "uuid": notif.uuid},
                    None,
                    204,
                )

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "delete_namespace_notification"
                assert call_args[0][1] == "buynlarge"
