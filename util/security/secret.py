import itertools
import uuid

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_HKDF_SALT = b"quay-field-encryption-v1"
_HKDF_INFO = b"aes-256-gcm"


def _normalize_secret_key(config_secret_key):
    secret_key = None

    try:
        big_int = int(config_secret_key)
        secret_key = bytearray.fromhex("{:02x}".format(big_int))
    except ValueError:
        pass

    if secret_key is None:
        try:
            secret_key = uuid.UUID(config_secret_key).bytes
        except ValueError:
            pass

    if secret_key is None:
        secret_key = bytearray(list(map(ord, config_secret_key)))

    assert len(secret_key) > 0
    return bytes(secret_key)


def convert_secret_key(config_secret_key):
    """
    Converts the secret key from the app config into a secret key that is usable by AES Cipher.
    Uses itertools.cycle padding to 32 bytes (v0 key derivation).
    """
    raw = _normalize_secret_key(config_secret_key)
    return b"".join(itertools.islice(itertools.cycle([bytes([b]) for b in raw]), 32))


def derive_key_hkdf(config_secret_key):
    """
    Derives a 32-byte AES-256 key using HKDF-SHA256 (v1 key derivation).
    """
    raw = _normalize_secret_key(config_secret_key)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    )
    return hkdf.derive(raw)
