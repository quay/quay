import json

import pytest
from httmock import HTTMock, urlmatch
from mock import Mock, patch

from data import model
from notifications.models_interface import Notification, Repository
from notifications.notificationevent import NotificationEvent
from notifications.notificationmethod import (
    CannotValidateNotificationMethodException,
    EmailMethod,
    FlowdockMethod,
    HipchatMethod,
    QuayNotificationMethod,
    SlackMethod,
    WebhookMethod,
)
from test.fixtures import *


class TestSlackFormatting:
    def test_bold_tags_have_surrounding_spaces(self):
        method = SlackMethod()
        html = (
            "Namespace <b>quayqe</b> storage usage has\n" "<b>exceeded</b> its quota limit (110%)."
        )
        result = method.format_for_slack(html)
        assert "has *exceeded*" in result
        assert "has*exceeded*" not in result

    def test_bold_namespace_has_surrounding_spaces(self):
        method = SlackMethod()
        html = "Namespace <b>quayqe</b> storage usage has reached\n<b>70%</b> of its quota limit."
        result = method.format_for_slack(html)
        assert "*quayqe*" in result
        assert "reached *70%*" in result
        assert "reached*70%*" not in result

    def test_br_tags_become_newlines(self):
        method = SlackMethod()
        html = "line one<br>line two"
        result = method.format_for_slack(html)
        assert result == "line one\nline two"

    def test_existing_templates_unchanged(self):
        method = SlackMethod()
        html = '<a href="https://quay.io">link</a> and <i>italic</i>'
        result = method.format_for_slack(html)
        assert "<https://quay.io|link>" in result
        assert "_italic_" in result


def assert_validated(method, method_config, error_message, namespace_name, repo_name):
    if error_message is None:
        method.validate(namespace_name, repo_name, method_config)
    else:
        with pytest.raises(CannotValidateNotificationMethodException) as ipe:
            method.validate(namespace_name, repo_name, method_config)
        assert str(ipe.value) == error_message


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing target"),
        ({"target": {"name": "invaliduser", "kind": "user"}}, "Unknown user invaliduser"),
        ({"target": {"name": "invalidorg", "kind": "org"}}, "Unknown organization invalidorg"),
        ({"target": {"name": "invalidteam", "kind": "team"}}, "Unknown team invalidteam"),
        ({"target": {"name": "devtable", "kind": "user"}}, None),
        ({"target": {"name": "buynlarge", "kind": "org"}}, None),
        ({"target": {"name": "owners", "kind": "team"}}, None),
    ],
)
def test_validate_quay_notification(method_config, error_message, initialized_db):
    method = QuayNotificationMethod()
    assert_validated(method, method_config, error_message, "buynlarge", "orgrepo")


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing e-mail address"),
        (
            {"email": "a@b.com"},
            "The specified e-mail address is not authorized to receive "
            "notifications for this repository",
        ),
        ({"email": "jschorr@devtable.com"}, None),
    ],
)
def test_validate_email(method_config, error_message, initialized_db):
    method = EmailMethod()
    assert_validated(method, method_config, error_message, "devtable", "simple")


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing webhook URL"),
        ({"url": "telnet://example.com"}, "Invalid webhook URL"),
        ({"url": "http://example.com"}, None),
        ({"url": "http://localhost/"}, "Invalid webhook URL"),
        ({"url": "http://localhost:5000/"}, "Invalid webhook URL"),
        ({"url": "https://127.0.0.1:5000/"}, "Invalid webhook URL"),
    ],
)
def test_validate_webhook(method_config, error_message, initialized_db):
    method = WebhookMethod()
    assert_validated(method, method_config, error_message, "devtable", "simple")


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing Flowdock API Token"),
        ({"flow_api_token": "sometoken"}, None),
    ],
)
def test_validate_flowdock(method_config, error_message, initialized_db):
    method = FlowdockMethod()
    assert_validated(method, method_config, error_message, "devtable", "simple")


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing Hipchat Room Notification Token"),
        ({"notification_token": "sometoken"}, "Missing Hipchat Room ID"),
        ({"notification_token": "sometoken", "room_id": "foo"}, None),
    ],
)
def test_validate_hipchat(method_config, error_message, initialized_db):
    method = HipchatMethod()
    assert_validated(method, method_config, error_message, "devtable", "simple")


@pytest.mark.parametrize(
    "method_config,error_message",
    [
        ({}, "Missing Slack Callback URL"),
        ({"url": "http://example.com"}, None),
        ({"url": "http://example.com", "template": "${vulnerability.id} in ${repository}"}, None),
        ({"url": "http://example.com", "template": "${}"}, "Empty expression found"),
        (
            {"url": "http://example.com", "template": "Found ${foo bar}"},
            "For expression `foo bar`: Parse error at 1:4 near token bar (ID)",
        ),
    ],
)
def test_validate_slack(method_config, error_message, initialized_db):
    method = SlackMethod()
    assert_validated(method, method_config, error_message, "devtable", "simple")


