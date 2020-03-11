import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES


class AESCipher(object):
    """
    Helper class for encrypting and decrypting data via AES.

    Copied From: http://stackoverflow.com/a/21928790
    """

    def __init__(self, key):
        self.bs = 32
        self.key = key

    def encrypt(self, raw):
        assert isinstance(raw, bytes)
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size :])).decode("utf-8")

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs).encode("ascii")

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]
