from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class GlobalPromStatsWorkerDataInterface(object):
    """
  Interface that represents all data store interactions required by the global prom stats worker.
  """

    @abstractmethod
    def get_repository_count(self):
        """ Returns the number of repositories in the database. """
        pass

    @abstractmethod
    def get_active_user_count(self):
        """ Returns the number of active users in the database. """
        pass

    @abstractmethod
    def get_active_org_count(self):
        """ Returns the number of active organizations in the database. """
        pass

    @abstractmethod
    def get_robot_count(self):
        """ Returns the number of robots in the database. """
        pass
