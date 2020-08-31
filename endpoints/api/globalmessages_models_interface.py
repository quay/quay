from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class GlobalMessage(
    namedtuple(
        "GlobalMessage",
        [
            "uuid",
            "content",
            "severity",
            "media_type_name",
        ],
    )
):
    def to_dict(self):
        return {
            "uuid": self.uuid,
            "content": self.content,
            "severity": self.severity,
            "media_type": self.media_type_name,
        }


@add_metaclass(ABCMeta)
class GlobalMessageDataInterface(object):
    """
    Data interface for globalmessages API.
    """

    @abstractmethod
    def get_all_messages(self):
        """

        Returns:
        list(GlobalMessage)
        """

    @abstractmethod
    def create_message(self, severity, media_type_name, content):
        """

        Returns:
        GlobalMessage or None
        """

    @abstractmethod
    def delete_message(self, uuid):
        """

        Returns:
        void
        """
