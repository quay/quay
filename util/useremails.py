import os
import json
import logging

from flask_mail import Message

import features

from _init import ROOT_DIR
from app import mail, app, get_app_url
from util.jinjautil import get_template_env
from util.html import html2text


logger = logging.getLogger(__name__)

template_env = get_template_env(os.path.join(ROOT_DIR, "emails"))


class CannotSendEmailException(Exception):
    pass


class GmailAction(object):
    """
    Represents an action that can be taken in Gmail in response to the email.
    """

    def __init__(self, metadata):
        self.metadata = metadata

    @staticmethod
    def confirm(name, url, description):
        return GmailAction(
            {
                "@context": "http://schema.org",
                "@type": "EmailMessage",
                "action": {
                    "@type": "ConfirmAction",
                    "name": name,
                    "handler": {"@type": "HttpActionHandler", "url": get_app_url() + "/" + url},
                },
                "description": description,
            }
        )

    @staticmethod
    def view(name, url, description):
        return GmailAction(
            {
                "@context": "http://schema.org",
                "@type": "EmailMessage",
                "action": {"@type": "ViewAction", "name": name, "url": get_app_url() + "/" + url},
                "description": description,
            }
        )


def send_email(recipient, subject, template_file, parameters, action=None):
    app_title = app.config["REGISTRY_TITLE_SHORT"]
    app_url = get_app_url()
    html, plain = render_email(
        app_title, app_url, recipient, subject, template_file, parameters, action=None
    )
    msg = Message("[%s] %s" % (app_title, subject), recipients=[recipient])
    msg.html = html
    msg.body = plain

    try:
        mail.send(msg)
        if app.config["TESTING"]:
            logger.debug("Quay is configured for testing. Email not sent: '%s'", msg.subject)
        else:
            logger.debug("Sent email: '%s'", msg.subject)
    except Exception as ex:
        logger.exception("Error while trying to send email to %s", recipient)
        raise CannotSendEmailException(str(ex))


def render_email(app_title, app_url, recipient, subject, template_file, parameters, action=None):
    def app_link_handler(url=None):
        return app_url + "/" + url if url else app_url

    app_logo = app.config.get("ENTERPRISE_LOGO_URL", "https://quay.io/static/img/quay-logo.png")

    parameters.update(
        {
            "subject": subject,
            "app_logo": app_logo,
            "app_url": app_url,
            "app_title": app_title,
            "hosted": features.BILLING,
            "app_link": app_link_handler,
            "action_metadata": json.dumps(action.metadata) if action else None,
            "with_base_template": True,
        }
    )

    rendered_html = template_env.get_template(template_file + ".html").render(parameters)

    parameters.update(
        {"with_base_template": False,}
    )

    rendered_for_plain = template_env.get_template(template_file + ".html").render(parameters)
    return rendered_html, html2text(rendered_for_plain)


def send_password_changed(username, email):
    send_email(email, "Account password changed", "passwordchanged", {"username": username})


def send_email_changed(username, old_email, new_email):
    send_email(
        old_email,
        "Account e-mail address changed",
        "emailchanged",
        {"username": username, "new_email": new_email},
    )


def send_change_email(username, email, token):
    send_email(
        email,
        "E-mail address change requested",
        "changeemail",
        {"username": username, "token": token},
    )


def send_confirmation_email(username, email, token):
    action = GmailAction.confirm(
        "Confirm E-mail", "confirm?code=" + token, "Verification of e-mail address"
    )

    send_email(
        email,
        "Please confirm your e-mail address",
        "confirmemail",
        {"username": username, "token": token},
        action=action,
    )


def send_repo_authorization_email(namespace, repository, email, token):
    action = GmailAction.confirm(
        "Verify E-mail", "authrepoemail?code=" + token, "Verification of e-mail address"
    )

    subject = "Please verify your e-mail address for repository %s/%s" % (namespace, repository)
    send_email(
        email,
        subject,
        "repoauthorizeemail",
        {"namespace": namespace, "repository": repository, "token": token},
        action=action,
    )


def send_org_recovery_email(org, admin_users):
    subject = "Organization %s recovery" % (org.username)
    send_email(
        org.email,
        subject,
        "orgrecovery",
        {"organization": org.username, "admin_usernames": [user.username for user in admin_users],},
    )


def send_recovery_email(email, token):
    action = GmailAction.view("Recover Account", "recovery?code=" + token, "Recovery of an account")

    subject = "Account recovery"
    send_email(email, subject, "recovery", {"email": email, "token": token}, action=action)


def send_payment_failed(email, username):
    send_email(email, "Subscription Payment Failure", "paymentfailure", {"username": username})


def send_org_invite_email(member_name, member_email, orgname, team, adder, code):
    action = GmailAction.view(
        "Join %s" % team, "confirminvite?code=" + code, "Invitation to join a team"
    )

    send_email(
        member_email,
        "Invitation to join team",
        "teaminvite",
        {"inviter": adder, "token": code, "organization": orgname, "teamname": team},
        action=action,
    )


def send_invoice_email(email, contents):
    # Note: This completely generates the contents of the email, so we don't use the
    # normal template here.
    msg = Message("Quay payment received - Thank you!", recipients=[email])
    msg.html = contents
    mail.send(msg)


def send_logs_exported_email(
    email, export_id, status, exported_data_url=None, exported_data_expiration=None
):
    send_email(
        email,
        "Export Action Logs Complete",
        "logsexported",
        {
            "status": status,
            "export_id": export_id,
            "exported_data_url": exported_data_url,
            "exported_data_expiration": exported_data_expiration,
        },
    )


# INTERNAL EMAILS BELOW


def send_subscription_change(change_description, customer_id, customer_email, quay_username):
    SUBSCRIPTION_CHANGE_TITLE = "Subscription Change - {0} {1}"
    SUBSCRIPTION_CHANGE = """
  Change: {0}<br>
  Customer id: <a href="https://manage.stripe.com/customers/{1}">{1}</a><br>
  Customer email: <a href="mailto:{2}">{2}</a><br>
  Quay user or org name: {3}<br>
  """

    title = SUBSCRIPTION_CHANGE_TITLE.format(quay_username, change_description)
    msg = Message(title, recipients=["stripe@quay.io"])
    msg.html = SUBSCRIPTION_CHANGE.format(
        change_description, customer_id, customer_email, quay_username
    )
    mail.send(msg)
