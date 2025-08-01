import pytest

from oauth.login import OAuthLoginException
from oauth.login_utils import get_sub_username_email_from_token
from oauth.services.rhsso import RHSSOOAuthService


@pytest.fixture
def rhsso_service():
    config = {"RHSSO_LOGIN_CONFIG": {}}
    return RHSSOOAuthService(config, "RHSSO_LOGIN_CONFIG")


def test_get_user_id_with_digit_sub_returns_deprecated_sub(rhsso_service):
    """Test that when sub is a digit, deprecated_sub is returned."""
    decoded_token = {
        "sub": "12345678",
        "deprecated_sub": "f:uuid-1234:original_username",
    }

    result = rhsso_service.get_user_id(decoded_token)
    assert result == "f:uuid-1234:original_username"


def test_get_user_id_with_digit_sub_missing_deprecated_sub_returns_sub(rhsso_service):
    """Test fallback to sub when deprecated_sub is missing."""
    decoded_token = {
        "sub": "87654321",
    }

    result = rhsso_service.get_user_id(decoded_token)
    assert result == "87654321"


def test_get_user_id_missing_sub_field_raises_exception(rhsso_service):
    """Test that missing sub field raises OAuthLoginException."""
    decoded_token = {
        "deprecated_sub": "f:uuid-1234:original_username",
    }

    with pytest.raises(OAuthLoginException, match="Token missing 'sub' field"):
        rhsso_service.get_user_id(decoded_token)


def test_get_sub_username_email_with_login_service(rhsso_service):
    """Test get_sub_username_email_from_token with login_service provided."""
    decoded_token = {
        "sub": "12345678",
        "deprecated_sub": "f:uuid-1234:original_username",
        "email": "test@example.com",
        "email_verified": True,
    }

    user_id, username, email, additional_info = get_sub_username_email_from_token(
        decoded_token, login_service=rhsso_service
    )

    # Should use the RHSSO service's get_user_id which returns deprecated_sub
    assert user_id == "f:uuid-1234:original_username"
