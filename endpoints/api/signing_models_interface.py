from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class SigningInterface(object):
    """
    Interface that represents all data store interactions required by the signing API endpoint.
    """

    @abstractmethod
    def is_trust_enabled(self, namespace_name, repo_name):
        """
        Returns whether the repository with the given namespace name and repository name exists and
        has trust enabled.
        """
