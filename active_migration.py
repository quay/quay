from enum import Enum, unique
from data.migrationutil import DefinedDataMigration, MigrationPhase


@unique
class ERTMigrationFlags(Enum):
    """ Flags for the encrypted robot token migration. """

    READ_OLD_FIELDS = "read-old"
    WRITE_OLD_FIELDS = "write-old"


ActiveDataMigration = DefinedDataMigration(
    "encrypted_robot_tokens",
    "ENCRYPTED_ROBOT_TOKEN_MIGRATION_PHASE",
    [
        MigrationPhase(
            "add-new-fields",
            "c13c8052f7a6",
            [ERTMigrationFlags.READ_OLD_FIELDS, ERTMigrationFlags.WRITE_OLD_FIELDS],
        ),
        MigrationPhase(
            "backfill-then-read-only-new", "703298a825c2", [ERTMigrationFlags.WRITE_OLD_FIELDS]
        ),
        MigrationPhase(
            "change-column-types", "49e1138ed12d", [ERTMigrationFlags.WRITE_OLD_FIELDS],
        ),
        MigrationPhase("stop-writing-both", "703298a825c2", []),
        MigrationPhase("remove-old-fields", "c059b952ed76", []),
    ],
)
