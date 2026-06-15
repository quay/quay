"""add_namespace_notification_tables

Revision ID: 6715e4719375
Revises: c3d4e5f6a7b8
Create Date: 2026-06-15 05:05:54.770716

"""

# revision identifiers, used by Alembic.
revision = '6715e4719375'
down_revision = 'c3d4e5f6a7b8'

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "namespacenotification",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("namespace_id", sa.Integer, nullable=False),
        sa.Column("event_id", sa.Integer, nullable=False),
        sa.Column("method_id", sa.Integer, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("config_json", sa.Text, nullable=False),
        sa.Column("event_config_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("number_of_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_ran_ms", sa.BigInteger, nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_namespacenotification")),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_namespacenotification_namespace_id"),
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["externalnotificationevent.id"],
            name=op.f("fk_namespacenotification_event_id"),
        ),
        sa.ForeignKeyConstraint(
            ["method_id"],
            ["externalnotificationmethod.id"],
            name=op.f("fk_namespacenotification_method_id"),
        ),
    )

    op.create_index(
        "namespacenotification_uuid",
        "namespacenotification",
        ["uuid"],
        unique=False,
    )

    op.create_index(
        "namespacenotification_namespace_id",
        "namespacenotification",
        ["namespace_id"],
        unique=False,
    )

    op.create_table(
        "quotanotificationstate",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("namespace_id", sa.Integer, nullable=False),
        sa.Column("threshold_percent", sa.Integer, nullable=False),
        sa.Column("last_notified_at", sa.DateTime, nullable=True),
        sa.Column("cleared", sa.Boolean, nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotanotificationstate")),
        sa.ForeignKeyConstraint(
            ["namespace_id"],
            ["user.id"],
            name=op.f("fk_quotanotificationstate_namespace_id"),
        ),
    )

    op.create_index(
        "quotanotificationstate_namespace_id",
        "quotanotificationstate",
        ["namespace_id"],
        unique=False,
    )

    op.create_index(
        "quotanotificationstate_namespace_threshold",
        "quotanotificationstate",
        ["namespace_id", "threshold_percent"],
        unique=True,
    )

    op.bulk_insert(
        tables.externalnotificationevent,
        [
            {"name": "quota_warning"},
            {"name": "quota_error"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name.in_(
                ["quota_warning", "quota_error"]
            )
        )
    )

    op.drop_table("quotanotificationstate")
    op.drop_table("namespacenotification")
