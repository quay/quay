import argparse
import json

from authlib.jose import JsonWebKey
from cryptography.hazmat.primitives import serialization


def generate_key_pair(filename, kid=None):
    """
    'kid' will default to the jwk thumbprint if not set explicitly.

    Reference: https://tools.ietf.org/html/rfc7638
    """
    options = {}
    if kid:
        options["kid"] = kid

    jwk = JsonWebKey.generate_key("RSA", 2048, is_private=True, options=options)

    print(("Writing public key to %s.jwk" % filename))
    with open("%s.jwk" % filename, mode="w") as f:
        f.truncate(0)
        f.write(jwk.as_json())

    print(("Writing key ID to %s.kid" % filename))
    with open("%s.kid" % filename, mode="w") as f:
        f.truncate(0)
        f.write(jwk.as_dict()["kid"])

    print(("Writing private key to %s.pem" % filename))
    with open("%s.pem" % filename, mode="wb") as f:
        f.truncate(0)
        f.write(
            jwk.get_private_key().private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )


parser = argparse.ArgumentParser(description="Generates a key pair into files")
parser.add_argument("filename", help="The filename prefix for the generated key files")
args = parser.parse_args()
generate_key_pair(args.filename)
