# -*- coding: utf-8 -*-

import time

import jwt
import pytest

from cryptography.hazmat.primitives import serialization

from app import app, instance_keys
from auth.auth_context_type import ValidatedAuthContext
from auth.registry_jwt_auth import identity_from_bearer_token, InvalidJWTException
from data import model  # TODO: remove this after service keys are decoupled
from data.database import ServiceKeyApprovalType
from initdb import setup_database_for_testing, finished_database_for_testing
from util.morecollections import AttrDict
from util.security.registry_jwt import ANONYMOUS_SUB, build_context_and_subject

TEST_AUDIENCE = app.config["SERVER_HOSTNAME"]
TEST_USER = AttrDict({"username": "joeuser", "uuid": "foobar", "enabled": True})
MAX_SIGNED_S = 3660
TOKEN_VALIDITY_LIFETIME_S = 60 * 60  # 1 hour
ANONYMOUS_SUB = "(anonymous)"
SERVICE_NAME = "quay"

# This import has to come below any references to "app".
from test.fixtures import *


def _access(typ="repository", name="somens/somerepo", actions=None):
    actions = [] if actions is None else actions
    return [
        {
            "type": typ,
            "name": name,
            "actions": actions,
        }
    ]


def _delete_field(token_data, field_name):
    token_data.pop(field_name)
    return token_data


def _token_data(
    access=[],
    context=None,
    audience=TEST_AUDIENCE,
    user=TEST_USER,
    iat=None,
    exp=None,
    nbf=None,
    iss=None,
    subject=None,
):
    if subject is None:
        _, subject = build_context_and_subject(ValidatedAuthContext(user=user))
    return {
        "iss": iss or instance_keys.service_name,
        "aud": audience,
        "nbf": nbf if nbf is not None else int(time.time()),
        "iat": iat if iat is not None else int(time.time()),
        "exp": exp if exp is not None else int(time.time() + TOKEN_VALIDITY_LIFETIME_S),
        "sub": subject,
        "access": access,
        "context": context,
    }


def _token(token_data, key_id=None, private_key=None, skip_header=False, alg=None):
    key_id = key_id or instance_keys.local_key_id
    private_key = private_key or instance_keys.local_private_key

    if alg == "none":
        private_key = None

    token_headers = {"kid": key_id}

    if skip_header:
        token_headers = {}

    token_data = jwt.encode(token_data, private_key, alg or "RS256", headers=token_headers)
    return "Bearer {0}".format(token_data.decode("ascii"))


def _parse_token(token):
    return identity_from_bearer_token(token)[0]


def test_accepted_token(initialized_db):
    token = _token(_token_data())
    identity = _parse_token(token)
    assert identity.id == TEST_USER.username, "should be %s, but was %s" % (
        TEST_USER.username,
        identity.id,
    )
    assert len(identity.provides) == 0

    anon_token = _token(_token_data(user=None))
    anon_identity = _parse_token(anon_token)
    assert anon_identity.id == ANONYMOUS_SUB, "should be %s, but was %s" % (
        ANONYMOUS_SUB,
        anon_identity.id,
    )
    assert len(identity.provides) == 0


