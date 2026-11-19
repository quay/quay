import pytest

from util.security.registry_jwt import _generate_jwt_object


@pytest.mark.parametrize(
    "reserved_field",
    ["iss", "aud", "nbf", "iat", "exp", "sub", "access", "context"],
)
def test_generate_jwt_rejects_reserved_extra_fields(reserved_field):
    with pytest.raises(ValueError, match="extra_fields cannot override JWT fields"):
        _generate_jwt_object(
            "audience",
            "subject",
            {},
            [],
            300,
            "issuer",
            "key-id",
            None,
            {reserved_field: "overridden"},
        )


def test_generate_jwt_allows_custom_extra_fields(monkeypatch):
    monkeypatch.setattr(
        "util.security.registry_jwt.jwt.encode",
        lambda token_data, *_args, **_kwargs: token_data,
    )

    token_data = _generate_jwt_object(
        "audience",
        "subject",
        {},
        [],
        300,
        "issuer",
        "key-id",
        None,
        {"federation": {"issuer": "https://issuer.example.com"}},
    )

    assert token_data["federation"] == {"issuer": "https://issuer.example.com"}
