import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from peewee import PeeweeException

from app import instance_keys
from auth.auth_context_type import ValidatedAuthContext
from auth.oauth import validate_bearer_auth
from auth.validateresult import AuthKind, ValidateResult
from data import model
from data.database import APIToken, FederatedLogin, User
from data.model import api_token
from data.model import config as model_config
from data.model.user import (
    TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
    generate_federated_robot_jwt_token,
)
from data.readreplica import ReadOnlyModeException
from test.fixtures import *
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token


@pytest.mark.parametrize(
    "header, expected_result",
    [
        ("", ValidateResult(AuthKind.oauth, missing=True)),
        ("somerandomtoken", ValidateResult(AuthKind.oauth, missing=True)),
        ("bearer some random token", ValidateResult(AuthKind.oauth, missing=True)),
        (
            "bearer invalidtoken",
            ValidateResult(
                AuthKind.oauth, error_message="OAuth access token could not be validated"
            ),
        ),
    ],
)
def test_bearer(header, expected_result, app):
    assert validate_bearer_auth(header) == expected_result


def test_valid_oauth(app):
    user = model.user.get_user("devtable")
    app = model.oauth.list_applications_for_org(model.user.get_user_or_org("buynlarge"))[0]
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, app.client_id, "repo:read", access_token=token_string
    )
    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken == oauth_token
    assert result.authed_user == user
    assert result.auth_valid


def test_robot_api_token_authenticates_as_its_robot(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("api-token", creator)
    token, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "CI token"
    )

    assert secret.startswith(api_token.API_TOKEN_PREFIX)
    assert token.token_code.matches(secret[len(token.token_name) :])

    result = validate_bearer_auth("Bearer " + secret)

    assert result.context.robot == robot
    assert result.context.api_scopes == "repo:read"
    assert result.context.api_token == token
    assert result.authed_user == robot
    assert result.auth_valid

    with patch("features.ROBOT_API_TOKENS", False):
        disabled_result = validate_bearer_auth("Bearer " + secret)
    assert not disabled_result.auth_valid
    assert disabled_result.error_message == "API token is invalid, revoked or expired"

    assert api_token.revoke_token(robot, token.uuid)
    revoked_result = validate_bearer_auth("Bearer " + secret)
    assert not revoked_result.auth_valid
    assert revoked_result.error_message == "API token is invalid, revoked or expired"


@pytest.mark.parametrize(
    "whitelist, expected_valid",
    [
        ([], False),
        (lambda robot: [robot.username], True),
        (lambda robot: [robot.username + "-suffix"], False),
    ],
)
def test_robot_api_credentials_respect_robot_access_policy(app, whitelist, expected_valid):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("policy-api-token", creator)
    _, opaque_token = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "Policy token"
    )
    binding = model.user.create_robot_federation_config(
        robot,
        [
            {
                "issuer": "https://issuer.example",
                "subject": robot.username,
                "api_scopes": "repo:read",
            }
        ],
    )[0]
    jwt_token = generate_federated_robot_jwt_token(instance_keys, robot, "repo:read", binding)
    whitelist = whitelist(robot) if callable(whitelist) else whitelist

    with patch.dict(
        model_config.app_config,
        {"ROBOTS_DISALLOW": True, "ROBOTS_WHITELIST": whitelist},
    ):
        for token in (opaque_token, jwt_token):
            assert validate_bearer_auth("Bearer " + token).auth_valid is expected_valid


LEGACY_FEDERATION_BINDINGS = [
    {
        "issuer": "https://issuer.example",
        "subject": "system:serviceaccount:ci:builder-a",
        "audiences": ["quay"],
        "api_scopes": "repo:read",
    },
    {
        "issuer": "https://issuer.example",
        "subject": "system:serviceaccount:ci:builder-b",
        "audiences": ["quay"],
        "api_scopes": "repo:read",
    },
]


def _store_legacy_federation_config(robot, bindings):
    """Write bindings in the pre-id JSON shape (no id, no version) straight into the row."""
    federated = FederatedLogin.get(FederatedLogin.user == robot)
    federated.metadata_json = json.dumps({"federation_config": bindings})
    federated.save()


