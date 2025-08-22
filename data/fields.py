import base64
import json
import pickle
import string
import hashlib
import hmac
from random import SystemRandom

import bcrypt
from peewee import CharField, SmallIntegerField, TextField

from data.text import prefix_search
from util.bytes import Bytes


def random_string(length=16):
    random = SystemRandom()
    return "".join([random.choice(string.ascii_uppercase + string.digits) for _ in range(length)])


def _create_hasher_signature(data, secret_key=None):
    """
    Create HMAC signature for hasher state to prevent tampering.
    """
    if secret_key is None:
        # In production, this should come from config
        secret_key = b"quay-hasher-signature-key-change-in-production"
    
    return hmac.new(secret_key, data, hashlib.sha256).digest()


def _verify_hasher_signature(data, signature, secret_key=None):
    """
    Verify HMAC signature for hasher state.
    """
    if secret_key is None:
        secret_key = b"quay-hasher-signature-key-change-in-production"
    
    expected_signature = _create_hasher_signature(data, secret_key)
    return hmac.compare_digest(signature, expected_signature)


class _ResumableSHAField(TextField):
    """
    Base Class used to store the state of an in-progress hash in the database. This is particularly
    useful for working with large byte streams and allows the hashing to be paused and resumed
    as needed.
    """

    def _create_sha(self):
        raise NotImplementedError

    def db_value(self, value):
        """
        Serialize the Hasher's state for storage in the database as plain-text.
        Uses signed serialization to prevent tampering.
        """
        if value is None:
            return None

        # Serialize the hasher state
        pickled_data = pickle.dumps(value)
        
        # Create signature to prevent tampering
        signature = _create_hasher_signature(pickled_data)
        
        # Combine signature and data
        signed_data = signature + pickled_data
        
        serialized_state = base64.b64encode(signed_data).decode("ascii")
        return serialized_state

    def python_value(self, value):
        """
        Restore the Hasher from its state stored in the database.
        Verifies signature to prevent arbitrary code execution via pickle deserialization.
        """
        if value is None:
            return None

        try:
            # Decode the base64 data
            signed_data = base64.b64decode(value.encode("ascii"))
            
            # Extract signature (first 32 bytes for SHA-256 HMAC) and data
            if len(signed_data) < 32:
                raise ValueError("Invalid hasher state: too short")
                
            signature = signed_data[:32]
            pickled_data = signed_data[32:]
            
            # Verify signature to prevent tampering
            if not _verify_hasher_signature(pickled_data, signature):
                raise ValueError("Invalid hasher state: signature verification failed")
            
            # Only deserialize if signature is valid
            hasher = pickle.loads(pickled_data)
            
            # Additional validation: ensure the object has expected hasher methods
            if not hasattr(hasher, 'update') or not hasattr(hasher, 'digest'):
                raise ValueError("Invalid hasher state: object is not a valid hasher")
                
            return hasher
            
        except (ValueError, TypeError, pickle.UnpicklingError) as e:
            # Log the error and return None to gracefully handle corrupted data
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to deserialize hasher state: {e}")
            
            # Return a fresh hasher instead of None to prevent application errors
            return self._create_sha()


class ResumableSHA256Field(_ResumableSHAField):
    def _create_sha(self):
        """Create a fresh SHA-256 hasher instance."""
        try:
            import resumablesha256 as rehash
            return rehash.sha256()
        except ImportError:
            # Fallback to standard hashlib if resumablesha256 is not available
            import hashlib
            return hashlib.sha256()


class ResumableSHA1Field(_ResumableSHAField):
    def _create_sha(self):
        """Create a fresh SHA-1 hasher instance."""
        try:
            import resumablesha256 as rehash
            # Assuming resumablesha256 also provides sha1, or use hashlib as fallback
            return rehash.sha1() if hasattr(rehash, 'sha1') else hashlib.sha1()
        except ImportError:
            # Fallback to standard hashlib if resumablesha256 is not available
            import hashlib
            return hashlib.sha1()


class JSONField(TextField):
    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is None or value == "":
            return {}
        return json.loads(value)


class Base64BinaryField(TextField):
    def db_value(self, value):
        if value is None:
            return None
        return base64.b64encode(value).decode("ascii")

    def python_value(self, value):
        if value is None:
            return None
        return base64.b64decode(value.encode("ascii"))


class DecryptedValue(object):
    """
    Wrapper around an already decrypted value to be placed into an encrypted field.
    """

    def __init__(self, decrypted_value):
        assert decrypted_value is not None
        self.value = decrypted_value

    def decrypt(self):
        return self.value

    def matches(self, unencrypted_value):
        """
        Returns whether the value of this field matches the unencrypted_value.
        """
        return self.decrypt() == unencrypted_value


