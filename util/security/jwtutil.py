import re

from calendar import timegm
from datetime import datetime, timedelta
from jwt import PyJWT
from jwt.exceptions import (
    InvalidTokenError,
    DecodeError,
    InvalidAudienceError,
    ExpiredSignatureError,
    ImmatureSignatureError,
    InvalidIssuedAtError,
    InvalidIssuerError,
    MissingRequiredClaimError,
    InvalidAlgorithmError,
)

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from jwkest.jwk import keyrep, RSAKey, ECKey


# TOKEN_REGEX defines a regular expression for matching JWT bearer tokens.
TOKEN_REGEX = re.compile(r"\ABearer (([a-zA-Z0-9+\-_/]+\.)+[a-zA-Z0-9+\-_/]+)\Z")

# ALGORITHM_WHITELIST defines a whitelist of allowed algorithms to be used in JWTs. DO NOT ADD
# `none` here!
ALGORITHM_WHITELIST = ["rs256", "hs256"]


class _StrictJWT(PyJWT):
    """
    _StrictJWT defines a JWT decoder with extra checks.
    """

    @staticmethod
    def _get_default_options():
        # Weird syntax to call super on a staticmethod
        defaults = super(_StrictJWT, _StrictJWT)._get_default_options()
        defaults.update(
            {"require_exp": True, "require_iat": True, "require_nbf": True, "exp_max_s": None,}
        )
        return defaults

    def _validate_claims(self, payload, options, audience=None, issuer=None, leeway=0, **kwargs):
        if options.get("exp_max_s") is not None:
            if "verify_expiration" in kwargs and not kwargs.get("verify_expiration"):
                raise ValueError("exp_max_s option implies verify_expiration")

            options["verify_exp"] = True

        # Do all of the other checks
        super(_StrictJWT, self)._validate_claims(
            payload, options, audience, issuer, leeway, **kwargs
        )

        now = timegm(datetime.utcnow().utctimetuple())
        self._reject_future_iat(payload, now, leeway)

        if "exp" in payload and options.get("exp_max_s") is not None:
            # Validate that the expiration was not more than exp_max_s seconds after the issue time
            # or in the absence of an issue time, more than exp_max_s in the future from now

            # This will work because the parent method already checked the type of exp
            expiration = datetime.utcfromtimestamp(int(payload["exp"]))
            max_signed_s = options.get("exp_max_s")

            start_time = datetime.utcnow()
            if "iat" in payload:
                start_time = datetime.utcfromtimestamp(int(payload["iat"]))

            if expiration > start_time + timedelta(seconds=max_signed_s):
                raise InvalidTokenError(
                    "Token was signed for more than %s seconds from %s", max_signed_s, start_time
                )

    def _reject_future_iat(self, payload, now, leeway):
        try:
            iat = int(payload["iat"])
        except ValueError:
            raise DecodeError("Issued At claim (iat) must be an integer.")

        if iat > (now + leeway):
            raise InvalidIssuedAtError("Issued At claim (iat) cannot be in" " the future.")


def decode(jwt, key="", verify=True, algorithms=None, options=None, **kwargs):
    """
    Decodes a JWT.
    """
    if not algorithms:
        raise InvalidAlgorithmError("algorithms must be specified")

    normalized = set([a.lower() for a in algorithms])
    if "none" in normalized:
        raise InvalidAlgorithmError("`none` algorithm is not allowed")

    if set(normalized).intersection(set(ALGORITHM_WHITELIST)) != set(normalized):
        raise InvalidAlgorithmError(
            "Algorithms `%s` are not whitelisted. Allowed: %s" % (algorithms, ALGORITHM_WHITELIST)
        )

    return _StrictJWT().decode(jwt, key, verify, algorithms, options, **kwargs)


def exp_max_s_option(max_exp_s):
    """
    Returns an options dictionary that sets the maximum expiration seconds for a JWT.
    """
    return {
        "exp_max_s": max_exp_s,
    }


def jwk_dict_to_public_key(jwk):
    """
    Converts the specified JWK into a public key.
    """
    jwkest_key = keyrep(jwk)
    if isinstance(jwkest_key, RSAKey):
        pycrypto_key = jwkest_key.key
        return RSAPublicNumbers(e=pycrypto_key.e, n=pycrypto_key.n).public_key(default_backend())
    elif isinstance(jwkest_key, ECKey):
        x, y = jwkest_key.get_key()
        return EllipticCurvePublicNumbers(x, y, jwkest_key.curve).public_key(default_backend())

    raise Exception("Unsupported kind of JWK: %s", str(type(jwkest_key)))
