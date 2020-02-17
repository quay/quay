from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class ServiceKey(
    namedtuple(
        "ServiceKey",
        [
            "name",
            "kid",
            "service",
            "jwk",
            "metadata",
            "created_date",
            "expiration_date",
            "rotation_duration",
            "approval",
        ],
    )
):
    """
    Service Key represents a public key (JWK) being used by an instance of a particular service to
    authenticate with other services.
    """

    pass


class ServiceKeyException(Exception):
    pass


class ServiceKeyDoesNotExist(ServiceKeyException):
    pass


@add_metaclass(ABCMeta)
class KeyServerDataInterface(object):
    """
    Interface that represents all data store interactions required by a JWT key service.
    """

    @abstractmethod
    def list_service_keys(self, service):
        """
        Returns a list of service keys or an empty list if the service does not exist.
        """
        pass

    @abstractmethod
    def get_service_key(self, signer_kid, service=None, alive_only=None, approved_only=None):
        """
        Returns a service kid with the given kid or raises ServiceKeyNotFound.
        """
        pass

    @abstractmethod
    def create_service_key(
        self, name, kid, service, jwk, metadata, expiration_date, rotation_duration=None
    ):
        """
        Stores a service key.
        """
        pass

    @abstractmethod
    def replace_service_key(self, old_kid, kid, jwk, metadata, expiration_date):
        """
        Replaces a service with a new key or raises ServiceKeyNotFound.
        """
        pass

    @abstractmethod
    def delete_service_key(self, kid):
        """
        Deletes and returns a service key with the given kid or raises ServiceKeyNotFound.
        """
        pass
