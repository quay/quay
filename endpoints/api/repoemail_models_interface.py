from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class RepositoryAuthorizedEmail(
    namedtuple(
        "RepositoryAuthorizedEmail",
        [
            "email",
            "repository_name",
            "namespace_name",
            "confirmed",
            "code",
        ],
    )
):
    """
    Tag represents a name to an image.

    :type email: string
    :type repository_name: string
    :type namespace_name: string
    :type confirmed: boolean
    :type code: string
    """

    def to_dict(self):
        return {
            "email": self.email,
            "repository": self.repository_name,
            "namespace": self.namespace_name,
            "confirmed": self.confirmed,
            "code": self.code,
        }


@add_metaclass(ABCMeta)
class RepoEmailDataInterface(object):
    """
    Interface that represents all data store interactions required by a Repo Email.
    """

    @abstractmethod
    def get_email_authorized_for_repo(self, namespace_name, repository_name, email):
        """
        Returns a RepositoryAuthorizedEmail if available else None.
        """

    @abstractmethod
    def create_email_authorization_for_repo(self, namespace_name, repository_name, email):
        """
        Returns the newly created repository authorized email.
        """
