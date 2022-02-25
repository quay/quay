import os
from functools import lru_cache

from authlib.jose import JsonWebKey
from _init import OVERRIDE_CONFIG_DIRECTORY

DOCKER_V2_SIGNINGKEY_FILENAME = "docker_v2.pem"


# Check for a key in config. If none found, generate a new signing key for Docker V2 manifests.
@lru_cache(maxsize=1)
def get_docker_v2_signing_key():
    _v2_key_path = os.path.join(OVERRIDE_CONFIG_DIRECTORY, DOCKER_V2_SIGNINGKEY_FILENAME)
    if os.path.exists(_v2_key_path):
        with open(_v2_key_path) as key_file:
            docker_v2_signing_key = JsonWebKey.import_key(key_file.read())
    else:
        docker_v2_signing_key = JsonWebKey.generate_key("RSA", 2048, is_private=True)
    return docker_v2_signing_key
