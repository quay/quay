# -*- coding: utf-8 -*-

import pytest

from data.encryption import _VERSIONS, DecryptionFailureException, FieldEncrypter


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
    "secret_key, encrypted_value, expected_decrypted_value",
    [
        ("test1234", "v1$$KeHii9PxEjCRCz0vP+7+492VY29BypjJWesd/w==", ""),
        ("test1234", "v1$$ycGiFF7IH9QmsxHoVRRkFzHSkR0cTthX1neza30kHGmpTXVypT3k", "hello world"),
        (
            "\1\2\3\4\5\6",
            "v1$$zHTuvZ3QxWdYt9G5EFLgKm2V9/4Ys8Zrz6BSusy/wnf5fwVVXY39NMc2p20M/w==",
            "hello world, again",
        ),
    ],
)
def test_encryption_value_v1(secret_key, encrypted_value, expected_decrypted_value):
    encrypter = FieldEncrypter(secret_key, "v1")
    decrypted = encrypter.decrypt_value(encrypted_value)

    assert decrypted == expected_decrypted_value


def test_cross_version_decrypt():
    v0_enc = FieldEncrypter("test1234", "v0")
    v1_enc = FieldEncrypter("test1234", "v1")
    v0_val = v0_enc.encrypt_value("hello")
    v1_val = v1_enc.encrypt_value("hello")
    assert v0_enc.decrypt_value(v1_val) == "hello"
    assert v1_enc.decrypt_value(v0_val) == "hello"
