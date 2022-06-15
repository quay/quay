from random import SystemRandom


def generate_secret_key():
    cryptogen = SystemRandom()
    return str(cryptogen.getrandbits(256))
