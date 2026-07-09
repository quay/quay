import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.migrations.tester import NoopTester
from data.migrations.versions import (
    b30800b1d271_add_oauth_token_display_name as migration,
)


def _operations(connection):
    context = MigrationContext.configure(connection, opts={"render_as_batch": True})
    return Operations(context)


def _column_names(connection, table_name):
    return {column["name"] for column in sa.inspect(connection).get_columns(table_name)}


def _column(connection, table_name, column_name):
    return next(
        column
        for column in sa.inspect(connection).get_columns(table_name)
        if column["name"] == column_name
    )


def test_oauth_token_display_name_migration_upgrade_and_downgrade():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "oauthaccesstoken",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("token_name", sa.String(length=255), nullable=False),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        migration.upgrade(_operations(connection), None, NoopTester())

        columns = _column_names(connection, "oauthaccesstoken")
        assert "display_name" in columns
        assert _column(connection, "oauthaccesstoken", "display_name")["nullable"] is True

        migration.downgrade(_operations(connection), None, NoopTester())

        columns = _column_names(connection, "oauthaccesstoken")
        assert "display_name" not in columns
