"""
Repository Mirror.

Revision ID: 5248ddf35167
Revises: b918abdbee43
Create Date: 2019-06-25 16:22:36.310532
"""

revision = "5248ddf35167"
down_revision = "b918abdbee43"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(op, tables, tester):
    op.create_table(
        "repomirrorrule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("creation_date", sa.DateTime(), nullable=False),
        sa.Column("rule_type", sa.Integer(), nullable=False),
        sa.Column("rule_value", sa.Text(), nullable=False),
        sa.Column("left_child_id", sa.Integer(), nullable=True),
        sa.Column("right_child_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["left_child_id"],
            ["repomirrorrule.id"],
            name=op.f("fk_repomirrorrule_left_child_id_repomirrorrule"),
        ),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repomirrorrule_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["right_child_id"],
            ["repomirrorrule.id"],
            name=op.f("fk_repomirrorrule_right_child_id_repomirrorrule"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repomirrorrule")),
    )
    op.create_index(
        "repomirrorrule_left_child_id", "repomirrorrule", ["left_child_id"], unique=False
    )
    op.create_index(
        "repomirrorrule_repository_id", "repomirrorrule", ["repository_id"], unique=False
    )
    op.create_index(
        "repomirrorrule_right_child_id", "repomirrorrule", ["right_child_id"], unique=False
    )
    op.create_index("repomirrorrule_rule_type", "repomirrorrule", ["rule_type"], unique=False)
    op.create_index("repomirrorrule_uuid", "repomirrorrule", ["uuid"], unique=True)

    op.create_table(
        "repomirrorconfig",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("creation_date", sa.DateTime(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("mirror_type", sa.Integer(), nullable=False),
        sa.Column("internal_robot_id", sa.Integer(), nullable=False),
        sa.Column("external_registry", sa.String(length=255), nullable=False),
        sa.Column("external_namespace", sa.String(length=255), nullable=False),
        sa.Column("external_repository", sa.String(length=255), nullable=False),
        sa.Column("external_registry_username", sa.String(length=2048), nullable=True),
        sa.Column("external_registry_password", sa.String(length=2048), nullable=True),
        sa.Column("external_registry_config", sa.Text(), nullable=False),
        sa.Column("sync_interval", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("sync_start_date", sa.DateTime(), nullable=True),
        sa.Column("sync_expiration_date", sa.DateTime(), nullable=True),
        sa.Column("sync_retries_remaining", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("sync_status", sa.Integer(), nullable=False),
        sa.Column("sync_transaction_id", sa.String(length=36), nullable=True),
        sa.Column("root_rule_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repomirrorconfig_repository_id_repository"),
        ),
        sa.ForeignKeyConstraint(
            ["root_rule_id"],
            ["repomirrorrule.id"],
            name=op.f("fk_repomirrorconfig_root_rule_id_repomirrorrule"),
        ),
        sa.ForeignKeyConstraint(
            ["internal_robot_id"],
            ["user.id"],
            name=op.f("fk_repomirrorconfig_internal_robot_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repomirrorconfig")),
    )
    op.create_index(
        "repomirrorconfig_mirror_type", "repomirrorconfig", ["mirror_type"], unique=False
    )
    op.create_index(
        "repomirrorconfig_repository_id", "repomirrorconfig", ["repository_id"], unique=True
    )
    op.create_index(
        "repomirrorconfig_root_rule_id", "repomirrorconfig", ["root_rule_id"], unique=False
    )
    op.create_index(
        "repomirrorconfig_sync_status", "repomirrorconfig", ["sync_status"], unique=False
    )
    op.create_index(
        "repomirrorconfig_sync_transaction_id",
        "repomirrorconfig",
        ["sync_transaction_id"],
        unique=False,
    )
    op.create_index(
        "repomirrorconfig_internal_robot_id",
        "repomirrorconfig",
        ["internal_robot_id"],
        unique=False,
    )

    op.add_column(
        "repository", sa.Column("state", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_index("repository_state", "repository", ["state"], unique=False)

    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "repo_mirror_enabled"},
            {"name": "repo_mirror_disabled"},
            {"name": "repo_mirror_config_changed"},
            {"name": "repo_mirror_sync_started"},
            {"name": "repo_mirror_sync_failed"},
            {"name": "repo_mirror_sync_success"},
            {"name": "repo_mirror_sync_now_requested"},
            {"name": "repo_mirror_sync_tag_success"},
            {"name": "repo_mirror_sync_tag_failed"},
            {"name": "repo_mirror_sync_test_success"},
            {"name": "repo_mirror_sync_test_failed"},
            {"name": "repo_mirror_sync_test_started"},
            {"name": "change_repo_state"},
        ],
    )

    tester.populate_table(
        "repomirrorrule",
        [
            ("uuid", tester.TestDataType.String),
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("creation_date", tester.TestDataType.DateTime),
            ("rule_type", tester.TestDataType.Integer),
            ("rule_value", tester.TestDataType.String),
        ],
    )

    tester.populate_table(
        "repomirrorconfig",
        [
            ("repository_id", tester.TestDataType.Foreign("repository")),
            ("creation_date", tester.TestDataType.DateTime),
            ("is_enabled", tester.TestDataType.Boolean),
            ("mirror_type", tester.TestDataType.Constant(1)),
            ("internal_robot_id", tester.TestDataType.Foreign("user")),
            ("external_registry", tester.TestDataType.String),
            ("external_namespace", tester.TestDataType.String),
            ("external_repository", tester.TestDataType.String),
            ("external_registry_username", tester.TestDataType.String),
            ("external_registry_password", tester.TestDataType.String),
            ("external_registry_config", tester.TestDataType.JSON),
            ("sync_start_date", tester.TestDataType.DateTime),
            ("sync_expiration_date", tester.TestDataType.DateTime),
            ("sync_retries_remaining", tester.TestDataType.Integer),
            ("sync_status", tester.TestDataType.Constant(0)),
            ("sync_transaction_id", tester.TestDataType.String),
            ("root_rule_id", tester.TestDataType.Foreign("repomirrorrule")),
        ],
    )


def downgrade(op, tables, tester):
    op.drop_column("repository", "state")

    op.drop_table("repomirrorconfig")

    op.drop_table("repomirrorrule")

    for logentrykind in [
        "repo_mirror_enabled",
        "repo_mirror_disabled",
        "repo_mirror_config_changed",
        "repo_mirror_sync_started",
        "repo_mirror_sync_failed",
        "repo_mirror_sync_success",
        "repo_mirror_sync_now_requested",
        "repo_mirror_sync_tag_success",
        "repo_mirror_sync_tag_failed",
        "repo_mirror_sync_test_success",
        "repo_mirror_sync_test_failed",
        "repo_mirror_sync_test_started",
        "change_repo_state",
    ]:
        op.execute(
            tables.logentrykind.delete().where(
                tables.logentrykind.c.name == op.inline_literal(logentrykind)
            )
        )
