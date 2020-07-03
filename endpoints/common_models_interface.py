from typing import List

from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


USER_FIELDS: List[str] = ["uuid", "username", "email", "given_name", "family_name", "company", "location"]


class User(namedtuple("User", USER_FIELDS)):
    """
    User represents a user.
    """


@add_metaclass(ABCMeta)
class EndpointsCommonDataInterface(object):
    """
    Interface that represents all data store interactions required by the common endpoints lib.
    """

    @abstractmethod
    def get_user(self, user_uuid):
        """
        Returns the User matching the given uuid, if any or None if none.
        """

    @abstractmethod
    def get_namespace_uuid(self, namespace_name):
        """
        Returns the uuid of the Namespace with the given name, if any.
        """
