import base64

from cryptography.fernet import Fernet, InvalidToken


def encrypt_string(string, key):
    """ Encrypts a string with the specified key. The key must be 32 raw bytes. """
    f = Fernet(key)
    return f.encrypt(string)


def decrypt_string(string, key, ttl=None):
    """ Decrypts an encrypted string with the specified key. The key must be 32 raw bytes. """
    f = Fernet(key)
    try:
        return f.decrypt(str(string), ttl=ttl)
    except InvalidToken:
        return None
    except TypeError:
        return None
