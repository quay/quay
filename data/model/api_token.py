"""Lifecycle and JWT helpers for Quay-issued API tokens."""

from contextlib import nullcontext
from datetime import datetime, timedelta
from math import isfinite

from auth import scopes
from data.database import APIToken, User, db_for_update, random_string_generator
from data.fields import Credential
from data.model import config, db_transaction
from data.readreplica import ReadOnlyModeException
from util.security.registry_jwt import generate_bearer_token

API_TOKEN_DEFAULT_EXPIRATION_SECONDS = 60 * 60 * 24 * 30
API_TOKEN_MAX_EXPIRATION_SECONDS = 60 * 60 * 24 * 90
MAX_API_TOKEN_DISPLAY_NAME_LENGTH = 255
API_TOKEN_PREFIX = "qro_"
API_TOKEN_NAME_LENGTH = 20
API_TOKEN_CODE_LENGTH = 40


def normalize_scope(scope_string):
    return " ".join(dict.fromkeys(scope_string.replace(",", " ").split()))


def validate_api_scope_string(scope_string):
    scope_set = scopes.scopes_from_scope_string(scope_string)
    return bool(scope_set) and scopes.DIRECT_LOGIN not in scope_set


def validate_token_display_name(value):
    if not isinstance(value, str):
        raise ValueError("'name' must be a string")
    value = value.strip()
    if not value:
        raise ValueError("'name' cannot be empty")
    if len(value) > MAX_API_TOKEN_DISPLAY_NAME_LENGTH:
        raise ValueError("'name' is too long")
    return value


class TokenLimitExceeded(Exception):
    def __init__(self, max_active_tokens):
        self.max_active_tokens = max_active_tokens
        super().__init__("maximum %d active API tokens per subject" % max_active_tokens)


def validate_expiration(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or (isinstance(value, float) and not isfinite(value))
        or value <= 0
    ):
        raise ValueError("'expiration' must be a positive number of seconds")
    return min(max(int(value), 1), API_TOKEN_MAX_EXPIRATION_SECONDS)


def count_active_tokens(subject_user):
    return (
        APIToken.select()
        .where(
            APIToken.subject_user == subject_user,
            APIToken.revoked_at.is_null(),
            APIToken.expires_at > datetime.utcnow(),
        )
        .count()
    )


def create_token_under_limit(subject_user, creator, scope, expiration_seconds, display_name):
    scope = normalize_scope(scope)
    if not validate_api_scope_string(scope):
        raise ValueError("'scope' must include at least one API scope")

    max_active_tokens = (config.app_config or {}).get("API_TOKEN_MAXIMUM_TOKEN_COUNT")
    transaction = db_transaction() if max_active_tokens is not None else nullcontext()
    with transaction:
        if max_active_tokens is not None:
            subject_user = db_for_update(User.select().where(User.id == subject_user.id)).get()
            if count_active_tokens(subject_user) >= int(max_active_tokens):
                raise TokenLimitExceeded(int(max_active_tokens))
        token_name = API_TOKEN_PREFIX + random_string_generator(API_TOKEN_NAME_LENGTH)()
        token_code = random_string_generator(API_TOKEN_CODE_LENGTH)()
        token = APIToken.create(
            subject_user=subject_user,
            creator=creator,
            token_name=token_name,
            token_code=Credential.from_string(token_code),
            scope=normalize_scope(scope),
            display_name=display_name,
            expires_at=datetime.utcnow() + timedelta(seconds=expiration_seconds),
        )
        return token, token_name + token_code


def mint_jwt(token, instance_keys, audience):
    lifetime = max(int((token.expires_at - datetime.utcnow()).total_seconds()), 1)
    return generate_bearer_token(
        audience,
        token.subject_user.username,
        {},
        {},
        lifetime,
        instance_keys,
        {"api_scopes": token.scope, "jti": token.uuid},
    )


def list_tokens(subject_user):
    return list(
        APIToken.select()
        .where(APIToken.subject_user == subject_user, APIToken.revoked_at.is_null())
        .order_by(APIToken.created.desc())
    )


def revoke_token(subject_user, token_uuid):
    return (
        APIToken.update(revoked_at=datetime.utcnow())
        .where(
            APIToken.subject_user == subject_user,
            APIToken.uuid == token_uuid,
            APIToken.revoked_at.is_null(),
        )
        .execute()
        > 0
    )


def _update_last_accessed(token):
    now = datetime.utcnow()
    threshold = timedelta(
        seconds=config.app_config.get("OAUTH_TOKEN_LAST_ACCESSED_UPDATE_THRESHOLD_S", 60)
    )
    if token.last_accessed is not None and now - token.last_accessed < threshold:
        return
    try:
        APIToken.update(last_accessed=now).where(APIToken.id == token.id).execute()
        token.last_accessed = now
    except ReadOnlyModeException:
        pass


def validate_token(token_string):
    if not token_string.startswith(API_TOKEN_PREFIX):
        return None

    token_name_length = len(API_TOKEN_PREFIX) + API_TOKEN_NAME_LENGTH
    token_name = token_string[:token_name_length]
    token_code = token_string[token_name_length:]
    if not token_code:
        return None

    try:
        token = APIToken.get(APIToken.token_name == token_name, APIToken.revoked_at.is_null())
    except APIToken.DoesNotExist:
        return None

    if token.expires_at <= datetime.utcnow() or not token.token_code.matches(token_code):
        return None

    _update_last_accessed(token)
    return token
