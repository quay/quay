from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class SuperuserConfigDataInterface(object):
    """
    Interface that represents all data store interactions required by the superuser config API.
    """

    @abstractmethod
    def is_valid(self):
        """
        Returns true if the configured database is valid.
        """

    @abstractmethod
    def has_users(self):
        """
        Returns true if there are any users defined.
        """

    @abstractmethod
    def create_superuser(self, username, password, email):
        """
        Creates a new superuser with the given username, password and email.

        Returns the user's UUID.
        """

    @abstractmethod
    def has_federated_login(self, username, service_name):
        """
        Returns true if the matching user has a federated login under the matching service.
        """

    @abstractmethod
    def attach_federated_login(self, username, service_name, federated_username):
        """
        Attaches a federatated login to the matching user, under the given service.
        """
