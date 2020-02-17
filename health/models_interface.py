from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class HealthCheckDataInterface(object):
    """
    Interface that represents all data store interactions required by health checks.
    """

    @abstractmethod
    def check_health(self, app_config):
        """
        Returns True if the connection to the database is healthy and False otherwise.
        """
        pass
