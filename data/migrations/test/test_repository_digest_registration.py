import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.database import RepositoryBlobDigest, RepositoryManifestDigest
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


def _columns_by_name(connection, table_name):
    return {column["name"]: column for column in sa.inspect(connection).get_columns(table_name)}


def _column_names(connection, table_name):
    return set(_columns_by_name(connection, table_name))


def _foreign_key_targets(connection, table_name):
    return {
        foreign_key["name"]: (
            foreign_key["constrained_columns"],
            foreign_key["referred_table"],
            foreign_key["referred_columns"],
        )
        for foreign_key in sa.inspect(connection).get_foreign_keys(table_name)
    }


def test_repository_digest_model_field_lengths():
    assert RepositoryBlobDigest._meta.fields["digest"].max_length == 255
    assert RepositoryManifestDigest._meta.fields["digest"].max_length == 255


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

        blob_columns = _columns_by_name(connection, "repositoryblobdigest")
        manifest_columns = _columns_by_name(connection, "repositorymanifestdigest")
        assert blob_columns["digest"]["type"].length == 255
        assert manifest_columns["digest"]["type"].length == 255

        blob_upload_columns = _columns_by_name(connection, "blobupload")
        assert {
            "requested_digest_algorithm",
            "requested_digest_state",
        } <= set(blob_upload_columns)
        assert blob_upload_columns["requested_digest_algorithm"]["type"].length == 255
        assert blob_upload_columns["requested_digest_algorithm"]["nullable"] is True
        assert isinstance(blob_upload_columns["requested_digest_state"]["type"], sa.Text)
        assert blob_upload_columns["requested_digest_state"]["nullable"] is True
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
        blob_digest_index = blob_indexes["repositoryblobdigest_repository_id_digest"]
        manifest_digest_index = manifest_indexes["repositorymanifestdigest_repository_id_digest"]
        assert blob_digest_index["column_names"] == ["repository_id", "digest"]
        assert blob_digest_index["unique"] == 1
        assert manifest_digest_index["column_names"] == ["repository_id", "digest"]
        assert manifest_digest_index["unique"] == 1

        assert _foreign_key_targets(connection, "repositoryblobdigest") == {
            "fk_repositoryblobdigest_repository_id": (
                ["repository_id"],
                "repository",
                ["id"],
            ),
            "fk_repositoryblobdigest_image_storage_id": (
                ["image_storage_id"],
                "imagestorage",
                ["id"],
            ),
        }
        assert _foreign_key_targets(connection, "repositorymanifestdigest") == {
            "fk_repositorymanifestdigest_repository_id": (
                ["repository_id"],
                "repository",
                ["id"],
            ),
            "fk_repositorymanifestdigest_manifest_id": (
                ["manifest_id"],
                "manifest",
                ["id"],
            ),
        }

        migration.downgrade(_operations(connection), None, NoopTester())

        table_names = set(sa.inspect(connection).get_table_names())
        assert "repositoryblobdigest" not in table_names
        assert "repositorymanifestdigest" not in table_names
        assert "requested_digest_algorithm" not in _column_names(connection, "blobupload")
        assert "requested_digest_state" not in _column_names(connection, "blobupload")
