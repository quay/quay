"""add organization level mirror tables

Revision ID: a1b2c3d4e5f6
Revises: 27d0df099ac4
Create Date: 2026-01-15 10:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "27d0df099ac4"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    inspector = Inspector.from_engine(op.get_bind())
    table_names = inspector.get_table_names()

    # Create OrgMirrorConfig table
    if "orgmirrorconfig" not in table_names:
        op.create_table(
            "orgmirrorconfig",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("creation_date", sa.DateTime(), nullable=False),
            sa.Column(
                "is_enabled", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()
            ),
            # Mirror type (1=PULL)
            sa.Column("mirror_type", sa.Integer(), nullable=False, server_default="1"),
            # External registry configuration
            sa.Column("external_registry_type", sa.Integer(), nullable=False),
            sa.Column("external_registry_url", sa.String(length=2048), nullable=False),
            sa.Column("external_namespace", sa.String(length=255), nullable=False),
            # Credentials
            sa.Column("external_registry_username", sa.String(length=4096), nullable=True),
            sa.Column("external_registry_password", sa.String(length=9000), nullable=True),
            sa.Column("external_registry_config", sa.Text(), nullable=False),
            # Robot account
            sa.Column("internal_robot_id", sa.Integer(), nullable=False),
            # Repository filtering - list of glob patterns (e.g., ["ubuntu", "debian*"])
            sa.Column("repository_filters", sa.Text(), nullable=False),
            # Visibility for created repos
            sa.Column("visibility_id", sa.Integer(), nullable=False),
            # If True, delete mirror repos when they no longer exist in source
            sa.Column(
                "delete_stale_repos",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            ),
            # Worker scheduling
            sa.Column("sync_interval", sa.Integer(), nullable=False),
            sa.Column("sync_start_date", sa.DateTime(), nullable=True),
            sa.Column("sync_expiration_date", sa.DateTime(), nullable=True),
            sa.Column("sync_retries_remaining", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("sync_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sync_transaction_id", sa.String(length=36), nullable=True),
            # Skopeo timeout
            sa.Column("skopeo_timeout", sa.BigInteger(), nullable=False, server_default="300"),
            # Foreign key constraints
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["user.id"],
                name=op.f("fk_orgmirrorconfig_organization_id_user"),
            ),
            sa.ForeignKeyConstraint(
                ["internal_robot_id"],
                ["user.id"],
                name=op.f("fk_orgmirrorconfig_internal_robot_id_user"),
            ),
            sa.ForeignKeyConstraint(
                ["visibility_id"],
                ["visibility.id"],
                name=op.f("fk_orgmirrorconfig_visibility_id_visibility"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_orgmirrorconfig")),
        )

    # Create indexes for OrgMirrorConfig
    orgmirrorconfig_indexes = inspector.get_indexes("orgmirrorconfig")
    orgmirrorconfig_index_names = [i["name"] for i in orgmirrorconfig_indexes]

    if "orgmirrorconfig_organization_id" not in orgmirrorconfig_index_names:
        op.create_index(
            "orgmirrorconfig_organization_id",
            "orgmirrorconfig",
            ["organization_id"],
            unique=True,
        )
    if "orgmirrorconfig_internal_robot_id" not in orgmirrorconfig_index_names:
        op.create_index(
            "orgmirrorconfig_internal_robot_id",
            "orgmirrorconfig",
            ["internal_robot_id"],
            unique=False,
        )
    if "orgmirrorconfig_sync_status" not in orgmirrorconfig_index_names:
        op.create_index(
            "orgmirrorconfig_sync_status",
            "orgmirrorconfig",
            ["sync_status"],
            unique=False,
        )
    if "orgmirrorconfig_sync_start_date" not in orgmirrorconfig_index_names:
        op.create_index(
            "orgmirrorconfig_sync_start_date",
            "orgmirrorconfig",
            ["sync_start_date"],
            unique=False,
        )

    # Create OrgMirrorRepository table
    # Refresh table_names in case orgmirrorconfig was just created
    table_names = inspector.get_table_names()
    if "orgmirrorrepository" not in table_names:
        op.create_table(
            "orgmirrorrepository",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("org_mirror_config_id", sa.Integer(), nullable=False),
            sa.Column("repository_name", sa.String(length=255), nullable=False),
            sa.Column("repository_id", sa.Integer(), nullable=True),
            # Discovery and sync tracking
            sa.Column("discovery_date", sa.DateTime(), nullable=False),
            sa.Column("sync_status", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sync_start_date", sa.DateTime(), nullable=True),
            sa.Column("sync_expiration_date", sa.DateTime(), nullable=True),
            sa.Column("sync_retries_remaining", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("sync_transaction_id", sa.String(length=36), nullable=True),
            sa.Column("last_sync_date", sa.DateTime(), nullable=True),
            sa.Column("status_message", sa.Text(), nullable=True),
            sa.Column("creation_date", sa.DateTime(), nullable=False),
            # Foreign key constraints
            sa.ForeignKeyConstraint(
                ["org_mirror_config_id"],
                ["orgmirrorconfig.id"],
                name=op.f("fk_orgmirrorrepository_org_mirror_config_id_orgmirrorconfig"),
            ),
            sa.ForeignKeyConstraint(
                ["repository_id"],
                ["repository.id"],
                name=op.f("fk_orgmirrorrepository_repository_id_repository"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_orgmirrorrepository")),
        )

    # Create indexes for OrgMirrorRepository
    orgmirrorrepository_indexes = inspector.get_indexes("orgmirrorrepository")
    orgmirrorrepository_index_names = [i["name"] for i in orgmirrorrepository_indexes]

    if "orgmirrorrepository_org_mirror_config_id" not in orgmirrorrepository_index_names:
        op.create_index(
            "orgmirrorrepository_org_mirror_config_id",
            "orgmirrorrepository",
            ["org_mirror_config_id"],
            unique=False,
        )
    if "orgmirrorrepository_repository_id" not in orgmirrorrepository_index_names:
        op.create_index(
            "orgmirrorrepository_repository_id",
            "orgmirrorrepository",
            ["repository_id"],
            unique=False,
        )
    if "orgmirrorrepository_sync_status" not in orgmirrorrepository_index_names:
        op.create_index(
            "orgmirrorrepository_sync_status",
            "orgmirrorrepository",
            ["sync_status"],
            unique=False,
        )
    # Unique constraint on (org_mirror_config_id, repository_name)
    if "orgmirrorrepository_config_repo_name" not in orgmirrorrepository_index_names:
        op.create_index(
            "orgmirrorrepository_config_repo_name",
            "orgmirrorrepository",
            ["org_mirror_config_id", "repository_name"],
            unique=True,
        )
    # Composite index for efficient status counting per org mirror config
    if "orgmirrorrepository_config_status" not in orgmirrorrepository_index_names:
        op.create_index(
            "orgmirrorrepository_config_status",
            "orgmirrorrepository",
            ["org_mirror_config_id", "sync_status"],
            unique=False,
        )

    # Add log entry kinds for organization mirroring (skip if already exist)
    org_mirror_log_kinds = [
        "org_mirror_enabled",
        "org_mirror_disabled",
        "org_mirror_config_changed",
        "org_mirror_sync_started",
        "org_mirror_sync_failed",
        "org_mirror_sync_success",
        "org_mirror_sync_now_requested",
        "org_mirror_sync_cancelled",
        "org_mirror_repo_created",
    ]
    conn = op.get_bind()
    for kind_name in org_mirror_log_kinds:
        result = conn.execute(
            sa.text("SELECT 1 FROM logentrykind WHERE name = :name"), {"name": kind_name}
        )
        if result.fetchone() is None:
            op.execute(tables.logentrykind.insert().values(name=kind_name))

    # Populate test data for migration testing
    tester.populate_table(
        "orgmirrorconfig",
        [
            ("organization_id", tester.TestDataType.Foreign("user")),
            ("creation_date", tester.TestDataType.DateTime),
            ("is_enabled", tester.TestDataType.Boolean),
            ("mirror_type", tester.TestDataType.Constant(1)),  # PULL
            ("external_registry_type", tester.TestDataType.Constant(1)),  # HARBOR
            ("external_registry_url", tester.TestDataType.String),
            ("external_namespace", tester.TestDataType.String),
            ("external_registry_username", tester.TestDataType.String),
            ("external_registry_password", tester.TestDataType.String),
            ("external_registry_config", tester.TestDataType.JSON),
            ("internal_robot_id", tester.TestDataType.Foreign("user")),
            ("repository_filters", tester.TestDataType.JSON),
            ("visibility_id", tester.TestDataType.Foreign("visibility")),
            ("delete_stale_repos", tester.TestDataType.Boolean),
            ("sync_interval", tester.TestDataType.Integer),
            ("sync_start_date", tester.TestDataType.DateTime),
            ("sync_status", tester.TestDataType.Constant(0)),  # NEVER_RUN
            ("sync_transaction_id", tester.TestDataType.String),
            ("skopeo_timeout", tester.TestDataType.Integer),
        ],
    )

    tester.populate_table(
        "orgmirrorrepository",
        [
            ("org_mirror_config_id", tester.TestDataType.Foreign("orgmirrorconfig")),
            ("repository_name", tester.TestDataType.String),
            ("discovery_date", tester.TestDataType.DateTime),
            ("sync_status", tester.TestDataType.Constant(0)),  # NEVER_RUN
            ("sync_retries_remaining", tester.TestDataType.Integer),
            ("sync_transaction_id", tester.TestDataType.String),
            ("creation_date", tester.TestDataType.DateTime),
        ],
    )


def downgrade(op, tables, tester):
    inspector = Inspector.from_engine(op.get_bind())
    table_names = inspector.get_table_names()

    # Drop tables in reverse order (child first)
    if "orgmirrorrepository" in table_names:
        op.drop_table("orgmirrorrepository")
    if "orgmirrorconfig" in table_names:
        op.drop_table("orgmirrorconfig")

    # Remove log entry kinds
    for logentrykind in [
        "org_mirror_enabled",
        "org_mirror_disabled",
        "org_mirror_config_changed",
        "org_mirror_sync_started",
        "org_mirror_sync_failed",
        "org_mirror_sync_success",
        "org_mirror_sync_now_requested",
        "org_mirror_sync_cancelled",
        "org_mirror_repo_created",
    ]:
        op.execute(
            tables.logentrykind.delete().where(
                tables.logentrykind.c.name == op.inline_literal(logentrykind)
            )
        )
