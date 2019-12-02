import pytest

from mock import patch, Mock
from httmock import urlmatch, HTTMock

from notifications.notificationmethod import (
    QuayNotificationMethod,
    EmailMethod,
    WebhookMethod,
    FlowdockMethod,
    HipchatMethod,
    SlackMethod,
    CannotValidateNotificationMethodException,
)
from notifications.notificationevent import RepoPushEvent
from notifications.models_interface import Repository
from workers.notificationworker.notificationworker import NotificationWorker

from test.fixtures import *

from workers.notificationworker.models_pre_oci import pre_oci_model as model


def test_basic_notification_endtoend(initialized_db):
    # Ensure the public user doesn't have any notifications.
    assert not model.user_has_local_notifications("public")

    # Add a basic build notification.
    notification_uuid = model.create_notification_for_testing("public")
    event_data = {}

    # Fire off the queue processing.
    worker = NotificationWorker(None)
    worker.process_queue_item(
        {"notification_uuid": notification_uuid, "event_data": event_data,}
    )

    # Ensure the notification was handled.
    assert model.user_has_local_notifications("public")


@pytest.mark.parametrize(
    "method,method_config,netloc",
    [
        (QuayNotificationMethod, {"target": {"name": "devtable", "kind": "user"}}, None),
        (EmailMethod, {"email": "jschorr@devtable.com"}, None),
        (WebhookMethod, {"url": "http://example.com"}, "example.com"),
        (FlowdockMethod, {"flow_api_token": "sometoken"}, "api.flowdock.com"),
        (HipchatMethod, {"notification_token": "token", "room_id": "foo"}, "api.hipchat.com"),
        (SlackMethod, {"url": "http://example.com"}, "example.com"),
    ],
)
def test_notifications(method, method_config, netloc, initialized_db):
    url_hit = [False]

    @urlmatch(netloc=netloc)
    def url_handler(_, __):
        url_hit[0] = True
        return ""

    mock = Mock()

    def get_mock(*args, **kwargs):
        return mock

    with patch("notifications.notificationmethod.Message", get_mock):
        with HTTMock(url_handler):
            # Add a basic build notification.
            notification_uuid = model.create_notification_for_testing(
                "public", method_name=method.method_name(), method_config=method_config
            )
            event_data = RepoPushEvent().get_sample_data("devtable", "simple", {})

            # Fire off the queue processing.
            worker = NotificationWorker(None)
            worker.process_queue_item(
                {
                    "notification_uuid": notification_uuid,
                    "event_data": event_data,
                    "performer_data": {},
                }
            )

    if netloc is not None:
        assert url_hit[0]
