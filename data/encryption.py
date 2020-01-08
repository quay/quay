import os
import logging
import base64

from collections import namedtuple
from cryptography.hazmat.primitives.ciphers.aead import AESCCM

from util.security.secret import convert_secret_key


class DecryptionFailureException(Exception):
    """
    Exception raised if a field could not be decrypted.
    """


EncryptionVersion = namedtuple("EncryptionVersion", ["prefix", "encrypt", "decrypt"])

logger = logging.getLogger(__name__)


_SEPARATOR = "$$"
AES_CCM_NONCE_LENGTH = 13


def _encrypt_ccm(secret_key, value, field_max_length=None):
    aesccm = AESCCM(secret_key)
    nonce = os.urandom(AES_CCM_NONCE_LENGTH)
    ct = aesccm.encrypt(nonce, value.encode("utf-8"), None)
    encrypted = base64.b64encode(nonce + ct).decode("utf-8")
    if field_max_length:
        msg = "Tried to encode a value too large for this field"
        assert (len(encrypted) + _RESERVED_FIELD_SPACE) <= field_max_length, msg

    return encrypted


def _decrypt_ccm(secret_key, value):
    aesccm = AESCCM(secret_key)
    try:
        decoded = base64.b64decode(value)
        nonce = decoded[:AES_CCM_NONCE_LENGTH]
        ct = decoded[AES_CCM_NONCE_LENGTH:]
        decrypted = aesccm.decrypt(nonce, ct, None)
        return decrypted.decode("utf-8")
    except Exception:
        logger.exception("Got exception when trying to decrypt value `%s`", value)
        raise DecryptionFailureException()


# Defines the versions of encryptions we support. This will allow us to upgrade to newer encryption
# protocols (fairly seamlessly) if need be in the future.
_VERSIONS = {
    "v0": EncryptionVersion("v0", _encrypt_ccm, _decrypt_ccm),
}

_RESERVED_FIELD_SPACE = len(_SEPARATOR) + max([len(k) for k in list(_VERSIONS.keys())])


class FieldEncrypter(object):
    """
    Helper object for defining how fields are encrypted and decrypted between the database and the
    application.
    """

    def __init__(self, secret_key, version="v0"):
        # NOTE: secret_key will be None when the system is being first initialized, so we allow that
        # case here, but make sure to assert that it is *not* None below if any encryption is actually
        # needed.
        self._secret_key = convert_secret_key(secret_key) if secret_key is not None else None
        self._encryption_version = _VERSIONS[version]

    def encrypt_value(self, value, field_max_length=None):
        """
        Encrypts the value using the current version of encryption.
        """
        assert self._secret_key is not None
        encrypted_value = self._encryption_version.encrypt(
            self._secret_key, value, field_max_length
        )
        return "%s%s%s" % (self._encryption_version.prefix, _SEPARATOR, encrypted_value)

    def decrypt_value(self, value):
        """
        Decrypts the value, returning it.

        If the value cannot be decrypted raises a DecryptionFailureException.
        """
        assert self._secret_key is not None
        if _SEPARATOR not in value:
            raise DecryptionFailureException("Invalid encrypted value")

        version_prefix, data = value.split(_SEPARATOR, 1)
        if version_prefix not in _VERSIONS:
            raise DecryptionFailureException("Unknown version prefix %s" % version_prefix)

        return _VERSIONS[version_prefix].decrypt(self._secret_key, data)
