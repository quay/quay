from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from util.security.ssh import generate_ssh_keypair


def test_generate_ssh_keypair_meets_github_rsa_minimum():
    public_ssh, private_pem = generate_ssh_keypair()

    assert isinstance(public_ssh, bytes)
    assert isinstance(private_pem, bytes)
    assert public_ssh.decode("ascii").startswith("ssh-rsa ")

    private_key = load_pem_private_key(private_pem, password=None)
    assert isinstance(private_key, rsa.RSAPrivateKey)
    # GitHub.com requires new RSA SSH keys to be at least 3072 bits.
    assert private_key.key_size >= 3072
    assert private_key.key_size == 4096

    loaded_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    assert loaded_public == public_ssh
