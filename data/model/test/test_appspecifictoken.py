from datetime import datetime, timedelta
from mock import patch

import pytest

from data.model import config as _config
from data import model
from data.model.appspecifictoken import create_token, revoke_token, access_valid_token
from data.model.appspecifictoken import gc_expired_tokens, get_expiring_tokens
from data.model.appspecifictoken import get_full_token_string
from util.timedeltastring import convert_to_timedelta

from test.fixtures import *


@pytest.mark.parametrize(
    "expiration", [(None), ("-1m"), ("-1d"), ("-1w"), ("10m"), ("10d"), ("10w"),]
)
def test_gc(expiration, initialized_db):
    user = model.user.get_user("devtable")

    expiration_date = None
    is_expired = False
    if expiration:
        if expiration[0] == "-":
            is_expired = True
            expiration_date = datetime.now() - convert_to_timedelta(expiration[1:])
        else:
            expiration_date = datetime.now() + convert_to_timedelta(expiration)

    # Create a token.
    token = create_token(user, "Some token", expiration=expiration_date)

    # GC tokens.
    gc_expired_tokens(timedelta(seconds=0))

    # Ensure the token was GCed if expired and not if it wasn't.
    assert (access_valid_token(get_full_token_string(token)) is None) == is_expired


def test_access_token(initialized_db):
    user = model.user.get_user("devtable")

    # Create a token.
    token = create_token(user, "Some token")
    assert token.last_accessed is None

    # Lookup the token.
    token = access_valid_token(get_full_token_string(token))
    assert token.last_accessed is not None

    # Revoke the token.
    revoke_token(token)

    # Ensure it cannot be accessed
    assert access_valid_token(get_full_token_string(token)) is None


def test_expiring_soon(initialized_db):
    user = model.user.get_user("devtable")

    # Create some tokens.
    create_token(user, "Some token")
    exp_token = create_token(
        user, "Some expiring token", datetime.now() + convert_to_timedelta("1d")
    )
    create_token(user, "Some other token", expiration=datetime.now() + convert_to_timedelta("2d"))

    # Get the token expiring soon.
    expiring_soon = get_expiring_tokens(user, convert_to_timedelta("25h"))
    assert expiring_soon
    assert len(expiring_soon) == 1
    assert expiring_soon[0].id == exp_token.id

    expiring_soon = get_expiring_tokens(user, convert_to_timedelta("49h"))
    assert expiring_soon
    assert len(expiring_soon) == 2


@pytest.fixture(scope="function")
def app_config():
    with patch.dict(_config.app_config, {}, clear=True):
        yield _config.app_config


@pytest.mark.parametrize("expiration", [(None), ("10m"), ("10d"), ("10w"),])
@pytest.mark.parametrize("default_expiration", [(None), ("10m"), ("10d"), ("10w"),])
def test_create_access_token(expiration, default_expiration, initialized_db, app_config):
    user = model.user.get_user("devtable")
    expiration_date = datetime.now() + convert_to_timedelta(expiration) if expiration else None
    with patch.dict(_config.app_config, {}, clear=True):
        app_config["APP_SPECIFIC_TOKEN_EXPIRATION"] = default_expiration
        if expiration:
            exp_token = create_token(user, "Some token", expiration=expiration_date)
            assert exp_token.expiration == expiration_date
        else:
            exp_token = create_token(user, "Some token")
            assert (exp_token.expiration is None) == (default_expiration is None)


@pytest.mark.parametrize(
    "invalid_token",
    [
        "",
        "foo",
        "a" * 40,
        "b" * 40,
        "%s%s" % ("b" * 40, "a" * 40),
        "%s%s" % ("a" * 39, "b" * 40),
        "%s%s" % ("a" * 40, "b" * 39),
        "%s%s" % ("a" * 40, "b" * 41),
    ],
)
def test_invalid_access_token(invalid_token, initialized_db):
    user = model.user.get_user("devtable")
    token = access_valid_token(invalid_token)
    assert token is None
