import json

from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class RepositoryNotification(
    namedtuple(
        "RepositoryNotification",
        [
            "uuid",
            "title",
            "event_name",
            "method_name",
            "config_json",
            "event_config_json",
            "number_of_failures",
        ],
    )
):
    """
    RepositoryNotification represents a notification for a repository.

    :type uuid: string
    :type event: string
    :type method: string
    :type config: string
    :type title: string
    :type event_config: string
    :type number_of_failures: int
    """

    def to_dict(self):
        try:
            config = json.loads(self.config_json)
        except ValueError:
            config = {}

        try:
            event_config = json.loads(self.event_config_json)
        except ValueError:
            event_config = {}

        return {
            "uuid": self.uuid,
            "title": self.title,
            "event": self.event_name,
            "method": self.method_name,
            "config": config,
            "event_config": event_config,
            "number_of_failures": self.number_of_failures,
        }


@add_metaclass(ABCMeta)
class RepoNotificationInterface(object):
    """
    Interface that represents all data store interactions required by the RepositoryNotification
    API.
    """

    @abstractmethod
    def create_repo_notification(
        self,
        namespace_name,
        repository_name,
        event_name,
        method_name,
        method_config,
        event_config,
        title=None,
    ):
        """

        Args:
          namespace_name: namespace of repository
          repository_name: name of repository
          event_name: name of event
          method_name: name of method
          method_config: method config, json string
          event_config: event config, json string
          title: title of the notification

        Returns:
          RepositoryNotification object

        """
        pass

    @abstractmethod
    def list_repo_notifications(self, namespace_name, repository_name, event_name=None):
        """

        Args:
          namespace_name: namespace of repository
          repository_name: name of repository
          event_name: name of event

        Returns:
          list(RepositoryNotification)
        """
        pass

    @abstractmethod
    def get_repo_notification(self, uuid):
        """

        Args:
          uuid: uuid of notification

        Returns:
          RepositoryNotification or None

        """
        pass

    @abstractmethod
    def delete_repo_notification(self, namespace_name, repository_name, uuid):
        """

        Args:
          namespace_name: namespace of repository
          repository_name: name of repository
          uuid: uuid of notification

        Returns:
          RepositoryNotification or None

        """
        pass

    @abstractmethod
    def reset_notification_number_of_failures(self, namespace_name, repository_name, uuid):
        """

        Args:
          namespace_name: namespace of repository
          repository_name: name of repository
          uuid: uuid of notification

        Returns:
          RepositoryNotification

        """
        pass

    @abstractmethod
    def queue_test_notification(self, uuid):
        """

        Args:
          uuid: uuid of notification

        Returns:
          RepositoryNotification or None

        """
        pass
