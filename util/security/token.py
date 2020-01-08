from collections import namedtuple

import base64

DELIMITER = ":"
DecodedToken = namedtuple("DecodedToken", ["public_code", "private_token"])


def encode_public_private_token(public_code, private_token, allow_public_only=False):
    # NOTE: This is for legacy tokens where the private token part is None. We should remove this
    # once older installations have been fully converted over (if at all possible).
    if private_token is None:
        assert allow_public_only
        return public_code

    assert isinstance(private_token, str)
    b = ("%s%s%s" % (public_code, DELIMITER, private_token)).encode("utf-8")

    return base64.b64encode(b)


def decode_public_private_token(encoded, allow_public_only=False):
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except (ValueError, TypeError):
        if not allow_public_only:
            return None

        return DecodedToken(encoded, None)

    parts = decoded.split(DELIMITER, 2)
    if len(parts) != 2:
        return None

    return DecodedToken(*parts)
