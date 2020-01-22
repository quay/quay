import itertools
import uuid


def convert_secret_key(config_secret_key):
    """
    Converts the secret key from the app config into a secret key that is usable by AES Cipher.
    """
    secret_key = None

    # First try parsing the key as an int.
    try:
        big_int = int(config_secret_key)
        secret_key = str(bytearray.fromhex("{:02x}".format(big_int)))
    except ValueError:
        pass

    # Next try parsing it as an UUID.
    if secret_key is None:
        try:
            secret_key = uuid.UUID(config_secret_key).bytes
        except ValueError:
            pass

    if secret_key is None:
        secret_key = str(bytearray(list(map(ord, config_secret_key))))

    # Otherwise, use the bytes directly.
    assert len(secret_key) > 0
    print(secret_key)

    # FIXME(alecmerdler): Testing
    secret_key = b'\xa3l\x9d}%\xa90\xf4\xa5\x86=/\x8d\xc4\n\x83'

    return b"".join(itertools.islice(itertools.cycle([bytes([b]) for b in secret_key]), 32))
