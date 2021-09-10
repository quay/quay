import logging
import os.path
import re
import json
import mock

import requests
from flask_mail import Message
from urllib.parse import urlparse

from app import mail, app, OVERRIDE_CONFIG_DIRECTORY
from data import model
from util.config.validator import SSL_FILENAMES
from util.jsontemplate import JSONTemplate, JSONTemplateParseException
from util.fips import login_fips_safe
from workers.queueworker import JobException
import features

logger = logging.getLogger(__name__)

METHOD_TIMEOUT = app.config.get("NOTIFICATION_SEND_TIMEOUT", 10)  # Seconds
HOSTNAME_BLACKLIST = ["localhost", "127.0.0.1"]
HOSTNAME_BLACKLIST.extend(app.config.get("WEBHOOK_HOSTNAME_BLACKLIST", []))
MAIL_DEFAULT_SENDER = app.config.get("MAIL_DEFAULT_SENDER", "admin@example.com")


class InvalidNotificationMethodException(Exception):
    pass


class CannotValidateNotificationMethodException(Exception):
    pass


class NotificationMethodPerformException(JobException):
    pass


def _ssl_cert():
    if app.config["PREFERRED_URL_SCHEME"] == "https":
        cert_files = [OVERRIDE_CONFIG_DIRECTORY + f for f in SSL_FILENAMES]
        cert_exists = all([os.path.isfile(f) for f in cert_files])
        return cert_files if cert_exists else None

    return None


class NotificationMethod(object):
    def __init__(self):
        pass

    @classmethod
    def method_name(cls):
        """
        Particular method implemented by subclasses.
        """
        raise NotImplementedError

    def validate(self, namespace_name, repo_name, config_data):
        """
        Validates that the notification can be created with the given data.

        Throws a CannotValidateNotificationMethodException on failure.
        """
        raise NotImplementedError

    def perform(self, notification_obj, event_handler, notification_data):
        """
        Performs the notification method.

        notification_obj: The notification namedtuple.
        event_handler: The NotificationEvent handler.
        notification_data: The dict of notification data placed in the queue.
        """
        raise NotImplementedError

    @classmethod
    def get_method(cls, methodname):
        for subc in cls.__subclasses__():
            if subc.method_name() == methodname:
                return subc()

        raise InvalidNotificationMethodException("Unable to find method: %s" % methodname)


class QuayNotificationMethod(NotificationMethod):
    @classmethod
    def method_name(cls):
        return "quay_notification"

    def validate(self, namespace_name, repo_name, config_data):
        _, err_message, _ = self.find_targets(namespace_name, config_data)
        if err_message:
            raise CannotValidateNotificationMethodException(err_message)

    def find_targets(self, namespace_name, config_data):
        target_info = config_data.get("target", None)
        if not target_info or not target_info.get("kind"):
            return (True, "Missing target", [])

        if target_info["kind"] == "user":
            target = model.user.get_nonrobot_user(target_info["name"])
            if not target:
                # Just to be safe.
                return (True, "Unknown user %s" % target_info["name"], [])

            return (True, None, [target])
        elif target_info["kind"] == "org":
            try:
                target = model.organization.get_organization(target_info["name"])
            except model.organization.InvalidOrganizationException:
                return (True, "Unknown organization %s" % target_info["name"], None)

            # Only repositories under the organization can cause notifications to that org.
            if target_info["name"] != namespace_name:
                return (False, "Organization name must match repository namespace")

            return (True, None, [target])
        elif target_info["kind"] == "team":
            # Lookup the team.
            org_team = None
            try:
                org_team = model.team.get_organization_team(namespace_name, target_info["name"])
            except model.InvalidTeamException:
                # Probably deleted.
                return (True, "Unknown team %s" % target_info["name"], None)

            # Lookup the team's members
            return (True, None, model.organization.get_organization_team_members(org_team.id))

    def perform(self, notification_obj, event_handler, notification_data):
        repository = notification_obj.repository
        if not repository:
            # Probably deleted.
            return

        # Lookup the target user or team to which we'll send the notification.
        config_data = notification_obj.method_config_dict
        status, err_message, target_users = self.find_targets(
            repository.namespace_name, config_data
        )
        if not status:
            raise NotificationMethodPerformException(err_message)

        # For each of the target users, create a notification.
        for target_user in set(target_users or []):
            model.notification.create_notification(
                event_handler.event_name(), target_user, metadata=notification_data["event_data"]
            )


