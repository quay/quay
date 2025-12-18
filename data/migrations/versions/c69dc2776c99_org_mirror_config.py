"""
Add organization-level repository mirroring tables.

Revision ID: c69dc2776c99
Revises: 9307c3d604b4
Create Date: 2025-12-17 14:30:00.000000
"""

revision = "c69dc2776c99"
down_revision = "9307c3d604b4"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "orgmirrorconfig",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("creation_date", sa.DateTime(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("mirror_type", sa.Integer(), nullable=False),
        sa.Column("internal_robot_id", sa.Integer(), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("external_registry_username", sa.String(length=4096), nullable=True),
        sa.Column("external_registry_password", sa.String(length=9000), nullable=True),
        sa.Column("external_registry_config", sa.Text(), nullable=False),
        sa.Column("sync_interval", sa.Integer(), nullable=False),
        sa.Column("sync_start_date", sa.DateTime(), nullable=True),
        sa.Column("sync_expiration_date", sa.DateTime(), nullable=True),
        sa.Column("sync_retries_remaining", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sync_status", sa.Integer(), nullable=False),
        sa.Column("sync_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("root_rule_id", sa.Integer(), nullable=True),
        sa.Column("skopeo_timeout", sa.BigInteger(), nullable=False),
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
            ["root_rule_id"],
            ["repomirrorrule.id"],
            name=op.f("fk_orgmirrorconfig_root_rule_id_repomirrorrule"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orgmirrorconfig")),
    )

    op.create_index(
        "orgmirrorconfig_organization_id",
        "orgmirrorconfig",
        ["organization_id"],
        unique=True,
    )

    op.create_index(
        "orgmirrorconfig_internal_robot_id",
        "orgmirrorconfig",
        ["internal_robot_id"],
        unique=False,
    )

    op.create_index(
        "orgmirrorconfig_sync_status",
        "orgmirrorconfig",
        ["sync_status"],
        unique=False,
    )

    op.create_index(
        "orgmirrorconfig_root_rule_id",
        "orgmirrorconfig",
        ["root_rule_id"],
        unique=False,
    )

    op.create_table(
        "orgmirrorrepo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("org_mirror_id", sa.Integer(), nullable=False),
        sa.Column("repository_name", sa.String(length=255), nullable=False),
        sa.Column("external_repo_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("discovery_date", sa.DateTime(), nullable=False),
        sa.Column("last_sync_date", sa.DateTime(), nullable=True),
        sa.Column("repository_id", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_mirror_id"],
            ["orgmirrorconfig.id"],
            name=op.f("fk_orgmirrorrepo_org_mirror_id_orgmirrorconfig"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_orgmirrorrepo_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orgmirrorrepo")),
    )

    op.create_index(
        "orgmirrorrepo_org_mirror_id",
        "orgmirrorrepo",
        ["org_mirror_id"],
        unique=False,
    )

    op.create_index(
        "orgmirrorrepo_repository_id",
        "orgmirrorrepo",
        ["repository_id"],
        unique=False,
    )

    op.create_index(
        "orgmirrorrepo_org_mirror_id_repository_name",
        "orgmirrorrepo",
        ["org_mirror_id", "repository_name"],
        unique=True,
    )

    op.create_index(
        "orgmirrorrepo_status",
        "orgmirrorrepo",
        ["status"],
        unique=False,
    )

    # Add log entry kinds for organization mirroring audit events
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "org_mirror_enabled"},
            {"name": "org_mirror_disabled"},
            {"name": "org_mirror_config_changed"},
            {"name": "org_mirror_sync_started"},
            {"name": "org_mirror_sync_failed"},
            {"name": "org_mirror_sync_success"},
            {"name": "org_mirror_sync_now_requested"},
            {"name": "org_mirror_repo_discovered"},
            {"name": "org_mirror_repo_created"},
            {"name": "org_mirror_repo_skipped"},
            {"name": "org_mirror_repo_failed"},
        ],
    )

    tester.populate_table(
        "orgmirrorconfig",
        [
            ("organization_id", tester.TestDataType.Foreign("user")),
            ("creation_date", tester.TestDataType.DateTime),
            ("is_enabled", tester.TestDataType.Boolean),
            ("mirror_type", tester.TestDataType.Constant(1)),
            ("internal_robot_id", tester.TestDataType.Foreign("user")),
            ("external_reference", tester.TestDataType.String),
            ("external_registry_username", tester.TestDataType.String),
            ("external_registry_password", tester.TestDataType.String),
            ("external_registry_config", tester.TestDataType.JSON),
            ("sync_interval", tester.TestDataType.Integer),
            ("sync_start_date", tester.TestDataType.DateTime),
            ("sync_expiration_date", tester.TestDataType.DateTime),
            ("sync_retries_remaining", tester.TestDataType.Integer),
            ("sync_status", tester.TestDataType.Constant(0)),
            ("sync_transaction_id", tester.TestDataType.String),
            ("skopeo_timeout", tester.TestDataType.BigInteger),
        ],
    )

    tester.populate_table(
        "orgmirrorrepo",
        [
            ("org_mirror_id", tester.TestDataType.Foreign("orgmirrorconfig")),
            ("repository_name", tester.TestDataType.String),
            ("external_repo_name", tester.TestDataType.String),
            ("status", tester.TestDataType.Constant(0)),
            ("discovery_date", tester.TestDataType.DateTime),
            ("last_sync_date", tester.TestDataType.DateTime),
            ("repository_id", tester.TestDataType.Foreign("repository")),
        ],
    )


def downgrade(op, tables, tester):
    op.drop_table("orgmirrorrepo")
    op.drop_table("orgmirrorconfig")

    for logentrykind in [
        "org_mirror_enabled",
        "org_mirror_disabled",
        "org_mirror_config_changed",
        "org_mirror_sync_started",
        "org_mirror_sync_failed",
        "org_mirror_sync_success",
        "org_mirror_sync_now_requested",
        "org_mirror_repo_discovered",
        "org_mirror_repo_created",
        "org_mirror_repo_skipped",
        "org_mirror_repo_failed",
    ]:
        op.execute(
            tables.logentrykind.delete().where(
                tables.logentrykind.c.name == op.inline_literal(logentrykind)
            )
        )