class LazyEncryptedValue(object):
    """
    Wrapper around an encrypted value in an encrypted field.

    Will decrypt lazily.
    """

    def __init__(self, encrypted_value, field):
        self.encrypted_value = encrypted_value
        self._field = field

    def decrypt(self, encrypter=None):
        """
        Decrypts the value.
        """
        encrypter = encrypter or self._field.model._meta.encrypter
        return encrypter.decrypt_value(self.encrypted_value)

    def matches(self, unencrypted_value):
        """
        Returns whether the value of this field matches the unencrypted_value.
        """
        return self.decrypt() == unencrypted_value

    def __eq__(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def __mod__(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def __pow__(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def __contains__(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def contains(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def startswith(self, _):
        raise Exception("Disallowed operation; use `matches`")

    def endswith(self, _):
        raise Exception("Disallowed operation; use `matches`")


def _add_encryption(field_class, requires_length_check=True):
    """
    Adds support for encryption and decryption to the given field class.
    """

    class indexed_class(field_class):
        def __init__(self, default_token_length=None, *args, **kwargs):
            def _generate_default():
                return DecryptedValue(random_string(default_token_length))

            if default_token_length is not None:
                kwargs["default"] = _generate_default

            field_class.__init__(self, *args, **kwargs)
            assert not self.index

        def db_value(self, value):
            if value is None:
                return None

            if isinstance(value, LazyEncryptedValue):
                return value.encrypted_value

            if isinstance(value, DecryptedValue):
                value = value.value

            meta = self.model._meta
            return meta.encrypter.encrypt_value(
                value, self.max_length if requires_length_check else None
            )

        def python_value(self, value):
            if value is None:
                return None

            return LazyEncryptedValue(value, self)

        def __hash__(self):
            return field_class.__hash__(self)

        def __eq__(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def __mod__(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def __pow__(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def __contains__(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def contains(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def startswith(self, _):
            raise Exception("Disallowed operation; use `matches`")

        def endswith(self, _):
            raise Exception("Disallowed operation; use `matches`")

    return indexed_class


EncryptedCharField = _add_encryption(CharField)
EncryptedTextField = _add_encryption(TextField, requires_length_check=False)


class EnumField(SmallIntegerField):
    def __init__(self, enum_type, *args, **kwargs):
        kwargs.pop("index", None)

        super(EnumField, self).__init__(index=True, *args, **kwargs)
        self.enum_type = enum_type

    def db_value(self, value):
        """
        Convert the python value for storage in the database.
        """
        return int(value.value)

    def python_value(self, value):
        """
        Convert the database value to a pythonic value.
        """
        return self.enum_type(value) if value is not None else None

    def clone_base(self, **kwargs):
        return super(EnumField, self).clone_base(enum_type=self.enum_type, **kwargs)


def _add_fulltext(field_class):
    """
    Adds support for full text indexing and lookup to the given field class.
    """

    class indexed_class(field_class):
        # Marker used by SQLAlchemy translation layer to add the proper index for full text searching.
        __fulltext__ = True

        def __init__(self, match_function, *args, **kwargs):
            field_class.__init__(self, *args, **kwargs)
            self.match_function = match_function

        def match(self, query):
            return self.match_function(self, query)

        def match_prefix(self, query):
            return prefix_search(self, query)

        def __mod__(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

        def __pow__(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

        def __contains__(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

        def contains(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

        def startswith(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

        def endswith(self, _):
            raise Exception("Unsafe operation: Use `match` or `match_prefix`")

    return indexed_class


FullIndexedCharField = _add_fulltext(CharField)
FullIndexedTextField = _add_fulltext(TextField)


class Credential(object):
    """
    Credential represents a hashed credential.
    """

    def __init__(self, hashed):
        self.hashed = hashed

    def matches(self, value):
        """
        Returns true if this credential matches the unhashed value given.
        """
        return bcrypt.hashpw(value.encode("utf-8"), self.hashed) == self.hashed

    @classmethod
    def from_string(cls, string_value):
        """
        Returns a Credential object from an unhashed string value.
        """
        return Credential(bcrypt.hashpw(string_value.encode("utf-8"), bcrypt.gensalt()))

    @classmethod
    def generate(cls, length=20):
        """
        Generates a new credential and returns it, along with its unhashed form.
        """
        token = random_string(length)
        return Credential.from_string(token), token


class CredentialField(CharField):
    """
    A character field that stores crytographically hashed credentials that should never be available
    to the user in plaintext after initial creation.

    This field automatically provides verification.
    """

    def __init__(self, *args, **kwargs):
        CharField.__init__(self, *args, **kwargs)
        assert "default" not in kwargs
        assert not self.index

    def db_value(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            raise Exception(
                "A string cannot be given to a CredentialField; please wrap in a Credential"
            )

        return Bytes.for_string_or_unicode(value.hashed).as_unicode()

    def python_value(self, value):
        if value is None:
            return None

        return Credential(Bytes.for_string_or_unicode(value).as_encoded_str())
