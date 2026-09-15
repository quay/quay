from importlib import import_module
from types import SimpleNamespace

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.migrations.tester import NoopTester

migration = import_module(
    "data.migrations.versions.8fd6edfc06db_add_workload_identity_audit_log_kinds"
)


def _operations(connection):
    context = MigrationContext.configure(connection, opts={"render_as_batch": True})
    return Operations(context)


def test_workload_identity_audit_log_kinds_migration_upgrade_and_downgrade():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    logentrykind = sa.Table(
        "logentrykind",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        tables = SimpleNamespace(logentrykind=logentrykind)
        migration.upgrade(_operations(connection), tables, NoopTester())

        expected = {
            "workload_identity_token_exchange",
            "workload_identity_token_exchange_failed",
        }
        assert set(connection.execute(sa.select(logentrykind.c.name)).scalars()) == expected

        migration.downgrade(_operations(connection), tables, NoopTester())

        assert set(connection.execute(sa.select(logentrykind.c.name)).scalars()) == set()
