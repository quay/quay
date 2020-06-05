"""
Backfill new encrypted fields.

Revision ID: 703298a825c2
Revises: c13c8052f7a6
Create Date: 2019-08-19 16:07:48.109889
"""
# revision identifiers, used by Alembic.
revision = "703298a825c2"
down_revision = "c13c8052f7a6"

import logging
import uuid

from datetime import datetime

from peewee import (
    JOIN,
    IntegrityError,
    DateTimeField,
    CharField,
    ForeignKeyField,
    BooleanField,
    TextField,
    IntegerField,
)

import sqlalchemy as sa

from data.database import (
    BaseModel,
    User,
    Repository,
    AccessTokenKind,
    Role,
    random_string_generator,
    QuayUserField,
    BuildTriggerService,
    uuid_generator,
    DisableReason,
)
from data.fields import (
    Credential,
    DecryptedValue,
    EncryptedCharField,
    EncryptedTextField,
    EnumField,
    CredentialField,
)
from data.model.token import ACCESS_TOKEN_NAME_PREFIX_LENGTH
from data.model.appspecifictoken import TOKEN_NAME_PREFIX_LENGTH as AST_TOKEN_NAME_PREFIX_LENGTH
from data.model.oauth import ACCESS_TOKEN_PREFIX_LENGTH as OAUTH_ACCESS_TOKEN_PREFIX_LENGTH
from data.model.oauth import AUTHORIZATION_CODE_PREFIX_LENGTH

BATCH_SIZE = 10

logger = logging.getLogger(__name__)


def _iterate(model_class, clause):
    while True:
        has_rows = False
        for row in list(model_class.select().where(clause).limit(BATCH_SIZE)):
            has_rows = True
            yield row

        if not has_rows:
            break


def _decrypted(value):
    if value is None:
        return None

    assert isinstance(value, str)
    return DecryptedValue(value)


# NOTE: As per standard migrations involving Peewee models, we copy them here, as they will change
# after this call.
class AccessToken(BaseModel):
    code = CharField(default=random_string_generator(length=64), unique=True, index=True)
    token_name = CharField(default=random_string_generator(length=32), unique=True, index=True)
    token_code = EncryptedCharField(default_token_length=32)
    temporary = BooleanField(default=True)


class RobotAccountToken(BaseModel):
    robot_account = QuayUserField(index=True, allows_robots=True, unique=True)
    token = EncryptedCharField(default_token_length=64)
    fully_migrated = BooleanField(default=False)


class RepositoryBuildTrigger(BaseModel):
    uuid = CharField(default=uuid_generator, index=True)
    auth_token = CharField(null=True)
    private_key = TextField(null=True)

    secure_auth_token = EncryptedCharField(null=True)
    secure_private_key = EncryptedTextField(null=True)
    fully_migrated = BooleanField(default=False)


class AppSpecificAuthToken(BaseModel):
    token_name = CharField(index=True, unique=True, default=random_string_generator(60))
    token_secret = EncryptedCharField(default_token_length=60)
    token_code = CharField(default=random_string_generator(length=120), unique=True, index=True)


class OAuthAccessToken(BaseModel):
    token_name = CharField(index=True, unique=True)
    token_code = CredentialField()
    access_token = CharField(index=True)


class OAuthAuthorizationCode(BaseModel):
    code = CharField(index=True, unique=True, null=True)
    code_name = CharField(index=True, unique=True)
    code_credential = CredentialField()


class OAuthApplication(BaseModel):
    secure_client_secret = EncryptedCharField(default_token_length=40, null=True)
    fully_migrated = BooleanField(default=False)
    client_secret = CharField(default=random_string_generator(length=40))