@pytest.mark.parametrize(
    "target,expected_users",
    [
        ({"name": "devtable", "kind": "user"}, ["devtable"]),
        ({"name": "buynlarge", "kind": "org"}, ["buynlarge"]),
        ({"name": "creators", "kind": "team"}, ["creator"]),
    ],
)
def test_perform_quay_notification(target, expected_users, initialized_db):
    repository = Repository("buynlarge", "orgrepo")
    notification = Notification(
        uuid="fake",
        event_name="repo_push",
        method_name="quay",
        event_config_dict={},
        method_config_dict={"target": target},
        repository=repository,
    )

    event_handler = NotificationEvent.get_event("repo_push")

    sample_data = event_handler.get_sample_data(repository.namespace_name, repository.name, {})

    method = QuayNotificationMethod()
    method.perform(notification, event_handler, {"event_data": sample_data})

    # Ensure that the notification was written for all the expected users.
    if target["kind"] != "team":
        user = model.user.get_namespace_user(target["name"])
        assert len(model.notification.list_notifications(user, kind_name="repo_push")) > 0


def test_perform_email(initialized_db):
    repository = Repository("buynlarge", "orgrepo")
    notification = Notification(
        uuid="fake",
        event_name="repo_push",
        method_name="email",
        event_config_dict={},
        method_config_dict={"email": "test@example.com"},
        repository=repository,
    )

    event_handler = NotificationEvent.get_event("repo_push")
    sample_data = event_handler.get_sample_data(repository.namespace_name, repository.name, {})

    mock = Mock()

    def get_mock(*args, **kwargs):
        return mock

    with patch("notifications.notificationmethod.Message", get_mock):
        method = EmailMethod()
        method.perform(
            notification, event_handler, {"event_data": sample_data, "performer_data": {}}
        )

    mock.send.assert_called_once()


@pytest.mark.parametrize(
    "method, method_config, netloc",
    [
        (WebhookMethod, {"url": "http://testurl"}, "testurl"),
        (FlowdockMethod, {"flow_api_token": "token"}, "api.flowdock.com"),
        (HipchatMethod, {"notification_token": "token", "room_id": "foo"}, "api.hipchat.com"),
        (SlackMethod, {"url": "http://example.com"}, "example.com"),
    ],
)
def test_perform_http_call(method, method_config, netloc, initialized_db):
    repository = Repository("buynlarge", "orgrepo")
    notification = Notification(
        uuid="fake",
        event_name="repo_push",
        method_name=method.method_name(),
        event_config_dict={},
        method_config_dict=method_config,
        repository=repository,
    )

    event_handler = NotificationEvent.get_event("repo_push")
    sample_data = event_handler.get_sample_data(repository.namespace_name, repository.name, {})

    url_hit = [False]

    @urlmatch(netloc=netloc)
    def url_handler(_, __):
        url_hit[0] = True
        return ""

    with HTTMock(url_handler):
        method().perform(
            notification, event_handler, {"event_data": sample_data, "performer_data": {}}
        )

    assert url_hit[0]


@pytest.mark.parametrize(
    "template, event_data, expected_text",
    [
        (None, {}, None),
        ("Pushed ${updated_tags} to ${repository}", {}, "Pushed latest,foo to buynlarge/orgrepo"),
        (
            "Pushed ${updated_tags} to ${repository}",
            {"updated_tags": ["latest"]},
            "Pushed latest to buynlarge/orgrepo",
        ),
        ("Pushed by ${missing.field}", {}, "Pushed by (none)"),
        ("${missing.field}", {}, "(none)"),
        ("${updated_tags}", {}, '["latest", "foo"]'),
        (
            "Scan: <https://quay.example/repository/${repository}?tab=tags|scan page>\n"
            "Runbook: <https://wiki.example.com/runbook>",
            {},
            "Scan: <https://quay.example/repository/buynlarge/orgrepo?tab=tags|scan page>\n"
            "Runbook: <https://wiki.example.com/runbook>",
        ),
        ("See https://sec.example/x?a=1&b=2", {}, "See https://sec.example/x?a=1&b=2"),
        (
            "Build: ${trigger_metadata.commit_info.message}",
            {
                "trigger_metadata": {
                    "commit_info": {"message": "fix <!channel> & <https://e.x|docs>"}
                }
            },
            "Build: fix &lt;!channel&gt; &amp; &lt;https://e.x|docs&gt;",
        ),
    ],
)
def test_perform_slack_template(template, event_data, expected_text, initialized_db):
    repository = Repository("buynlarge", "orgrepo")
    method_config = {"url": "http://example.com"}
    if template:
        method_config["template"] = template

    notification = Notification(
        uuid="fake",
        event_name="repo_push",
        method_name=SlackMethod.method_name(),
        event_config_dict={},
        method_config_dict=method_config,
        repository=repository,
    )

    event_handler = NotificationEvent.get_event("repo_push")
    sample_data = event_handler.get_sample_data(repository.namespace_name, repository.name, {})
    sample_data.update(event_data)
    notification_data = {"event_data": sample_data, "performer_data": {}}
    summary = event_handler.get_summary(sample_data, notification_data)
    if expected_text is None:
        expected_text = SlackMethod().format_for_slack(
            event_handler.get_message(sample_data, notification_data)
        )

    payloads = []

    @urlmatch(netloc="example.com")
    def url_handler(_, request):
        payloads.append(json.loads(request.body))
        return ""

    with HTTMock(url_handler):
        SlackMethod().perform(notification, event_handler, notification_data)

    assert payloads == [
        {
            "text": summary,
            "username": "quayiobot",
            "attachments": [
                {
                    "fallback": summary,
                    "text": expected_text,
                    "color": "good",
                    "mrkdwn_in": ["text"],
                }
            ],
        }
    ]
