import base64
import string
import json

from random import SystemRandom

import bcrypt
import resumablehashlib

from peewee import TextField, CharField, SmallIntegerField
from data.text import prefix_search


def random_string(length=16):
    random = SystemRandom()
    return "".join([random.choice(string.ascii_uppercase + string.digits) for _ in range(length)])


class _ResumableSHAField(TextField):
    def _create_sha(self):
        raise NotImplementedError

    def db_value(self, value):
        if value is None:
            return None

        sha_state = value.state()

        # One of the fields is a byte string, let's base64 encode it to make sure
        # we can store and fetch it regardless of default collocation.
        sha_state[3] = base64.b64encode(sha_state[3])

        return json.dumps(sha_state)

    def python_value(self, value):
        if value is None:
            return None

        sha_state = json.loads(value)

        # We need to base64 decode the data bytestring.
        sha_state[3] = base64.b64decode(sha_state[3])
        to_resume = self._create_sha()
        to_resume.set_state(sha_state)
        return to_resume


class ResumableSHA256Field(_ResumableSHAField):
    def _create_sha(self):
        return resumablehashlib.sha256()


class ResumableSHA1Field(_ResumableSHAField):
    def _create_sha(self):
        return resumablehashlib.sha1()


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
        return base64.b64encode(value)

    def python_value(self, value):
        if value is None:
            return None
        return base64.b64decode(value)


class DecryptedValue(object):
    """
    Wrapper around an already decrypted value to be placed into an encrypted field.
    """

    def __init__(self, decrypted_value):
        assert decrypted_value is not None
        assert isinstance(decrypted_value, basestring)
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

        return value.hashed

    def python_value(self, value):
        if value is None:
            return None

        return Credential(value)
