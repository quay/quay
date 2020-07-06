import os

from abc import ABCMeta, abstractmethod, abstractproperty
from collections import namedtuple
from six import add_metaclass

MigrationPhase = namedtuple("MigrationPhase", ["name", "alembic_revision", "flags"])


@add_metaclass(ABCMeta)
class DataMigration(object):
    @abstractproperty
    def alembic_migration_revision(self):
        """
        Returns the alembic migration revision corresponding to the currently configured phase.
        """

    @abstractmethod
    def has_flag(self, flag):
        """
        Returns true if the data migration's current phase has the given flag set.
        """


class NullDataMigration(DataMigration):
    @property
    def alembic_migration_revision(self):
        return "head"

    def has_flag(self, flag):
        raise NotImplementedError()


class DefinedDataMigration(DataMigration):
    def __init__(self, name, env_var, phases):
        assert phases

        self.name = name
        self.phases = {phase.name: phase for phase in phases}

        # Add a synthetic phase for new installations that skips the entire migration.
        self.phases["new-installation"] = phases[-1]._replace(
            name="new-installation", alembic_revision="head"
        )

        phase_name = os.getenv(env_var)
        if phase_name is None:
            msg = "Missing env var `%s` for data migration `%s`. %s" % (
                env_var,
                self.name,
                self._error_suffix,
            )
            raise Exception(msg)

        current_phase = self.phases.get(phase_name)
        if current_phase is None:
            msg = "Unknown phase `%s` for data migration `%s`. %s" % (
                phase_name,
                self.name,
                self._error_suffix,
            )
            raise Exception(msg)

        self.current_phase = current_phase

    @property
    def _error_suffix(self):
        message = "Available values for this migration: %s. " % (list(self.phases.keys()))
        message += "If this is a new installation, please use `new-installation`."
        return message

    @property
    def alembic_migration_revision(self):
        assert self.current_phase
        return self.current_phase.alembic_revision

    def has_flag(self, flag):
        assert self.current_phase
        return flag in self.current_phase.flags