def upgrade(op, tables, tester):

    # NOTE: Disconnects the Alembic database connection. We do this because the Peewee calls below
    # use a *different* connection, and if we leave the alembic connection open, it'll time out.
    # See: https://github.com/sqlalchemy/alembic/issues/630
    op.get_bind().execute("COMMIT")
    op.get_bind().invalidate()

    from app import app

    if app.config.get("SETUP_COMPLETE", False) or tester.is_testing():
        # AccessToken.
        logger.info("Backfilling encrypted credentials for access tokens")
        for access_token in _iterate(
            AccessToken, ((AccessToken.token_name >> None) | (AccessToken.token_name == ""))
        ):
            logger.info("Backfilling encrypted credentials for access token %s", access_token.id)
            assert access_token.code is not None
            assert access_token.code[:ACCESS_TOKEN_NAME_PREFIX_LENGTH]
            assert access_token.code[ACCESS_TOKEN_NAME_PREFIX_LENGTH:]

            token_name = access_token.code[:ACCESS_TOKEN_NAME_PREFIX_LENGTH]
            token_code = _decrypted(access_token.code[ACCESS_TOKEN_NAME_PREFIX_LENGTH:])

            (
                AccessToken.update(token_name=token_name, token_code=token_code)
                .where(AccessToken.id == access_token.id, AccessToken.code == access_token.code)
                .execute()
            )

        assert AccessToken.select().where(AccessToken.token_name >> None).count() == 0

        # Robots.
        logger.info("Backfilling encrypted credentials for robots")
        while True:
            has_row = False
            query = (
                User.select()
                .join(RobotAccountToken, JOIN.LEFT_OUTER)
                .where(User.robot == True, RobotAccountToken.id >> None)
                .limit(BATCH_SIZE)
            )

            for robot_user in query:
                logger.info("Backfilling encrypted credentials for robot %s", robot_user.id)
                has_row = True
                try:
                    RobotAccountToken.create(
                        robot_account=robot_user,
                        token=_decrypted(robot_user.email),
                        fully_migrated=False,
                    )
                except IntegrityError:
                    break

            if not has_row:
                break

        # RepositoryBuildTrigger
        logger.info("Backfilling encrypted credentials for repo build triggers")
        for repo_build_trigger in _iterate(
            RepositoryBuildTrigger, (RepositoryBuildTrigger.fully_migrated == False)
        ):
            logger.info(
                "Backfilling encrypted credentials for repo build trigger %s", repo_build_trigger.id
            )

            (
                RepositoryBuildTrigger.update(
                    secure_auth_token=_decrypted(repo_build_trigger.auth_token),
                    secure_private_key=_decrypted(repo_build_trigger.private_key),
                    fully_migrated=True,
                )
                .where(
                    RepositoryBuildTrigger.id == repo_build_trigger.id,
                    RepositoryBuildTrigger.uuid == repo_build_trigger.uuid,
                )
                .execute()
            )

        assert (
            RepositoryBuildTrigger.select()
            .where(RepositoryBuildTrigger.fully_migrated == False)
            .count()
        ) == 0

        # AppSpecificAuthToken
        logger.info("Backfilling encrypted credentials for app specific auth tokens")
        for token in _iterate(
            AppSpecificAuthToken,
            (
                (AppSpecificAuthToken.token_name >> None)
                | (AppSpecificAuthToken.token_name == "")
                | (AppSpecificAuthToken.token_secret >> None)
            ),
        ):
            logger.info("Backfilling encrypted credentials for app specific auth %s", token.id)
            assert token.token_code[AST_TOKEN_NAME_PREFIX_LENGTH:]

            token_name = token.token_code[:AST_TOKEN_NAME_PREFIX_LENGTH]
            token_secret = _decrypted(token.token_code[AST_TOKEN_NAME_PREFIX_LENGTH:])
            assert token_name
            assert token_secret

            (
                AppSpecificAuthToken.update(token_name=token_name, token_secret=token_secret)
                .where(
                    AppSpecificAuthToken.id == token.id,
                    AppSpecificAuthToken.token_code == token.token_code,
                )
                .execute()
            )

        assert (
            AppSpecificAuthToken.select().where(AppSpecificAuthToken.token_name >> None).count()
        ) == 0

        # OAuthAccessToken
        logger.info("Backfilling credentials for OAuth access tokens")
        for token in _iterate(
            OAuthAccessToken,
            ((OAuthAccessToken.token_name >> None) | (OAuthAccessToken.token_name == "")),
        ):
            logger.info("Backfilling credentials for OAuth access token %s", token.id)
            token_name = token.access_token[:OAUTH_ACCESS_TOKEN_PREFIX_LENGTH]
            token_code = Credential.from_string(
                token.access_token[OAUTH_ACCESS_TOKEN_PREFIX_LENGTH:]
            )
            assert token_name
            assert token.access_token[OAUTH_ACCESS_TOKEN_PREFIX_LENGTH:]

            (
                OAuthAccessToken.update(token_name=token_name, token_code=token_code)
                .where(
                    OAuthAccessToken.id == token.id,
                    OAuthAccessToken.access_token == token.access_token,
                )
                .execute()
            )

        assert (OAuthAccessToken.select().where(OAuthAccessToken.token_name >> None).count()) == 0

        # OAuthAuthorizationCode
        logger.info("Backfilling credentials for OAuth auth code")
        for code in _iterate(
            OAuthAuthorizationCode,
            ((OAuthAuthorizationCode.code_name >> None) | (OAuthAuthorizationCode.code_name == "")),
        ):
            logger.info("Backfilling credentials for OAuth auth code %s", code.id)
            user_code = code.code or random_string_generator(AUTHORIZATION_CODE_PREFIX_LENGTH * 2)()
            code_name = user_code[:AUTHORIZATION_CODE_PREFIX_LENGTH]
            code_credential = Credential.from_string(user_code[AUTHORIZATION_CODE_PREFIX_LENGTH:])
            assert code_name
            assert user_code[AUTHORIZATION_CODE_PREFIX_LENGTH:]

            (
                OAuthAuthorizationCode.update(code_name=code_name, code_credential=code_credential)
                .where(OAuthAuthorizationCode.id == code.id)
                .execute()
            )

        assert (
            OAuthAuthorizationCode.select().where(OAuthAuthorizationCode.code_name >> None).count()
        ) == 0

        # OAuthApplication
        logger.info("Backfilling secret for OAuth applications")
        for app in _iterate(OAuthApplication, OAuthApplication.fully_migrated == False):
            logger.info("Backfilling secret for OAuth application %s", app.id)
            client_secret = app.client_secret or str(uuid.uuid4())
            secure_client_secret = _decrypted(client_secret)

            (
                OAuthApplication.update(
                    secure_client_secret=secure_client_secret, fully_migrated=True
                )
                .where(OAuthApplication.id == app.id, OAuthApplication.fully_migrated == False)
                .execute()
            )

        assert (
            OAuthApplication.select().where(OAuthApplication.fully_migrated == False).count()
        ) == 0


def downgrade(op, tables, tester):
    pass
