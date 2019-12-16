from Crypto.PublicKey import RSA


def generate_ssh_keypair():
    """
    Generates a new 2048 bit RSA public key in OpenSSH format and private key in PEM format.
    """
    key = RSA.generate(2048)
    public_key = key.publickey().exportKey("OpenSSH")
    private_key = key.exportKey("PEM")
    return (public_key, private_key)
