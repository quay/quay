from app import app
from data import model

import argparse


def renameUser(username, new_name):
    if username == new_name:
        raise Exception("Must give a new username")

    check = model.user.get_user_or_org(new_name)
    if check is not None:
        raise Exception("New username %s already exists" % new_name)

    existing = model.user.get_user_or_org(username)
    if existing is None:
        raise Exception("Username %s does not exist" % username)

    print("Renaming user...")
    model.user.change_username(existing.id, new_name)
    print("Rename complete")


parser = argparse.ArgumentParser(description="Rename a user")
parser.add_argument("username", help="The current username")
parser.add_argument("new_name", help="The new username")
args = parser.parse_args()
renameUser(args.username, args.new_name)
