import base64
import hashlib
import secrets
import string

_UNRESERVED = string.ascii_letters + string.digits + "-._~"


def generate_code_verifier(length: int = 64) -> str:
    if length < 43 or length > 128:
        raise ValueError("PKCE code_verifier length must be between 43 and 128 characters")
    return "".join(secrets.choice(_UNRESERVED) for _ in range(length))


def code_challenge(verifier: str, method: str = "S256") -> str:
    if method.upper() == "PLAIN":
        return verifier
    if method.upper() != "S256":
        raise ValueError("Unsupported PKCE method: %s" % method)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
