from app import app

from util.useremails import send_confirmation_email

from data import model

import argparse

from flask import Flask, current_app


def sendConfirmation(username):
    user = model.user.get_nonrobot_user(username)
    if not user:
        print("No user found")
        return

    with app.app_context():
        confirmation_code = model.user.create_confirm_email_code(user)
        send_confirmation_email(user.username, user.email, confirmation_code)
        print("Email sent to %s" % (user.email))


parser = argparse.ArgumentParser(description="Sends a confirmation email")
parser.add_argument("username", help="The username")
args = parser.parse_args()
sendConfirmation(args.username)
