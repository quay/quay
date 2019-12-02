import pytest

from auth.auth_context_type import SignedAuthContext, ValidatedAuthContext, ContextEntityKind
from data import model, database

from test.fixtures import *


def get_oauth_token(_):
    return database.OAuthAccessToken.get()


@pytest.mark.parametrize(
    "kind, entity_reference, loader",
    [
        (ContextEntityKind.anonymous, None, None),
        (
            ContextEntityKind.appspecifictoken,
            "%s%s" % ("a" * 60, "b" * 60),
            model.appspecifictoken.access_valid_token,
        ),
        (ContextEntityKind.oauthtoken, None, get_oauth_token),
        (ContextEntityKind.robot, "devtable+dtrobot", model.user.lookup_robot),
        (ContextEntityKind.user, "devtable", model.user.get_user),
    ],
)
@pytest.mark.parametrize("v1_dict_format", [(True), (False),])
def test_signed_auth_context(kind, entity_reference, loader, v1_dict_format, initialized_db):
    if kind == ContextEntityKind.anonymous:
        validated = ValidatedAuthContext()
        assert validated.is_anonymous
    else:
        ref = loader(entity_reference)
        validated = ValidatedAuthContext(**{kind.value: ref})
        assert not validated.is_anonymous

    assert validated.entity_kind == kind
    assert validated.unique_key

    signed = SignedAuthContext.build_from_signed_dict(
        validated.to_signed_dict(), v1_dict_format=v1_dict_format
    )

    if not v1_dict_format:
        # Under legacy V1 format, we don't track the app specific token, merely its associated user.
        assert signed.entity_kind == kind
        assert signed.description == validated.description
        assert signed.credential_username == validated.credential_username
        assert (
            signed.analytics_id_and_public_metadata()
            == validated.analytics_id_and_public_metadata()
        )
        assert signed.unique_key == validated.unique_key

    assert signed.is_anonymous == validated.is_anonymous
    assert signed.authed_user == validated.authed_user
    assert signed.has_nonrobot_user == validated.has_nonrobot_user

    assert signed.to_signed_dict() == validated.to_signed_dict()
