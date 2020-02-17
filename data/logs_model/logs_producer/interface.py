from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class LogProducerInterface(object):
    @abstractmethod
    def send(self, logentry):
        """
        Send a log entry to the configured log infrastructure.
        """
