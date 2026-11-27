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
    NotificationMethodPerformException,
    QuayNotificationMethod,
    SlackMethod,
    WebhookMethod,
)
from test.fixtures import *

_PUBLIC_DNS = [(2, 1, 6, "", ("93.184.216.34", 0))]


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
        ({"url": "http://10.0.0.1/"}, "Invalid webhook URL"),
        ({"url": "http://169.254.169.254/latest/meta-data/"}, "Invalid webhook URL"),
        ({"url": "http://host.containers.internal:9999/ssrf"}, "Invalid webhook URL"),
        ({"url": "http://user:pass@example.com/"}, "Invalid webhook URL"),
        (
            {"url": r"http://169.254.169.254\x.93.184.216.34.sslip.io/latest/meta-data/"},
            "Invalid webhook URL",
        ),
    ],
)
def test_validate_webhook(method_config, error_message, initialized_db):
    method = WebhookMethod()
    with patch("util.security.ssrf._getaddrinfo", return_value=_PUBLIC_DNS):
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
        ({"url": "http://10.0.0.1/hooks"}, "Invalid Slack Callback URL"),
        ({"url": "http://localhost/hooks"}, "Invalid Slack Callback URL"),
    ],
)
def test_validate_slack(method_config, error_message, initialized_db):
    method = SlackMethod()
    with patch("util.security.ssrf._getaddrinfo", return_value=_PUBLIC_DNS):
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
        (WebhookMethod, {"url": "http://example.com/hook"}, "example.com"),
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

    with patch("util.security.ssrf._getaddrinfo", return_value=_PUBLIC_DNS):
        with HTTMock(url_handler):
            method().perform(
                notification, event_handler, {"event_data": sample_data, "performer_data": {}}
            )

    assert url_hit[0]


@pytest.mark.parametrize(
    "method, method_config, error_message",
    [
        (
            WebhookMethod,
            {"url": "http://10.0.0.1/ssrf"},
            "Invalid webhook URL",
        ),
        (
            WebhookMethod,
            {"url": "http://host.containers.internal:9999/ssrf"},
            "Invalid webhook URL",
        ),
        (
            SlackMethod,
            {"url": "http://169.254.169.254/hooks"},
            "Invalid Slack Callback URL",
        ),
    ],
)
def test_perform_blocks_ssrf_urls(method, method_config, error_message, initialized_db):
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

    with patch("notifications.notificationmethod.requests.post") as mock_post:
        with pytest.raises(NotificationMethodPerformException) as exc:
            method().perform(
                notification, event_handler, {"event_data": sample_data, "performer_data": {}}
            )
        assert str(exc.value) == error_message
        mock_post.assert_not_called()


def test_validate_webhook_extra_hostname_blacklist(initialized_db):
    method = WebhookMethod()
    with patch.dict(
        "notifications.notificationmethod.app.config",
        {"WEBHOOK_HOSTNAME_BLACKLIST": ["evil.example.com"]},
    ):
        with patch("util.security.ssrf._getaddrinfo", return_value=_PUBLIC_DNS):
            assert_validated(
                method,
                {"url": "https://evil.example.com/hook"},
                "Invalid webhook URL",
                "devtable",
                "simple",
            )


def test_validate_webhook_passes_environment_proxy_config(initialized_db):
    method = WebhookMethod()
    proxy = {"http_proxy": "http://proxy.example:8080", "https_proxy": None, "no_proxy": None}
    with patch(
        "notifications.notificationmethod.get_environment_proxy_config",
        return_value=proxy,
    ):
        with patch(
            "notifications.notificationmethod.validate_external_registry_url"
        ) as mock_validate:
            method.validate("devtable", "simple", {"url": "https://example.com/hook"})

    mock_validate.assert_called_once()
    assert mock_validate.call_args.kwargs.get("proxy_config") == proxy
    assert mock_validate.call_args.kwargs.get("resolve_dns") is True


@pytest.mark.parametrize(
    "method, method_config",
    [
        (WebhookMethod, {"url": "http://example.com/hook"}),
        (SlackMethod, {"url": "http://example.com/hooks"}),
    ],
)
def test_perform_http_disables_redirects(method, method_config, initialized_db):
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

    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.content = b""

    with patch("util.security.ssrf._getaddrinfo", return_value=_PUBLIC_DNS):
        with patch(
            "notifications.notificationmethod.requests.post", return_value=mock_resp
        ) as mock_post:
            method().perform(
                notification, event_handler, {"event_data": sample_data, "performer_data": {}}
            )

    assert mock_post.call_count == 1
    assert mock_post.call_args.kwargs.get("allow_redirects") is False
