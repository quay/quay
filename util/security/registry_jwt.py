import logging
import time

from functools import wraps

import jwt

from prometheus_client import Counter

from util.security import jwtutil


logger = logging.getLogger(__name__)


bearer_token_decoded = Counter(
    "bearer_token_decoded_total",
    "number of times a bearer token has been validated",
    labelnames=["success"],
)


ANONYMOUS_SUB = "(anonymous)"
ALGORITHM = "RS256"
CLAIM_TUF_ROOTS = "com.apostille.roots"
CLAIM_TUF_ROOT = "com.apostille.root"
QUAY_TUF_ROOT = "quay"
SIGNER_TUF_ROOT = "signer"
DISABLED_TUF_ROOT = "$disabled"

# The number of allowed seconds of clock skew for a JWT. The iat, nbf and exp are adjusted with this
# count.
JWT_CLOCK_SKEW_SECONDS = 30


class InvalidBearerTokenException(Exception):
    pass


def decode_bearer_header(bearer_header, instance_keys, config):
    """
    decode_bearer_header decodes the given bearer header that contains an encoded JWT with both a
    Key ID as well as the signed JWT and returns the decoded and validated JWT.

    On any error, raises an InvalidBearerTokenException with the reason for failure.
    """
    # Extract the jwt token from the header
    match = jwtutil.TOKEN_REGEX.match(bearer_header)
    if match is None:
        raise InvalidBearerTokenException("Invalid bearer token format")

    encoded_jwt = match.group(1)
    logger.debug("encoded JWT: %s", encoded_jwt)
    return decode_bearer_token(encoded_jwt, instance_keys, config)


def observe_decode():
    """
    Decorates `decode_bearer_tokens` to record a metric into Prometheus such that any exceptions
    raised get recorded as a failure and the return of a payload is considered a success.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                rv = func(*args, **kwargs)
            except Exception as e:
                bearer_token_decoded.labels(False).inc()
                raise e
            bearer_token_decoded.labels(True).inc()
            return rv

        return wrapper

    return decorator


@observe_decode()
def decode_bearer_token(bearer_token, instance_keys, config):
    """
    decode_bearer_token decodes the given bearer token that contains both a Key ID as well as the
    encoded JWT and returns the decoded and validated JWT.

    On any error, raises an InvalidBearerTokenException with the reason for failure.
    """
    # Decode the key ID.
    try:
        headers = jwt.get_unverified_header(bearer_token)
    except jwtutil.InvalidTokenError as ite:
        logger.exception("Invalid token reason: %s", ite)
        raise InvalidBearerTokenException(ite)

    kid = headers.get("kid", None)
    if kid is None:
        logger.error("Missing kid header on encoded JWT: %s", bearer_token)
        raise InvalidBearerTokenException("Missing kid header")

    # Find the matching public key.
    public_key = instance_keys.get_service_key_public_key(kid)
    if public_key is None:
        logger.error(
            "Could not find requested service key %s with encoded JWT: %s", kid, bearer_token
        )
        raise InvalidBearerTokenException("Unknown service key")

    # Load the JWT returned.
    try:
        expected_issuer = instance_keys.service_name
        audience = config["SERVER_HOSTNAME"]
        max_signed_s = config.get("REGISTRY_JWT_AUTH_MAX_FRESH_S", 3660)
        max_exp = jwtutil.exp_max_s_option(max_signed_s)
        payload = jwtutil.decode(
            bearer_token,
            public_key,
            algorithms=[ALGORITHM],
            audience=audience,
            issuer=expected_issuer,
            options=max_exp,
            leeway=JWT_CLOCK_SKEW_SECONDS,
        )
    except jwtutil.InvalidTokenError as ite:
        logger.exception("Invalid token reason: %s", ite)
        raise InvalidBearerTokenException(ite)

    if not "sub" in payload:
        raise InvalidBearerTokenException("Missing sub field in JWT")

    return payload


def generate_bearer_token(audience, subject, context, access, lifetime_s, instance_keys):
    """
    Generates a registry bearer token (without the 'Bearer ' portion) based on the given
    information.
    """
    return _generate_jwt_object(
        audience,
        subject,
        context,
        access,
        lifetime_s,
        instance_keys.service_name,
        instance_keys.local_key_id,
        instance_keys.local_private_key,
    )


def _generate_jwt_object(
    audience, subject, context, access, lifetime_s, issuer, key_id, private_key
):
    """
    Generates a compact encoded JWT with the values specified.
    """
    token_data = {
        "iss": issuer,
        "aud": audience,
        "nbf": int(time.time()),
        "iat": int(time.time()),
        "exp": int(time.time() + lifetime_s),
        "sub": subject,
        "access": access,
        "context": context,
    }

    token_headers = {
        "kid": key_id,
    }

    return jwt.encode(token_data, private_key, ALGORITHM, headers=token_headers)


def build_context_and_subject(auth_context=None, tuf_roots=None):
    """
    Builds the custom context field for the JWT signed token and returns it, along with the subject
    for the JWT signed token.
    """
    # Serialize to a dictionary.
    context = auth_context.to_signed_dict() if auth_context else {}

    # TODO: remove once Apostille has been upgraded to not use the single root.
    single_root = (
        list(tuf_roots.values())[0]
        if tuf_roots is not None and len(tuf_roots) == 1
        else DISABLED_TUF_ROOT
    )

    context.update(
        {
            CLAIM_TUF_ROOTS: tuf_roots,
            CLAIM_TUF_ROOT: single_root,
        }
    )

    if not auth_context or auth_context.is_anonymous:
        return (context, ANONYMOUS_SUB)

    return (context, auth_context.authed_user.username if auth_context.authed_user else None)
