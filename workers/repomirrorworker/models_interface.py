from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class RepoMirrorToken(namedtuple("NextRepoMirrorToken", ["min_id"])):
    """
    RepoMirrorToken represents an opaque token that can be passed between runs of the repository
    mirror worker to continue mirroring whereever the previous run left off.

    Note that the data of the token is *opaque* to the repository mirror worker, and the worker
    should *not* pull any data out or modify the token in any way.
    """


@add_metaclass(ABCMeta)
class RepoMirrorWorkerDataInterface(object):
    @abstractmethod
    def repositories_to_mirror(self, target_time, start_token=None):
        """
        Returns a tuple consisting of an iterator of all the candidates to scan and a NextScanToken.

        The iterator returns a tuple for each iteration consisting of the candidate Repository, the
        abort signal, and the number of remaining candidates. If the iterator returned is None,
        there are no candidates to process.
        """
