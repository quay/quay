from cachetools.func import lru_cache
from data import model
from util.expiresdict import ExpiresDict, ExpiresEntry
from util.security import jwtutil


class CachingKey(object):
    def __init__(self, service_key):
        self._service_key = service_key
        self._cached_public_key = None

    @property  # type: ignore
    def public_key(self):
        cached_key = self._cached_public_key
        if cached_key is not None:
            return cached_key

        # Convert the JWK into a public key and cache it (since the conversion can take > 200ms).
        public_key = jwtutil.jwk_dict_to_public_key(self._service_key.jwk)
        self._cached_public_key = public_key
        return public_key


class InstanceKeys(object):
    """
    InstanceKeys defines a helper class for interacting with the Quay instance service keys used for
    JWT signing of registry tokens as well as requests from Quay to other services such as Clair.

    Each container will have a single registered instance key.
    """

    def __init__(self, app):
        self.app = app
        self.instance_keys = ExpiresDict(self._load_instance_keys)

    def clear_cache(self):
        """
        Clears the cache of instance keys.
        """
        self.instance_keys = ExpiresDict(self._load_instance_keys)

    def _load_instance_keys(self):
        # Load all the instance keys.
        keys = {}
        for key in model.service_keys.list_service_keys(self.service_name):
            keys[key.kid] = ExpiresEntry(CachingKey(key), key.expiration_date)

        return keys

    @property  # type: ignore
    def service_name(self):
        """
        Returns the name of the instance key's service (i.e. 'quay').
        """
        return self.app.config["INSTANCE_SERVICE_KEY_SERVICE"]

    @property  # type: ignore
    def service_key_expiration(self):
        """
        Returns the defined expiration for instance service keys, in minutes.
        """
        return self.app.config.get("INSTANCE_SERVICE_KEY_EXPIRATION", 120)

    @property  # type: ignore
    @lru_cache(maxsize=1)
    def local_key_id(self):
        """
        Returns the ID of the local instance service key.
        """
        return _load_file_contents(self.app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"])

    @property  # type: ignore
    @lru_cache(maxsize=1)
    def local_private_key(self):
        """
        Returns the private key of the local instance service key.
        """
        return _load_file_contents(self.app.config["INSTANCE_SERVICE_KEY_LOCATION"])

    def get_service_key_public_key(self, kid):
        """
        Returns the public key associated with the given instance service key or None if none.
        """
        caching_key = self.instance_keys.get(kid)
        if caching_key is None:
            return None

        return caching_key.public_key


def _load_file_contents(path):
    """
    Returns the contents of the specified file path.
    """
    with open(path) as f:
        return f.read()
