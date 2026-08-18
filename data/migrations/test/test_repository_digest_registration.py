import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.migrations.tester import NoopTester
from data.migrations.versions import (
    a2f338ee672c_add_repository_digest_registration_ as migration,
)


class RecordingTester(NoopTester):
    def __init__(self):
        self.populated_tables = []

    def populate_table(self, table_name, fields):
        self.populated_tables.append((table_name, [field_name for field_name, _ in fields]))

    def populate_column(self, table_name, col_name, field_type):
        raise AssertionError("new tables must be populated with populate_table")


def _operations(connection):
    context = MigrationContext.configure(connection, opts={"render_as_batch": True})
    return Operations(context)


def _column_names(connection, table_name):
    return {column["name"] for column in sa.inspect(connection).get_columns(table_name)}


def test_repository_digest_registration_migration_upgrade_and_downgrade():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table("repository", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("imagestorage", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("manifest", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    sa.Table("blobupload", metadata, sa.Column("id", sa.Integer(), primary_key=True))
    tester = RecordingTester()

    with engine.begin() as connection:
        metadata.create_all(connection)
        migration.upgrade(_operations(connection), None, tester)

        table_names = set(sa.inspect(connection).get_table_names())
        assert "repositoryblobdigest" in table_names
        assert "repositorymanifestdigest" in table_names
        assert {
            "requested_digest_algorithm",
            "requested_digest_state",
        } <= _column_names(connection, "blobupload")
        assert tester.populated_tables == [
            (
                "repositoryblobdigest",
                ["repository_id", "image_storage_id", "digest", "created_at"],
            ),
            (
                "repositorymanifestdigest",
                ["repository_id", "manifest_id", "digest", "created_at"],
            ),
        ]

        blob_indexes = {
            index["name"]: index
            for index in sa.inspect(connection).get_indexes("repositoryblobdigest")
        }
        manifest_indexes = {
            index["name"]: index
            for index in sa.inspect(connection).get_indexes("repositorymanifestdigest")
        }
        assert blob_indexes["repositoryblobdigest_repository_id_digest"]["unique"] == 1
        assert manifest_indexes["repositorymanifestdigest_repository_id_digest"]["unique"] == 1

        migration.downgrade(_operations(connection), None, NoopTester())

        table_names = set(sa.inspect(connection).get_table_names())
        assert "repositoryblobdigest" not in table_names
        assert "repositorymanifestdigest" not in table_names
        assert "requested_digest_algorithm" not in _column_names(connection, "blobupload")
        assert "requested_digest_state" not in _column_names(connection, "blobupload")
