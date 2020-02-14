from abc import ABCMeta, abstractmethod

from six import add_metaclass


@add_metaclass(ABCMeta)
class InitDataInterface(object):
    """
    Interface that represents all data store interactions required by __init__.
    """

    @abstractmethod
    def is_app_repository(self, namespace_name, repository_name):
        """
    
    Args:
      namespace_name: namespace or user 
      repository_name: repository 
    
    Returns:
      Boolean
    """
        pass

    @abstractmethod
    def repository_is_public(self, namespace_name, repository_name):
        """
    
    Args:
      namespace_name: namespace or user 
      repository_name: repository 

    Returns:
      Boolean
    """
        pass

    @abstractmethod
    def log_action(self, kind, namespace_name, repository_name, performer, ip, metadata):
        """
    
    Args:
      kind: type of log
      user_or_orgname: name of user or organization
      performer: user doing the action
      ip: originating ip
      metadata: metadata
      repository: repository the action is related to

    Returns:
      None
    """
        pass
