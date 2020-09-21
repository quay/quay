import argparse
import json

from Crypto.PublicKey import RSA
from jwkest.jwk import RSAKey
from util.security.fingerprint import canonical_kid


def generate_key_pair(filename, kid=None):
    private_key = RSA.generate(2048)
    jwk = RSAKey(key=private_key.publickey()).serialize()
    if kid is None:
        kid = canonical_kid(jwk)

    print(("Writing public key to %s.jwk" % filename))
    with open("%s.jwk" % filename, mode="w") as f:
        f.truncate(0)
        f.write(json.dumps(jwk))

    print(("Writing key ID to %s.kid" % filename))
    with open("%s.kid" % filename, mode="w") as f:
        f.truncate(0)
        f.write(kid)

    print(("Writing private key to %s.pem" % filename))
    with open("%s.pem" % filename, mode="wb") as f:
        f.truncate(0)
        f.write(private_key.exportKey())


parser = argparse.ArgumentParser(description="Generates a key pair into files")
parser.add_argument("filename", help="The filename prefix for the generated key files")
args = parser.parse_args()
generate_key_pair(args.filename)
