from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_ssh_keypair():
    """
    Generates a new 4096 bit RSA public key in OpenSSH format and private key in PEM format.

    GitHub.com rejects new RSA SSH keys shorter than 3072 bits (since 2026-10-14), so build
    trigger deploy keys must meet that minimum.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    public_ssh = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    return public_ssh, private_pem
