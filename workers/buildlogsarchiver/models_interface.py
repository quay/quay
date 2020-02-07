from abc import ABCMeta, abstractmethod
from collections import namedtuple
from six import add_metaclass


class Build(namedtuple("Build", ["uuid", "logs_archived"])):
    """
    Build represents a single build in the build system.
    """


@add_metaclass(ABCMeta)
class BuildLogsArchiverWorkerDataInterface(object):
    """
    Interface that represents all data store interactions required by the build logs archiver
    worker.
    """

    @abstractmethod
    def get_archivable_build(self):
        """
        Returns a build whose logs are available for archiving.

        If none, returns None.
        """
        pass

    @abstractmethod
    def get_build(self, build_uuid):
        """
        Returns the build with the matching UUID or None if none.
        """
        pass

    @abstractmethod
    def mark_build_archived(self, build_uuid):
        """
        Marks the build with the given UUID as having its logs archived.

        Returns False if the build was already marked as archived.
        """
        pass

    @abstractmethod
    def create_build_for_testing(self):
        """
        Creates an unarchived build for testing of archiving.
        """
        pass
