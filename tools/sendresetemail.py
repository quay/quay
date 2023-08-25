import argparse

from flask import Flask, current_app

from app import app
from data import model
from util.useremails import send_recovery_email


def sendReset(username):
    user = model.user.get_nonrobot_user(username)
    if not user:
        print("No user found")
        return

    with app.app_context():
        confirmation_code = model.user.create_reset_password_email_code(user.email)
        send_recovery_email(user.email, confirmation_code)
        print("Email sent to %s" % (user.email))


parser = argparse.ArgumentParser(description="Sends a reset email")
parser.add_argument("username", help="The username")
args = parser.parse_args()
sendReset(args.username)