class EmailMethod(NotificationMethod):
    @classmethod
    def method_name(cls):
        return "email"

    def validate(self, namespace_name, repo_name, config_data):
        email = config_data.get("email", "")
        if not email:
            raise CannotValidateNotificationMethodException("Missing e-mail address")

        record = model.repository.get_email_authorized_for_repo(namespace_name, repo_name, email)
        if not record or not record.confirmed:
            raise CannotValidateNotificationMethodException(
                "The specified e-mail address "
                "is not authorized to receive "
                "notifications for this repository"
            )

    def perform(self, notification_obj, event_handler, notification_data):
        config_data = notification_obj.method_config_dict
        email = config_data.get("email", "")
        if not email:
            return

        with app.app_context():
            msg = Message(
                event_handler.get_summary(notification_data["event_data"], notification_data),
                recipients=[email],
            )
            msg.html = event_handler.get_message(notification_data["event_data"], notification_data)

            try:
                if features.FIPS:
                    assert app.config[
                        "MAIL_USE_TLS"
                    ], "MAIL_USE_TLS must be enabled to use SMTP in FIPS mode."
                    with mock.patch("smtplib.SMTP.login", login_fips_safe):
                        mail.send(msg)
                else:
                    mail.send(msg)
            except Exception as ex:
                logger.exception("Email was unable to be sent")
                raise NotificationMethodPerformException(str(ex))


class WebhookMethod(NotificationMethod):
    @classmethod
    def method_name(cls):
        return "webhook"

    def validate(self, namespace_name, repo_name, config_data):
        # Validate the URL.
        url = config_data.get("url", "")
        if not url:
            raise CannotValidateNotificationMethodException("Missing webhook URL")

        parsed = urlparse(url)
        if parsed.scheme != "https" and parsed.scheme != "http":
            raise CannotValidateNotificationMethodException("Invalid webhook URL")

        if parsed.hostname.lower() in HOSTNAME_BLACKLIST:
            raise CannotValidateNotificationMethodException("Invalid webhook URL")

        # If a template was specified, ensure it is a valid template.
        template = config_data.get("template")
        if template:
            # Validate template.
            try:
                JSONTemplate(template)
            except JSONTemplateParseException as jtpe:
                raise CannotValidateNotificationMethodException(str(jtpe))

    def perform(self, notification_obj, event_handler, notification_data):
        config_data = notification_obj.method_config_dict
        url = config_data.get("url", "")
        if not url:
            return

        parsed = urlparse(url)
        if parsed.scheme != "https" and parsed.scheme != "http":
            logger.error("Invalid webhook URL: %s", url)
            return

        if parsed.hostname.lower() in HOSTNAME_BLACKLIST:
            logger.error("Invalid webhook URL: %s", url)
            return

        payload = notification_data["event_data"]
        template = config_data.get("template")
        if template:
            try:
                jt = JSONTemplate(template)
                payload = jt.apply(payload)
            except JSONTemplateParseException as jtpe:
                logger.exception("Got exception when trying to process template `%s`", template)
                raise NotificationMethodPerformException(str(jtpe))

        headers = {"Content-type": "application/json"}

        try:
            resp = requests.post(
                url,
                data=json.dumps(payload),
                headers=headers,
                cert=_ssl_cert(),
                timeout=METHOD_TIMEOUT,
            )
            if resp.status_code // 100 != 2:
                error_message = "%s response for webhook to url: %s" % (resp.status_code, url)
                logger.error(error_message)
                logger.error(resp.content)
                raise NotificationMethodPerformException(error_message)

        except requests.exceptions.RequestException as ex:
            logger.exception("Webhook was unable to be sent")
            raise NotificationMethodPerformException(str(ex))


class FlowdockMethod(NotificationMethod):
    """
    Method for sending notifications to Flowdock via the Team Inbox API:

    https://www.flowdock.com/api/team-inbox
    """

    @classmethod
    def method_name(cls):
        return "flowdock"

    def validate(self, namespace_name, repo_name, config_data):
        token = config_data.get("flow_api_token", "")
        if not token:
            raise CannotValidateNotificationMethodException("Missing Flowdock API Token")

    def perform(self, notification_obj, event_handler, notification_data):
        config_data = notification_obj.method_config_dict
        token = config_data.get("flow_api_token", "")
        if not token:
            return

        owner = model.user.get_user_or_org(notification_obj.repository.namespace_name)
        if not owner:
            # Something went wrong.
            return

        url = "https://api.flowdock.com/v1/messages/team_inbox/%s" % token
        headers = {"Content-type": "application/json"}
        payload = {
            "source": "Quay",
            "from_address": MAIL_DEFAULT_SENDER,
            "subject": event_handler.get_summary(
                notification_data["event_data"], notification_data
            ),
            "content": event_handler.get_message(
                notification_data["event_data"], notification_data
            ),
            "from_name": owner.username,
            "project": (
                notification_obj.repository.namespace_name + " " + notification_obj.repository.name
            ),
            "tags": ["#" + event_handler.event_name()],
            "link": notification_data["event_data"]["homepage"],
        }

        try:
            resp = requests.post(
                url, data=json.dumps(payload), headers=headers, timeout=METHOD_TIMEOUT
            )
            if resp.status_code // 100 != 2:
                error_message = "%s response for flowdock to url: %s" % (resp.status_code, url)
                logger.error(error_message)
                logger.error(resp.content)
                raise NotificationMethodPerformException(error_message)

        except requests.exceptions.RequestException as ex:
            logger.exception("Flowdock method was unable to be sent")
            raise NotificationMethodPerformException(str(ex))


