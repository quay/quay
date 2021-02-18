import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding


class AESCipher(object):
    """
    Helper class for encrypting and decrypting data via AES.

    References:
        - https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption.html
        - https://cryptography.io/en/latest/hazmat/primitives/padding.html
    """

    def __init__(self, key):
        self.bs = 32
        self.key = key

    def encrypt(self, raw):
        assert isinstance(raw, bytes)

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(raw) + padder.finalize()

        iv = os.urandom(algorithms.AES.block_size // 8)

        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ct = encryptor.update(padded_data) + encryptor.finalize()

        return base64.b64encode(iv + ct)

    def decrypt(self, enc):
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        enc = base64.b64decode(enc)

        iv = enc[: algorithms.AES.block_size // 8]

        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        decrypted_padded_data = (
            decryptor.update(enc[algorithms.AES.block_size // 8 :]) + decryptor.finalize()
        )

        return unpadder.update(decrypted_padded_data) + unpadder.finalize()
