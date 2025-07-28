import pytest

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
