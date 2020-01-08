import logging

from datetime import datetime

from data.database import AppSpecificAuthToken, User, random_string_generator
from data.model import config
from data.model._basequery import update_last_accessed
from data.fields import DecryptedValue
from util.timedeltastring import convert_to_timedelta
from util.unicode import remove_unicode
from util.bytes import Bytes

logger = logging.getLogger(__name__)

TOKEN_NAME_PREFIX_LENGTH = 60
MINIMUM_TOKEN_SUFFIX_LENGTH = 60


def _default_expiration_duration():
    expiration_str = config.app_config.get("APP_SPECIFIC_TOKEN_EXPIRATION")
    return convert_to_timedelta(expiration_str) if expiration_str else None


# Define a "unique" value so that callers can specifiy an expiration of None and *not* have it
# use the default.
_default_expiration_duration_opt = "__deo"


def create_token(user, title, expiration=_default_expiration_duration_opt):
    """
    Creates and returns an app specific token for the given user.

    If no expiration is specified (including `None`), then the default from config is used.
    """
    if expiration == _default_expiration_duration_opt:
        duration = _default_expiration_duration()
        expiration = duration + datetime.now() if duration else None

    token_code = random_string_generator(TOKEN_NAME_PREFIX_LENGTH + MINIMUM_TOKEN_SUFFIX_LENGTH)()
    token_name = token_code[:TOKEN_NAME_PREFIX_LENGTH]
    token_secret = token_code[TOKEN_NAME_PREFIX_LENGTH:]

    assert token_name
    assert token_secret

    return AppSpecificAuthToken.create(
        user=user,
        title=title,
        expiration=expiration,
        token_name=token_name,
        token_secret=DecryptedValue(token_secret),
    )


def list_tokens(user):
    """
    Lists all tokens for the given user.
    """
    return AppSpecificAuthToken.select().where(AppSpecificAuthToken.user == user)


def revoke_token(token):
    """
    Revokes an app specific token by deleting it.
    """
    token.delete_instance()


def revoke_token_by_uuid(uuid, owner):
    """
    Revokes an app specific token by deleting it.
    """
    try:
        token = AppSpecificAuthToken.get(uuid=uuid, user=owner)
    except AppSpecificAuthToken.DoesNotExist:
        return None

    revoke_token(token)
    return token


def get_expiring_tokens(user, soon):
    """
    Returns all tokens owned by the given user that will be expiring "soon", where soon is defined
    by the soon parameter (a timedelta from now).
    """
    soon_datetime = datetime.now() + soon
    return AppSpecificAuthToken.select().where(
        AppSpecificAuthToken.user == user,
        AppSpecificAuthToken.expiration <= soon_datetime,
        AppSpecificAuthToken.expiration > datetime.now(),
    )


def gc_expired_tokens(expiration_window):
    """
    Deletes all expired tokens outside of the expiration window.
    """
    (
        AppSpecificAuthToken.delete()
        .where(AppSpecificAuthToken.expiration < (datetime.now() - expiration_window))
        .execute()
    )


def get_token_by_uuid(uuid, owner=None):
    """
    Looks up an unexpired app specific token with the given uuid.

    Returns it if found or None if none. If owner is specified, only tokens owned by the owner user
    will be returned.
    """
    try:
        query = AppSpecificAuthToken.select().where(
            AppSpecificAuthToken.uuid == uuid,
            (
                (AppSpecificAuthToken.expiration > datetime.now())
                | (AppSpecificAuthToken.expiration >> None)
            ),
        )
        if owner is not None:
            query = query.where(AppSpecificAuthToken.user == owner)

        return query.get()
    except AppSpecificAuthToken.DoesNotExist:
        return None


def access_valid_token(token_code):
    """
    Looks up an unexpired app specific token with the given token code.

    If found, the token's last_accessed field is set to now and the token is returned. If not found,
    returns None.
    """
    token_code = remove_unicode(Bytes.for_string_or_unicode(token_code).as_encoded_str())

    prefix = token_code[:TOKEN_NAME_PREFIX_LENGTH]
    if len(prefix) != TOKEN_NAME_PREFIX_LENGTH:
        return None

    suffix = token_code[TOKEN_NAME_PREFIX_LENGTH:]

    # Lookup the token by its prefix.
    try:
        token = (
            AppSpecificAuthToken.select(AppSpecificAuthToken, User)
            .join(User)
            .where(
                AppSpecificAuthToken.token_name == prefix,
                (
                    (AppSpecificAuthToken.expiration > datetime.now())
                    | (AppSpecificAuthToken.expiration >> None)
                ),
            )
            .get()
        )

        if not token.token_secret.matches(suffix):
            return None

        assert len(prefix) == TOKEN_NAME_PREFIX_LENGTH
        assert len(suffix) >= MINIMUM_TOKEN_SUFFIX_LENGTH
        update_last_accessed(token)
        return token
    except AppSpecificAuthToken.DoesNotExist:
        pass

    return None


def get_full_token_string(token):
    assert token.token_name
    return "%s%s" % (token.token_name, token.token_secret.decrypt())
