import logging

from flask.sessions import SecureCookieSessionInterface, BadSignature

from app import app
from auth.validateresult import AuthKind, ValidateResult

logger = logging.getLogger(__name__)

# The prefix for all signatures of signed granted.
SIGNATURE_PREFIX = "sigv2="


def generate_signed_token(grants, user_context):
    """
    Generates a signed session token with the given grants and user context.
    """
    ser = SecureCookieSessionInterface().get_signing_serializer(app)
    data_to_sign = {
        "grants": grants,
        "user_context": user_context,
    }

    encrypted = ser.dumps(data_to_sign)
    return "{0}{1}".format(SIGNATURE_PREFIX, encrypted)


def validate_signed_grant(auth_header):
    """
    Validates a signed grant as found inside an auth header and returns whether it points to a valid
    grant.
    """
    if not auth_header:
        return ValidateResult(AuthKind.signed_grant, missing=True)

    # Try to parse the token from the header.
    normalized = [part.strip() for part in auth_header.split(" ") if part]
    if normalized[0].lower() != "token" or len(normalized) != 2:
        logger.debug("Not a token: %s", auth_header)
        return ValidateResult(AuthKind.signed_grant, missing=True)

    # Check that it starts with the expected prefix.
    if not normalized[1].startswith(SIGNATURE_PREFIX):
        logger.debug("Not a signed grant token: %s", auth_header)
        return ValidateResult(AuthKind.signed_grant, missing=True)

    # Decrypt the grant.
    encrypted = normalized[1][len(SIGNATURE_PREFIX) :]
    ser = SecureCookieSessionInterface().get_signing_serializer(app)

    try:
        token_data = ser.loads(encrypted, max_age=app.config["SIGNED_GRANT_EXPIRATION_SEC"])
    except BadSignature:
        logger.warning("Signed grant could not be validated: %s", encrypted)
        return ValidateResult(
            AuthKind.signed_grant, error_message="Signed grant could not be validated"
        )

    logger.debug("Successfully validated signed grant with data: %s", token_data)
    return ValidateResult(AuthKind.signed_grant, signed_data=token_data)
