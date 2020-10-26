from collections import namedtuple
import base64

from util.bytes import Bytes

DELIMITER = ":"
DecodedToken = namedtuple("DecodedToken", ["public_code", "private_token"])


def encode_public_private_token(public_code, private_token, allow_public_only=False):
    # NOTE: This is for legacy tokens where the private token part is None. We should remove this
    # once older installations have been fully converted over (if at all possible).
    if private_token is None:
        assert allow_public_only
        return public_code

    assert isinstance(private_token, str) and isinstance(public_code, str)
    b = ("%s%s%s" % (public_code, DELIMITER, private_token)).encode("utf-8")

    return base64.b64encode(b).decode("utf-8")


def decode_public_private_token(encoded, allow_public_only=False):
    token = Bytes.for_string_or_unicode(encoded)
    try:
        decoded = base64.b64decode(token.as_encoded_str()).decode("utf-8")
    except (ValueError, TypeError):
        if not allow_public_only:
            return None

        return DecodedToken(token.as_unicode(), None)

    parts = decoded.split(DELIMITER, 2)
    if len(parts) != 2:
        return None

    return DecodedToken(*parts)
