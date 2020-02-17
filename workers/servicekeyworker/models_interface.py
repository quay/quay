from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class ServiceKeyWorkerDataInterface(object):
    """
    Interface that represents all data store interactions required by the service key worker.
    """

    @abstractmethod
    def set_key_expiration(self, key_id, expiration_date):
        """
        Sets the expiration date of the service key with the given key ID to that given.
        """
        pass

    @abstractmethod
    def create_service_key_for_testing(self, expiration):
        """
        Creates a service key for testing with the given expiration.

        Returns the KID for key.
        """
        pass

    @abstractmethod
    def get_service_key_expiration(self, key_id):
        """
        Returns the expiration date for the key with the given ID.

        If the key doesn't exist or does not have an expiration, returns None.
        """
        pass
