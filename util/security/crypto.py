import base64

from cryptography.fernet import Fernet, InvalidToken


def encrypt_string(string, key):
    """
    Encrypts a string with the specified key.

    The key must be 32 raw bytes.
    """
    f = Fernet(key)

    # Fernet() works only on byte objects. Convert the string to bytes.
    unencrypted_bytes = string.encode()
    encrypted_bytes = f.encrypt(unencrypted_bytes)

    # Fernet() returns a byte object. Convert it to a string before returning.
    encrypted_string = encrypted_bytes.decode()
    return encrypted_string


def decrypt_string(string, key, ttl=None):
    """
    Decrypts an encrypted string with the specified key.

    The key must be 32 raw bytes.
    """
    f = Fernet(key)

    # Fernet() works only on byte objects. Convert the string to bytes before decrypting.
    encrypted_bytes = string.encode()  # str -> bytes

    try:
        decrypted_bytes = f.decrypt(encrypted_bytes, ttl=ttl)
    except InvalidToken:
        """
        From the the Cryptography's library documentation:

        If the token is in any way invalid, this exception is raised.
        A token may be invalid for a number of reasons: it is older than the
        ttl, it is malformed, or it does not have a valid signature.
        """
        return None  # TODO(kmullins): Shall we log this case? Is it expected?

    decrypted_string = decrypted_bytes.decode()  # bytes -> str
    return decrypted_string