class HipchatMethod(NotificationMethod):
    """
    Method for sending notifications to Hipchat via the API:

    https://www.hipchat.com/docs/apiv2/method/send_room_notification
    """

    @classmethod
    def method_name(cls):
        return "hipchat"

    def validate(self, namespace_name, repo_name, config_data):
        if not config_data.get("notification_token", ""):
            raise CannotValidateNotificationMethodException(
                "Missing Hipchat Room Notification Token"
            )

        if not config_data.get("room_id", ""):
            raise CannotValidateNotificationMethodException("Missing Hipchat Room ID")

    def perform(self, notification_obj, event_handler, notification_data):
        config_data = notification_obj.method_config_dict
        token = config_data.get("notification_token", "")
        room_id = config_data.get("room_id", "")

        if not token or not room_id:
            return

        owner = model.user.get_user_or_org(notification_obj.repository.namespace_name)
        if not owner:
            # Something went wrong.
            return

        url = "https://api.hipchat.com/v2/room/%s/notification?auth_token=%s" % (room_id, token)

        level = event_handler.get_level(notification_data["event_data"], notification_data)
        color = {
            "info": "gray",
            "warning": "yellow",
            "error": "red",
            "success": "green",
            "primary": "purple",
        }.get(level, "gray")

        headers = {"Content-type": "application/json"}
        payload = {
            "color": color,
            "message": event_handler.get_message(
                notification_data["event_data"], notification_data
            ),
            "notify": level == "error",
            "message_format": "html",
        }

        try:
            resp = requests.post(
                url, data=json.dumps(payload), headers=headers, timeout=METHOD_TIMEOUT
            )
            if resp.status_code // 100 != 2:
                error_message = "%s response for hipchat to url: %s" % (resp.status_code, url)
                logger.error(error_message)
                logger.error(resp.content)
                raise NotificationMethodPerformException(error_message)

        except requests.exceptions.RequestException as ex:
            logger.exception("Hipchat method was unable to be sent")
            raise NotificationMethodPerformException(str(ex))


from html.parser import HTMLParser


class SlackAdjuster(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.result = []

    def handle_data(self, d):
        self.result.append(d)

    def get_attr(self, attrs, name):
        for attr in attrs:
            if attr[0] == name:
                return attr[1]

        return ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.result.append("<%s|" % (self.get_attr(attrs, "href"),))

        if tag == "i":
            self.result.append("_")

        if tag == "b" or tag == "strong":
            self.result.append("*")

        if tag == "img":
            self.result.append("")

    def handle_endtag(self, tag):
        if tag == "a":
            self.result.append(">")

        if tag == "b" or tag == "strong":
            self.result.append("*")

        if tag == "i":
            self.result.append("_")

    def get_data(self):
        return "".join(self.result)


def adjust_tags(html):
    s = SlackAdjuster()
    s.feed(html)
    return s.get_data()


class SlackMethod(NotificationMethod):
    """
    Method for sending notifications to Slack via the API:

    https://api.slack.com/docs/attachments
    """

    @classmethod
    def method_name(cls):
        return "slack"

    def validate(self, namespace_name, repo_name, config_data):
        if not config_data.get("url", ""):
            raise CannotValidateNotificationMethodException("Missing Slack Callback URL")

    def format_for_slack(self, message):
        message = message.replace("\n", "")
        message = re.sub(r"\s+", " ", message)
        message = message.replace("<br>", "\n")
        return adjust_tags(message)

    def perform(self, notification_obj, event_handler, notification_data):
        config_data = notification_obj.method_config_dict
        url = config_data.get("url", "")
        if not url:
            return

        owner = model.user.get_user_or_org(notification_obj.repository.namespace_name)
        if not owner:
            # Something went wrong.
            return

        level = event_handler.get_level(notification_data["event_data"], notification_data)
        color = {
            "info": "#ffffff",
            "warning": "warning",
            "error": "danger",
            "success": "good",
            "primary": "good",
        }.get(level, "#ffffff")

        summary = event_handler.get_summary(notification_data["event_data"], notification_data)
        message = event_handler.get_message(notification_data["event_data"], notification_data)

        headers = {"Content-type": "application/json"}
        payload = {
            "text": summary,
            "username": "quayiobot",
            "attachments": [
                {
                    "fallback": summary,
                    "text": self.format_for_slack(message),
                    "color": color,
                    "mrkdwn_in": ["text"],
                }
            ],
        }

        try:
            resp = requests.post(
                url, data=json.dumps(payload), headers=headers, timeout=METHOD_TIMEOUT
            )
            if resp.status_code // 100 != 2:
                error_message = "%s response for Slack to url: %s" % (resp.status_code, url)
                logger.error(error_message)
                logger.error(resp.content)
                raise NotificationMethodPerformException(error_message)

        except requests.exceptions.RequestException as ex:
            logger.exception("Slack method was unable to be sent: %s", str(ex))
            raise NotificationMethodPerformException(str(ex))
