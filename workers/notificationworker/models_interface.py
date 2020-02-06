from abc import ABCMeta, abstractmethod
from collections import namedtuple
from six import add_metaclass


class Repository(namedtuple("Repository", ["namespace_name", "name"])):
    """
    Repository represents a repository.
    """


class Notification(
    namedtuple(
        "Notification",
        [
            "uuid",
            "event_name",
            "method_name",
            "event_config_dict",
            "method_config_dict",
            "repository",
        ],
    )
):
    """
    Notification represents a registered notification of some kind.
    """


@add_metaclass(ABCMeta)
class NotificationWorkerDataInterface(object):
    """
    Interface that represents all data store interactions required by the notification worker.
    """

    @abstractmethod
    def get_enabled_notification(self, notification_uuid):
        """
        Returns an *enabled* notification with the given UUID, or None if none.
        """
        pass

    @abstractmethod
    def reset_number_of_failures_to_zero(self, notification):
        """
        Resets the number of failures for the given notification back to zero.
        """
        pass

    @abstractmethod
    def increment_notification_failure_count(self, notification):
        """
        Increments the number of failures on the given notification.
        """
        pass

    @abstractmethod
    def create_notification_for_testing(
        self, target_username, method_name=None, method_config=None
    ):
        """
        Creates a notification for testing.
        """
        pass

    @abstractmethod
    def user_has_local_notifications(self, target_username):
        """
        Returns whether there are any Quay-local notifications for the given user.
        """
        pass
