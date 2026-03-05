import base64
import logging
import os
from collections import namedtuple

from cryptography.hazmat.primitives.ciphers.aead import AESCCM, AESGCM

from util.security.secret import convert_secret_key, derive_key_hkdf


class DecryptionFailureException(Exception):
    """
    Exception raised if a field could not be decrypted.
    """


EncryptionVersion = namedtuple("EncryptionVersion", ["prefix", "encrypt", "decrypt", "derive_key"])

logger = logging.getLogger(__name__)


_SEPARATOR = "$$"
AES_CCM_NONCE_LENGTH = 13
AES_GCM_NONCE_LENGTH = 12


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


def _encrypt_gcm(secret_key, value, field_max_length=None):
    aesgcm = AESGCM(secret_key)
    nonce = os.urandom(AES_GCM_NONCE_LENGTH)
    ct = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
    encrypted = base64.b64encode(nonce + ct).decode("utf-8")
    if field_max_length:
        msg = "Tried to encode a value too large for this field"
        assert (len(encrypted) + _RESERVED_FIELD_SPACE) <= field_max_length, msg

    return encrypted


def _decrypt_gcm(secret_key, value):
    aesgcm = AESGCM(secret_key)
    try:
        decoded = base64.b64decode(value)
        nonce = decoded[:AES_GCM_NONCE_LENGTH]
        ct = decoded[AES_GCM_NONCE_LENGTH:]
        decrypted = aesgcm.decrypt(nonce, ct, None)
        return decrypted.decode("utf-8")
    except Exception:
        logger.exception("Got exception when trying to decrypt value `%s`", value)
        raise DecryptionFailureException()


_VERSIONS = {
    "v0": EncryptionVersion("v0", _encrypt_ccm, _decrypt_ccm, convert_secret_key),
    "v1": EncryptionVersion("v1", _encrypt_gcm, _decrypt_gcm, derive_key_hkdf),
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
        self._raw_secret_key = secret_key
        self._encryption_version = _VERSIONS[version]

    def encrypt_value(self, value, field_max_length=None):
        assert self._raw_secret_key is not None
        derived_key = self._encryption_version.derive_key(self._raw_secret_key)
        encrypted_value = self._encryption_version.encrypt(derived_key, value, field_max_length)
        return "%s%s%s" % (self._encryption_version.prefix, _SEPARATOR, encrypted_value)

    def decrypt_value(self, value):
        assert self._raw_secret_key is not None
        if _SEPARATOR not in value:
            raise DecryptionFailureException("Invalid encrypted value")

        version_prefix, data = value.split(_SEPARATOR, 1)
        if version_prefix not in _VERSIONS:
            raise DecryptionFailureException("Unknown version prefix %s" % version_prefix)

        version = _VERSIONS[version_prefix]
        derived_key = version.derive_key(self._raw_secret_key)
        return version.decrypt(derived_key, data)
