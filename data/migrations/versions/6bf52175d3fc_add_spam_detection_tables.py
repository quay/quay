"""add spam detection tables

Revision ID: 6bf52175d3fc
Revises: c3d4e5f6a7b8
Create Date: 2026-06-11 20:47:14.698098

"""

# revision identifiers, used by Alembic.
revision = "6bf52175d3fc"
down_revision = "c3d4e5f6a7b8"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "spamdetectionrule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("pattern", sa.Text(), nullable=True),
        sa.Column("config", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("spamdetectionrule_uuid", "spamdetectionrule", ["uuid"], unique=True)
    op.create_index("spamdetectionrule_enabled", "spamdetectionrule", ["enabled"], unique=False)

    op.create_table(
        "quarantinedrepository",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.Integer(), nullable=False),
        sa.Column("namespace_name", sa.String(length=255), nullable=False),
        sa.Column("repository_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="flagged"),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("matched_rules", sa.Text(), nullable=True),
        sa.Column("total_confidence_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_empty", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
        sa.Column("scan_id", sa.String(length=36), nullable=True),
        sa.Column("actioned_by", sa.String(length=255), nullable=True),
        sa.Column("actioned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repository.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("quarantinedrepository_uuid", "quarantinedrepository", ["uuid"], unique=True)
    op.create_index(
        "quarantinedrepository_repository_id",
        "quarantinedrepository",
        ["repository_id"],
        unique=False,
    )
    op.create_index(
        "quarantinedrepository_namespace_name",
        "quarantinedrepository",
        ["namespace_name"],
        unique=False,
    )
    op.create_index(
        "quarantinedrepository_status",
        "quarantinedrepository",
        ["status"],
        unique=False,
    )
    op.create_index(
        "quarantinedrepository_scan_id",
        "quarantinedrepository",
        ["scan_id"],
        unique=False,
    )
    op.create_index(
        "quarantinedrepository_status_confidence",
        "quarantinedrepository",
        ["status", "total_confidence_score"],
        unique=False,
    )
    op.execute(
        "CREATE UNIQUE INDEX quarantinedrepository_repo_active_uniq "
        "ON quarantinedrepository (repository_id) "
        "WHERE status IN ('flagged', 'quarantined')"
    )

    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "spam_repo_quarantined"},
            {"name": "spam_repo_restored"},
            {"name": "spam_repo_dismissed"},
        ],
    )

    op.bulk_insert(
        tables.notificationkind,
        [
            {"name": "repo_spam_quarantined"},
        ],
    )


def downgrade(op, tables, tester):
    for kind in ("spam_repo_quarantined", "spam_repo_restored", "spam_repo_dismissed"):
        op.execute(
            tables.logentrykind.delete().where(
                tables.logentrykind.c.name == op.inline_literal(kind)
            )
        )
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("repo_spam_quarantined")
        )
    )
    op.execute("DROP INDEX IF EXISTS quarantinedrepository_repo_active_uniq")
    op.drop_table("quarantinedrepository")
    op.drop_table("spamdetectionrule")
