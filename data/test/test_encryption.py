# -*- coding: utf-8 -*-

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from data.encryption import (
    _VERSIONS,
    DecryptionFailureException,
    FieldEncrypter,
    aes256_encrypt,
)


@pytest.mark.parametrize(
    "test_data",
    [
        "",
        "hello world",
        "wassup?!",
        "IGZ2Y8KUN3EFWAZZXR3D7U4V5NXDVYZI5VGU6STPB6KM83PAB8WRGM32RD9FW0C0",
        "JLRFBYS1EHKUE73S99HWOQWNPGLUZTBRF5HQEFUJS5BK3XVB54RNXYV4AUMJXCMC",
        "a" * 3,
        "a" * 4,
        "a" * 5,
        "a" * 31,
        "a" * 32,
        "a" * 33,
        "a" * 150,
        "😇",
    ],
)
@pytest.mark.parametrize("version", list(_VERSIONS.keys()))
@pytest.mark.parametrize(
    "secret_key",
    [
        "test1234",
        "thisisanothercoolsecretkeyhere",
        "107383705745765174750346070528443780244192102846031525796571939503548634055845",
    ],
)
@pytest.mark.parametrize(
    "use_valid_key",
    [
        True,
        False,
    ],
)
def test_encryption(test_data, version, secret_key, use_valid_key):
    encrypter = FieldEncrypter(secret_key, version)
    encrypted = encrypter.encrypt_value(test_data, field_max_length=255)
    assert encrypted != test_data

    if use_valid_key:
        decrypted = encrypter.decrypt_value(encrypted)
        assert decrypted == test_data

        with pytest.raises(DecryptionFailureException):
            encrypter.decrypt_value("somerandomvalue")
    else:
        decrypter = FieldEncrypter("some other key", version)
        with pytest.raises(DecryptionFailureException):
            decrypter.decrypt_value(encrypted)


@pytest.mark.parametrize(
    "secret_key, encrypted_value, expected_decrypted_value",
    [
        ("test1234", "v0$$iE+87Qefu/2i+5zC87nlUtOskypk8MUUDS/QZPs=", ""),
        ("test1234", "v0$$XTxqlz/Kw8s9WKw+GaSvXFEKgpO/a2cGNhvnozzkaUh4C+FgHqZqnA==", "hello world"),
        (
            "test1234",
            "v0$$9LadVsSvfAr9r1OvghSYcJqrJpv46t+U6NgLKrcFY6y2bQsASIN36g==",
            "hello world",
        ),
        (
            "\1\2\3\4\5\6",
            "v0$$2wwWX8IhUYzuh4cyMgSXF3MEVDlEhrf0CNimTghlHgCuK6E4+bLJb1xJOKxsXMs=",
            "hello world, again",
        ),
    ],
)
def test_encryption_value(secret_key, encrypted_value, expected_decrypted_value):
    encrypter = FieldEncrypter(secret_key)
    decrypted = encrypter.decrypt_value(encrypted_value)

    assert decrypted == expected_decrypted_value


@pytest.mark.parametrize(
    "value, secret_key, iv",
    # secret_key generated as os.urandom(16).hex()
    [
        (
            "hello_world",
            "b430fbcf015adcf6db6d968f702710c0",
            b"!\x9e\xc06\xd3\x9d\x89\xa3\x90\x93\x85\xba\xae\x84Z\xc4",
        ),
        (
            "test1234",
            "47d3c98a36adf7199d56d722371cd0c6",
            b"\x0e\x95BE\x91?\xb5!\xee0(\xb0\x12{\xb6\xdf",
        ),
        (
            "string with special chars @#%^&!",
            "de6e0e75026e4dbbe4bcdee6cc69da68",
            b"\xa1]\xa9g\xb5u;E\xfc\xcfD&\xeb9M%",
        ),
        (
            "hello_world",
            "403d44e8eba659d57bfdd3360f79069c",
            b'\x97\x83\x93\xcc\x15:\xa7c-"L\xc4\x933\x97\x98',
        ),
    ],
)
def test_aes256_encrypt(value, secret_key, iv):
    encrypted = aes256_encrypt(value, secret_key, iv)

    cipher = Cipher(
        algorithms.AES256(secret_key.encode("utf-8")),
        modes.CBC(iv),
        backend=default_backend(),
    )
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES256.block_size).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()

    assert decrypted.decode("utf-8") == value
