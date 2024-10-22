"""Backfill existing superusers and restricted users

Revision ID: f96427d5d35c
Revises: 87d86e3d4c2c
Create Date: 2024-09-05 13:48:34.624765

"""

# revision identifiers, used by Alembic.
revision = "f96427d5d35c"
down_revision = "87d86e3d4c2c"

import logging
from datetime import datetime

import sqlalchemy as sa
from peewee import *
from peewee import BooleanField

from app import app
from data.database import BaseModel, random_string_generator, uuid_generator

logger = logging.getLogger(__name__)

# NOTE: As per standard migrations involving Peewee models, we copy the model here, as it will change
# after this call.


class User(BaseModel):
    uuid = CharField(default=uuid_generator, max_length=36, null=True, index=True)
    username = CharField(unique=True, index=True)
    password_hash = CharField(null=True)
    email = CharField(unique=True, index=True, default=random_string_generator(length=64))
    verified = BooleanField(default=False)
    stripe_id = CharField(index=True, null=True)
    organization = BooleanField(default=False, index=True)
    robot = BooleanField(default=False, index=True)
    invoice_email = BooleanField(default=False)
    invalid_login_attempts = IntegerField(default=0)
    last_invalid_login = DateTimeField(default=datetime.utcnow)
    removed_tag_expiration_s = BigIntegerField(default=1209600)  # Two weeks
    enabled = BooleanField(default=True)
    invoice_email_address = CharField(null=True, index=True)

    given_name = CharField(null=True)
    family_name = CharField(null=True)
    company = CharField(null=True)
    location = CharField(null=True)

    maximum_queued_builds_count = IntegerField(null=True)
    creation_date = DateTimeField(default=datetime.utcnow, null=True)
    last_accessed = DateTimeField(null=True, index=True)

    # Superusers, restricted users
    is_superuser = BooleanField(default=False)
    is_restricted_user = BooleanField(default=False)

    # Namespace default repo visibility
    private_repos_on_push = BooleanField(default=True)


def upgrade(op, tables, tester):
    superusers = app.config.get("SUPER_USERS", [])
    push_visibility = app.config.get("CREATE_PRIVATE_REPO_ON_PUSH", True)
    restrict_users = app.config.get("FEATURE_RESTRICTED_USERS", False)
    restricted_users_whitelist = app.config.get("RESTRICTED_USERS_WHITELIST", [])

    # Don't run this migration if the number of users is 0
    if User.select().count():

        # Backfill super users
        # Make sure that we have something to do
        logger.debug("Backfilling super user list.")
        if superusers:
            for user in superusers:
                logger.debug("Adding superuser privileges to user %s.", user)
                query = User.update(is_superuser=True, is_restricted_user=False).where(
                    User.username == user
                )
                query.execute()

        # Set all current namespaces' visibility
        logger.debug("Backfilling repository push visibility.")
        if not push_visibility:
            for user in User.select():
                logger.debug("Setting push visiblity on namespace %s.", user.username)
                query = User.update(private_repos_on_push=push_visibility).where(
                    User.username == user.username
                )
                query.execute()

        # Set restricted users
        logger.debug("Backfilling non-restricted users.")
        if restrict_users:
            for user in User.select():
                if user.username in restricted_users_whitelist or user.username in superusers:
                    logger.debug("Whitelisting namespace %s.", user.username)
                    query = User.update(is_restricted_user=False).where(
                        User.username == user.username
                    )
                    query.execute()
                else:
                    logger.debug("Restricting namespace %s.", user.username)
                    query = User.update(is_restricted_user=True).where(
                        User.username == user.username
                    )
                    query.execute()
                if user.robot == True and user.username.split("+")[0] in restricted_users_whitelist:
                    logger.debug("Whitelisting robot account %s.", user.username)
                    query = User.update(is_restricted_user=False).where(
                        User.username == user.username
                    )
                    query.execute()
                else:
                    logger.debug("Restricting robot account %s.", user.username)
                    query = User.update(is_restricted_user=True).where(
                        User.username == user.username
                    )
                    query.execute()
    else:
        pass


def downgrade(op, tables, tester):
    pass
