import json

from hashlib import sha256
from util.canonicaljson import canonicalize


def canonical_kid(jwk):
    """
    This function returns the SHA256 hash of a canonical JWK.

    Args:
      jwk (object): the JWK for which a kid will be generated.

    Returns:
      string: the unique kid for the given JWK.
    """
    return sha256(json.dumps(canonicalize(jwk), separators=(",", ":")).encode("utf-8")).hexdigest()
