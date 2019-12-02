from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class ScanToken(namedtuple("NextScanToken", ["min_id"])):
    """
  ScanToken represents an opaque token that can be passed between runs of the security worker
  to continue scanning whereever the previous run left off. Note that the data of the token is
  *opaque* to the security worker, and the security worker should *not* pull any data out or modify
  the token in any way.
  """


@add_metaclass(ABCMeta)
class SecurityWorkerDataInterface(object):
    """
  Interface that represents all data store interactions required by the security worker.
  """

    @abstractmethod
    def candidates_to_scan(self, target_version, start_token=None):
        """
    Returns a tuple consisting of an iterator of all the candidates to scan and a NextScanToken.
    The iterator returns a tuple for each iteration consisting of the candidate Image, the abort
    signal, and the number of remaining candidates. If the iterator returned is None, there are
    no candidates to process.
    """
        pass