def test_removed_legacy_federation_binding_token_is_rejected(app):
    # PROJQUAY-13549: two legacy bindings must stay independently revocable.
    robot, _ = model.user.create_robot("federated-revoke", model.user.get_user("devtable"))
    _store_legacy_federation_config(robot, [dict(b) for b in LEGACY_FEDERATION_BINDINGS])
    saved = model.user.create_robot_federation_config(
        robot, model.user.get_robot_federation_config(robot)
    )
    assert all(binding["id"] for binding in saved)
    assert len({binding["id"] for binding in saved}) == 2

    token_a = generate_federated_robot_jwt_token(instance_keys, robot, "repo:read", saved[0])
    token_b = generate_federated_robot_jwt_token(instance_keys, robot, "repo:read", saved[1])
    assert validate_bearer_auth("Bearer " + token_a).context.federation_binding == saved[0]
    assert validate_bearer_auth("Bearer " + token_b).context.federation_binding == saved[1]

    model.user.create_robot_federation_config(robot, [saved[1]])

    revoked = validate_bearer_auth("Bearer " + token_a)
    assert not revoked.auth_valid
    assert revoked.error_message == "Federation binding is no longer valid"
    retained = validate_bearer_auth("Bearer " + token_b)
    assert retained.auth_valid
    assert retained.context.federation_binding == saved[1]


def test_federated_robot_jwt_with_null_binding_identity_is_rejected(app):
    robot, _ = model.user.create_robot("federated-null", model.user.get_user("devtable"))
    _store_legacy_federation_config(robot, [dict(b) for b in LEGACY_FEDERATION_BINDINGS])

    # A token minted by a pre-fix build carries null binding claims; it must not resolve
    # against a stored binding that still lacks an id.
    context, subject = build_context_and_subject(ValidatedAuthContext(robot=robot))
    token = generate_bearer_token(
        model_config.app_config["SERVER_HOSTNAME"],
        subject,
        context,
        {},
        TMP_ROBOT_TOKEN_VALIDITY_LIFETIME_S,
        instance_keys,
        {
            "api_scopes": "repo:read",
            "federation_binding_id": None,
            "federation_binding_version": None,
        },
    )

    result = validate_bearer_auth("Bearer " + token)

    assert not result.auth_valid
    assert result.error_message == "Federation binding is no longer valid"


@pytest.mark.parametrize("allow_without_strict_logging", [True, False])
def test_robot_api_token_last_accessed_write_failure_respects_strict_logging(
    app, allow_without_strict_logging
):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("last-accessed-token", creator)
    token, _ = api_token.create_token_under_limit(robot, creator, "repo:read", 3600, "CI token")

    with (
        patch.dict(
            api_token.config.app_config,
            {
                "ALLOW_WITHOUT_STRICT_LOGGING": allow_without_strict_logging,
                "ALLOW_PULLS_WITHOUT_STRICT_LOGGING": False,
                "OAUTH_TOKEN_LAST_ACCESSED_UPDATE_THRESHOLD_S": 0,
            },
        ),
        patch.object(
            api_token.APIToken,
            "update",
            side_effect=PeeweeException("last_accessed update failed"),
        ),
    ):
        if allow_without_strict_logging:
            api_token._update_last_accessed(token)
        else:
            with pytest.raises(PeeweeException, match="last_accessed update failed"):
                api_token._update_last_accessed(token)


@pytest.mark.parametrize("scope", ["", "   ", "direct_user_login"])
def test_robot_api_token_requires_a_non_direct_api_scope(app, scope):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("scoped-api-token", creator)

    with pytest.raises(ValueError, match="must include at least one API scope"):
        api_token.create_token_under_limit(robot, creator, scope, 3600, "Invalid token")


def test_robot_api_token_creation_validates_expiration(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("expiring-api-token", creator)

    with pytest.raises(ValueError, match="positive number of seconds"):
        api_token.create_token_under_limit(robot, creator, "repo:read", 0, "Invalid token")

    token, _ = api_token.create_token_under_limit(
        robot,
        creator,
        "repo:read",
        api_token.API_TOKEN_MAX_EXPIRATION_SECONDS + 3600,
        "Capped token",
    )
    assert (
        0
        < (token.expires_at - datetime.utcnow()).total_seconds()
        <= (api_token.API_TOKEN_MAX_EXPIRATION_SECONDS)
    )


def test_robot_api_token_with_persisted_empty_scope_is_rejected(app):
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("empty-scope-token", creator)
    token, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "CI token"
    )
    token.scope = " "
    token.save()

    result = validate_bearer_auth("Bearer " + secret)

    assert not result.auth_valid
    assert result.error_message == "API token has invalid scopes"


