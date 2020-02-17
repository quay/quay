from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class SubscribeInterface(object):
    """
    Interface that represents all data store interactions required by the subscribe API endpoint.
    """

    @abstractmethod
    def get_private_repo_count(self, username):
        """
        Returns the number of private repositories for a given username or namespace.
        """

    @abstractmethod
    def create_unique_notification(self, kind_name, target_username, metadata={}):
        """
        Creates a notification using the given parameters.
        """

    @abstractmethod
    def delete_notifications_by_kind(self, target_username, kind_name):
        """
        Remove notifications for a target based on given kind.
        """
