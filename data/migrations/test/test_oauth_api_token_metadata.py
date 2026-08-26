from types import SimpleNamespace

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.migrations.tester import NoopTester
from data.migrations.versions import (
    d064a4f00d4a_add_oauth_api_token_metadata_and_audit_ as migration,
)


def _operations(connection):
    context = MigrationContext.configure(connection, opts={"render_as_batch": True})
    return Operations(context)


def _tables(metadata):
    return SimpleNamespace(logentrykind=metadata.tables["logentrykind"])


def _column_names(connection, table_name):
    return {column["name"] for column in sa.inspect(connection).get_columns(table_name)}


def _index_columns(connection, table_name, index_name):
    indexes = sa.inspect(connection).get_indexes(table_name)
    return next(index["column_names"] for index in indexes if index["name"] == index_name)


def test_oauth_api_token_metadata_migration_upgrade_and_downgrade():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "oauthaccesstoken",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("token_name", sa.String(length=255), nullable=False),
    )
    logentrykind = sa.Table(
        "logentrykind",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        migration.upgrade(_operations(connection), _tables(metadata), NoopTester())

        columns = _column_names(connection, "oauthaccesstoken")
        assert "created" in columns
        assert "last_accessed" in columns
        assert _index_columns(
            connection,
            "oauthaccesstoken",
            "oauthaccesstoken_application_id_last_accessed",
        ) == ["application_id", "last_accessed"]

        log_kinds = set(connection.execute(sa.select(logentrykind.c.name)).scalars())
        assert "create_oauth_api_token" in log_kinds
        assert "revoke_oauth_api_token" in log_kinds

        migration.downgrade(_operations(connection), _tables(metadata), NoopTester())

        columns = _column_names(connection, "oauthaccesstoken")
        assert "created" not in columns
        assert "last_accessed" not in columns
        assert "oauthaccesstoken_application_id_last_accessed" not in {
            index["name"] for index in sa.inspect(connection).get_indexes("oauthaccesstoken")
        }

        log_kinds = set(connection.execute(sa.select(logentrykind.c.name)).scalars())
        assert "create_oauth_api_token" not in log_kinds
        assert "revoke_oauth_api_token" not in log_kinds
