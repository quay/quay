import jsonschema
import jwt
import logging

from app import instance_keys
from util.security import jwtutil
from util.security.registry_jwt import \
    generate_bearer_token, \
    InvalidBearerTokenException, \
    ALGORITHM, \
    JWT_CLOCK_SKEW_SECONDS


logger = logging.getLogger(__name__)


ANONYMOUS_SUB = "(anonymous)"
BUILD_JOB_REGISTRATION_TYPE = "build_job_registration"
BUILD_JOB_TOKEN_TYPE = "build_job_token"


BUILD_TOKEN_CONTEXT_SCHEMA = {
    "type": "object",
    "description": "Build context",
    "required": ["token_type", "build_id", "job_id", "expiration"],
    "properties": {
        "token_type": {
            "type": "string",
            "description": "The build token type",
        },
        "build_id": {
            "type": "string",
            "description": "The build id",
        },
        "job_id": {
            "type": "string",
            "description": "The job id",
        },
        "expiration": {
            "type": "number",
            "description": "The number of seconds until the job expires",
        },
    }
}


class InvalidBuildTokenException(Exception):
    pass


def build_token(aud, token_type, build_id, job_id, expiration, instance_keys):
    """Returns an encoded JWT for the given build, signed by the local instance's private."""
    token_data = {
        "token_type": token_type,
        "build_id": build_id,
        "job_id": job_id,
        "expiration": expiration
    }

    token = generate_bearer_token(aud, ANONYMOUS_SUB, token_data, {}, expiration, instance_keys)
    return token.decode("utf-8")


def verify_build_token(token, aud, token_type, instance_keys):
    """Verify the JWT build token."""
    try:
        headers = jwt.get_unverified_header(token)
    except jwtutil.InvalidTokenError as ite:
        logger.error("Invalid token reason: %s", ite)
        raise InvalidBuildTokenException(ite)

    kid = headers.get("kid", None)
    if kid is None:
        logger.error("Missing kid header on encoded JWT: %s", token)
        raise InvalidBuildTokenException("Missing kid header")

    public_key = instance_keys.get_service_key_public_key(kid)
    if public_key is None:
        logger.error("Could not find requested service key %s with encoded JWT: %s", kid, token)
        raise InvalidBuildTokenException("Unknown service key")

    try:
        payload = jwtutil.decode(
            token,
            public_key,
            verify=True,
            algorithms=[ALGORITHM],
            audience=aud,
            issuer=instance_keys.service_name,
            leeway=JWT_CLOCK_SKEW_SECONDS
        )
    except jwtutil.InvalidTokenError as ite:
        logger.error("Invalid token reason: %s", ite)
        raise InvalidBuildTokenException(ite)

    if "sub" not in payload:
        raise InvalidBuildTokenException("Missing sub field in JWT")

    if payload["sub"] != ANONYMOUS_SUB:
        raise InvalidBuildTokenException("Wrong sub field in JWT")

    if ("context" not in payload 
        or not payload["context"]["token_type"]
        or not payload["context"]["build_id"]
        or not payload["context"]["job_id"]
        or not payload["context"]["expiration"]):
        raise InvalidBuildTokenException("Missing context field in JWT")

    try:
        jsonschema.validate(payload["context"], BUILD_TOKEN_CONTEXT_SCHEMA)
    except jsonschema.ValidationError:
        raise InvalidBuildTokenException("Unable to validate build token context schema: malformed context")

    if payload["context"]["token_type"] != token_type:
        raise InvalidBuildTokenException("Build token type in JWT does not match expected type: %s" % token_type)

    return payload