@pytest.mark.parametrize(
    "access",
    [
        (_access(actions=["pull", "push"])),
        (_access(actions=["pull", "*"])),
        (_access(actions=["*", "push"])),
        (_access(actions=["*"])),
        (_access(actions=["pull", "*", "push"])),
    ],
)
def test_token_with_access(access, initialized_db):
    token = _token(_token_data(access=access))
    identity = _parse_token(token)
    assert identity.id == TEST_USER.username, "should be %s, but was %s" % (
        TEST_USER.username,
        identity.id,
    )
    assert len(identity.provides) == 1

    role = list(identity.provides)[0][3]
    if "*" in access[0]["actions"]:
        assert role == "admin"
    elif "push" in access[0]["actions"]:
        assert role == "write"
    elif "pull" in access[0]["actions"]:
        assert role == "read"


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(
            _token(
                _token_data(
                    access=[
                        {
                            "toipe": "repository",
                            "namesies": "somens/somerepo",
                            "akshuns": ["pull", "push", "*"],
                        }
                    ]
                )
            ),
            id="bad access",
        ),
        pytest.param(_token(_token_data(audience="someotherapp")), id="bad aud"),
        pytest.param(_token(_delete_field(_token_data(), "aud")), id="no aud"),
        pytest.param(_token(_token_data(nbf=int(time.time()) + 600)), id="future nbf"),
        pytest.param(_token(_delete_field(_token_data(), "nbf")), id="no nbf"),
        pytest.param(_token(_token_data(iat=int(time.time()) + 600)), id="future iat"),
        pytest.param(_token(_delete_field(_token_data(), "iat")), id="no iat"),
        pytest.param(
            _token(_token_data(exp=int(time.time()) + MAX_SIGNED_S * 2)), id="exp too long"
        ),
        pytest.param(_token(_token_data(exp=int(time.time()) - 60)), id="expired"),
        pytest.param(_token(_delete_field(_token_data(), "exp")), id="no exp"),
        pytest.param(_token(_delete_field(_token_data(), "sub")), id="no sub"),
        pytest.param(_token(_token_data(iss="badissuer")), id="bad iss"),
        pytest.param(_token(_delete_field(_token_data(), "iss")), id="no iss"),
        pytest.param(_token(_token_data(), skip_header=True), id="no header"),
        pytest.param(_token(_token_data(), key_id="someunknownkey"), id="bad key"),
        pytest.param(_token(_token_data(), key_id="kid7"), id="bad key :: kid7"),
        pytest.param(_token(_token_data(), alg="none", private_key=None), id="none alg"),
        pytest.param("some random token", id="random token"),
        pytest.param("Bearer: sometokenhere", id="extra bearer"),
        pytest.param("\nBearer: dGVzdA", id="leading newline"),
    ],
)
def test_invalid_jwt(token, initialized_db):
    with pytest.raises(InvalidJWTException):
        _parse_token(token)


def test_mixing_keys_e2e(initialized_db):
    token_data = _token_data()

    # Create a new key for testing.
    p, key = model.service_keys.generate_service_key(
        instance_keys.service_name, None, kid="newkey", name="newkey", metadata={}
    )
    private_key = p.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Test first with the new valid, but unapproved key.
    unapproved_key_token = _token(token_data, key_id="newkey", private_key=private_key)
    with pytest.raises(InvalidJWTException):
        _parse_token(unapproved_key_token)

    # Approve the key and try again.
    admin_user = model.user.get_user("devtable")
    model.service_keys.approve_service_key(
        key.kid, ServiceKeyApprovalType.SUPERUSER, approver=admin_user
    )

    valid_token = _token(token_data, key_id="newkey", private_key=private_key)

    identity = _parse_token(valid_token)
    assert identity.id == TEST_USER.username
    assert len(identity.provides) == 0

    # Try using a different private key with the existing key ID.
    bad_private_token = _token(
        token_data, key_id="newkey", private_key=instance_keys.local_private_key
    )
    with pytest.raises(InvalidJWTException):
        _parse_token(bad_private_token)

    # Try using a different key ID with the existing private key.
    kid_mismatch_token = _token(
        token_data, key_id=instance_keys.local_key_id, private_key=private_key
    )
    with pytest.raises(InvalidJWTException):
        _parse_token(kid_mismatch_token)

    # Delete the new key.
    key.delete_instance(recursive=True)

    # Ensure it still works (via the cache.)
    deleted_key_token = _token(token_data, key_id="newkey", private_key=private_key)
    identity = _parse_token(deleted_key_token)
    assert identity.id == TEST_USER.username
    assert len(identity.provides) == 0

    # Break the cache.
    instance_keys.clear_cache()

    # Ensure the key no longer works.
    with pytest.raises(InvalidJWTException):
        _parse_token(deleted_key_token)


@pytest.mark.parametrize(
    "token",
    [
        "someunicodetoken✡",
        "\xc9\xad\xbd",
    ],
)
def test_unicode_token(token):
    with pytest.raises(InvalidJWTException):
        _parse_token(token)