def test_disabled_user_oauth(app):
    user = model.user.get_user("disabled")
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, "deadbeef", "repo:admin", access_token=token_string
    )

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken is None
    assert result.authed_user is None
    assert not result.auth_valid
    assert result.error_message == "Granter of the oauth access token is disabled"


def test_expired_token(app):
    user = model.user.get_user("devtable")
    token_string = "%s%s" % ("a" * 20, "b" * 20)
    oauth_token, _ = model.oauth.create_user_access_token(
        user, "deadbeef", "repo:admin", access_token=token_string, expires_in=-1000
    )

    result = validate_bearer_auth("bearer " + token_string)
    assert result.context.oauthtoken is None
    assert result.authed_user is None
    assert not result.auth_valid
    assert result.error_message == "OAuth access token has expired"


def _reload_robot(robot):
    return User.get(User.id == robot.id)


def test_robot_api_token_bearer_auth_updates_robot_last_accessed(app):
    # PROJQUAY-13785: the robot user's last_accessed must move when its API token is used,
    # not only the token's own last_accessed.
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("token-last-accessed", creator)
    token, secret = api_token.create_token_under_limit(
        robot, creator, "repo:read", 3600, "CI token"
    )
    assert _reload_robot(robot).last_accessed is None

    before = datetime.utcnow()
    result = validate_bearer_auth("Bearer " + secret)

    assert result.auth_valid
    assert result.authed_user == robot
    refreshed = _reload_robot(robot)
    assert refreshed.last_accessed is not None
    assert refreshed.last_accessed >= before.replace(microsecond=0)
    assert APIToken.get(APIToken.id == token.id).last_accessed is not None


def test_federated_robot_jwt_updates_robot_last_accessed(app):
    # PROJQUAY-13785: a Quay-signed robot JWT (federation token exchange) is also a robot
    # credential and must record robot use.
    robot, _ = model.user.create_robot("jwt-last-accessed", model.user.get_user("devtable"))
    _store_legacy_federation_config(robot, [dict(b) for b in LEGACY_FEDERATION_BINDINGS])
    saved = model.user.create_robot_federation_config(
        robot, model.user.get_robot_federation_config(robot)
    )
    jwt_token = generate_federated_robot_jwt_token(instance_keys, robot, "repo:read", saved[0])
    assert _reload_robot(robot).last_accessed is None

    result = validate_bearer_auth("Bearer " + jwt_token)

    assert result.auth_valid
    assert _reload_robot(robot).last_accessed is not None


def test_robot_api_token_last_accessed_is_throttled_like_password_auth(app):
    # PROJQUAY-13785: reuse the user last_accessed throttle, so a busy robot does not write
    # the user row on every request.
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("token-throttle", creator)
    _, secret = api_token.create_token_under_limit(robot, creator, "repo:read", 3600, "CI token")

    recent = datetime.utcnow().replace(microsecond=0) - timedelta(seconds=5)
    User.update(last_accessed=recent).where(User.id == robot.id).execute()
    with patch.dict(model_config.app_config, {"LAST_ACCESSED_UPDATE_THRESHOLD_S": 60}):
        assert validate_bearer_auth("Bearer " + secret).auth_valid
    assert _reload_robot(robot).last_accessed == recent

    stale = datetime.utcnow().replace(microsecond=0) - timedelta(days=1)
    User.update(last_accessed=stale).where(User.id == robot.id).execute()
    with patch.dict(model_config.app_config, {"LAST_ACCESSED_UPDATE_THRESHOLD_S": 60}):
        assert validate_bearer_auth("Bearer " + secret).auth_valid
    assert _reload_robot(robot).last_accessed > stale


def test_robot_api_token_auth_survives_read_only_user_update(app):
    # PROJQUAY-13785: in read-only mode the robot row cannot be written; auth must still pass.
    creator = model.user.get_user("devtable")
    robot, _ = model.user.create_robot("token-readonly", creator)
    _, secret = api_token.create_token_under_limit(robot, creator, "repo:read", 3600, "CI token")

    with (
        patch.object(User, "update", side_effect=ReadOnlyModeException("read only")),
        patch.object(APIToken, "update", side_effect=ReadOnlyModeException("read only")),
    ):
        result = validate_bearer_auth("Bearer " + secret)

    assert result.auth_valid
    assert _reload_robot(robot).last_accessed is None
