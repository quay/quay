import time

import pytest
import jwt

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from authlib.jose import jwk

from util.security.jwtutil import (
    decode,
    exp_max_s_option,
    jwk_dict_to_public_key,
    InvalidTokenError,
    InvalidAlgorithmError,
)


@pytest.fixture(scope="session")
def private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture(scope="session")
def private_key_pem(private_key):
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _token_data(audience, subject, iss, iat=None, exp=None, nbf=None):
    return {
        "iss": iss,
        "aud": audience,
        "nbf": nbf() if nbf is not None else int(time.time()),
        "iat": iat() if iat is not None else int(time.time()),
        "exp": exp() if exp is not None else int(time.time() + 3600),
        "sub": subject,
    }


@pytest.mark.parametrize(
    "aud, iss, nbf, iat, exp, expected_exception",
    [
        pytest.param(
            "invalidaudience",
            "someissuer",
            None,
            None,
            None,
            "Invalid audience",
            id="invalid audience",
        ),
        pytest.param(
            "someaudience", "invalidissuer", None, None, None, "Invalid issuer", id="invalid issuer"
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            lambda: time.time() + 120,
            None,
            None,
            "The token is not yet valid",
            id="invalid not before",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            None,
            lambda: time.time() + 120,
            None,
            "Issued At claim",
            id="issued at in future",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            None,
            None,
            lambda: time.time() - 100,
            "Signature has expired",
            id="already expired",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            None,
            None,
            lambda: time.time() + 10000,
            "Token was signed for more than",
            id="expiration too far in future",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            lambda: time.time() + 10,
            None,
            None,
            None,
            id="not before in future by within leeway",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            None,
            lambda: time.time() + 10,
            None,
            None,
            id="issued at in future but within leeway",
        ),
        pytest.param(
            "someaudience",
            "someissuer",
            None,
            None,
            lambda: time.time() - 10,
            None,
            id="expiration in past but within leeway",
        ),
    ],
)
def test_decode_jwt_validation(
    aud, iss, nbf, iat, exp, expected_exception, private_key_pem, public_key
):
    token = jwt.encode(_token_data(aud, "subject", iss, iat, exp, nbf), private_key_pem, "RS256")

    if expected_exception is not None:
        with pytest.raises(InvalidTokenError) as ite:
            max_exp = exp_max_s_option(3600)
            decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience="someaudience",
                issuer="someissuer",
                options=max_exp,
                leeway=60,
            )
        assert ite.match(expected_exception)
    else:
        max_exp = exp_max_s_option(3600)
        decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="someaudience",
            issuer="someissuer",
            options=max_exp,
            leeway=60,
        )


def test_decode_jwt_invalid_key(private_key_pem):
    # Encode with the test private key.
    token = jwt.encode(_token_data("aud", "subject", "someissuer"), private_key_pem, "RS256")

    # Try to decode with a different public key.
    another_public_key = (
        rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        .public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    with pytest.raises(InvalidTokenError) as ite:
        max_exp = exp_max_s_option(3600)
        decode(
            token,
            another_public_key,
            algorithms=["RS256"],
            audience="aud",
            issuer="someissuer",
            options=max_exp,
            leeway=60,
        )
    assert ite.match("Signature verification failed")


def test_decode_jwt_invalid_algorithm(private_key_pem, public_key):
    # Encode with the test private key.
    token = jwt.encode(_token_data("aud", "subject", "someissuer"), private_key_pem, "RS256")

    # Attempt to decode but only with a different algorithm than that used.
    with pytest.raises(InvalidAlgorithmError) as ite:
        max_exp = exp_max_s_option(3600)
        decode(
            token,
            public_key,
            algorithms=["ES256"],
            audience="aud",
            issuer="someissuer",
            options=max_exp,
            leeway=60,
        )
    assert ite.match("are not whitelisted")


def test_jwk_dict_to_public_key(private_key, private_key_pem):
    public_key = private_key.public_key()
    key_dict = jwk.dumps(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    converted = jwk_dict_to_public_key(key_dict)

    # Encode with the test private key.
    token = jwt.encode(_token_data("aud", "subject", "someissuer"), private_key_pem, "RS256")

    # Decode with the converted key.
    max_exp = exp_max_s_option(3600)
    decode(
        token,
        converted,
        algorithms=["RS256"],
        audience="aud",
        issuer="someissuer",
        options=max_exp,
        leeway=60,
    )
