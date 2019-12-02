import pytest

from auth.signedgrant import validate_signed_grant, generate_signed_token, SIGNATURE_PREFIX
from auth.validateresult import AuthKind, ValidateResult


@pytest.mark.parametrize(
    "header, expected_result",
    [
        pytest.param("", ValidateResult(AuthKind.signed_grant, missing=True), id="Missing"),
        pytest.param(
            "somerandomtoken",
            ValidateResult(AuthKind.signed_grant, missing=True),
            id="Invalid header",
        ),
        pytest.param(
            "token somerandomtoken",
            ValidateResult(AuthKind.signed_grant, missing=True),
            id="Random Token",
        ),
        pytest.param(
            "token " + SIGNATURE_PREFIX + "foo",
            ValidateResult(
                AuthKind.signed_grant, error_message="Signed grant could not be validated"
            ),
            id="Invalid token",
        ),
    ],
)
def test_token(header, expected_result):
    assert validate_signed_grant(header) == expected_result


def test_valid_grant():
    header = "token " + generate_signed_token({"a": "b"}, {"c": "d"})
    expected = ValidateResult(
        AuthKind.signed_grant, signed_data={"grants": {"a": "b",}, "user_context": {"c": "d"},}
    )
    assert validate_signed_grant(header) == expected
