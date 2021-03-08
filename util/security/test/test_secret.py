import json
import uuid
import pytest

from util.security.aes import AESCipher
from util.security.secret import convert_secret_key


@pytest.mark.parametrize(
    "config_secret_key, expected_secret_key",
    [
        pytest.param("somesecretkey", b"somesecretkeysomesecretkeysomese", id="Some string"),
        pytest.param(
            "255",
            b"\xff" * 32,
            id="Some int that can be represented as a byte",
        ),
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


@pytest.mark.parametrize(
    "secret_key, encrypted_msg, expected_msg",
    [
        pytest.param(
            "60819670227914197377449333332023941570310823814007397361459893170384762698201",
            "cLJIuEm7radxwXwqoOG/9yXYxWW8JFCvgssBP3fHDatx/ckLrX9fZ4lZVj6WEv0D",
            json.dumps({"password": "password"}).encode("utf-8"),
            id="Test decrypt some existing msg",
        ),
    ],
)
def test_aes_decrypt(secret_key, encrypted_msg, expected_msg):
    converted_secret_key = convert_secret_key(secret_key)
    cipher = AESCipher(converted_secret_key)
    decrypted_msg = cipher.decrypt(encrypted_msg)

    assert decrypted_msg == expected_msg


@pytest.mark.parametrize(
    "secret_key, original_msg",
    [
        pytest.param("somesecretkey", b"some secret message", id="Some string"),
        pytest.param(
            "255",
            b"another secret message",
            id="Some int that can be represented as a byte",
        ),
        pytest.param(
            "256",
            b"yet another secret message",
            id="Some int that can't be represented as a byte multiple (256 is 100 in hex -> 12 bits)",
        ),
        pytest.param(
            "123e4567-e89b-12d3-a456-426655440000",
            b"yet again another secret message",
            id="Some 16bit UUID",
        ),
    ],
)
def test_aes_encrypt_decrypt(secret_key, original_msg):
    converted_secret_key = convert_secret_key(secret_key)
    cipher = AESCipher(converted_secret_key)
    encrypted_msg = cipher.encrypt(original_msg)

    assert cipher.decrypt(encrypted_msg) == original_msg
