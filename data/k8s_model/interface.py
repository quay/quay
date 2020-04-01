from abc import ABCMeta, abstractmethod, abstractproperty
from six import add_metaclass


@add_metaclass(ABCMeta)
class K8sClusterInterface(object):
    """
    Interface for working with the Kubernetes data model.

    This model encapsulates all access when speaking to a registered Kubernetes API,
    as well as any data tracking in the database.
    """

    @abstractmethod
    def register_cluster(self, access_info):
        """
        Adds access to a new Kubernetes cluster using the given `access_info`.
        """

    @abstractmethod
    def deregister_cluster(self, access_uuid):
        """
        Removes access to an existing Kubernetes cluster using the given `access_uuid`.
        """
