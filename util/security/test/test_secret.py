import uuid
import pytest

from util.security.secret import convert_secret_key


@pytest.mark.parametrize(
    "config_secret_key, expected_secret_key",
    [
        pytest.param("somesecretkey", b"somesecretkeysomesecretkeysomese", id="Some string"),
        pytest.param("255", b"\xff" * 32, id="Some int that can be represented as a byte",),
        pytest.param(
            "256",
            b"25625625625625625625625625625625",
            id="Some int that can't be represented as a byte multiple (256 is 100 in hex -> 12 bits)",
        ),
        pytest.param(
            "123e4567-e89b-12d3-a456-426655440000",
            uuid.UUID("123e4567-e89b-12d3-a456-426655440000").bytes * 2,
            id="Some 16bit UUID",
        ),
    ],
)
def test_convert_secret_key(config_secret_key, expected_secret_key):
    converted_secret_key = convert_secret_key(config_secret_key)

    assert len(converted_secret_key) == 32
    assert isinstance(converted_secret_key, bytes)
    assert converted_secret_key == expected_secret_key
