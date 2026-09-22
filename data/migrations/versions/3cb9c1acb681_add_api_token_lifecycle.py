"""add API token lifecycle metadata

Revision ID: 3cb9c1acb681
Revises: 9fa37f66a9b6
Create Date: 2026-09-15 20:05:12.730436

"""

import sqlalchemy as sa

from util.migrate import UTF8CharField

# revision identifiers, used by Alembic.
revision = "3cb9c1acb681"
down_revision = "9fa37f66a9b6"


def upgrade(op, tables, tester):
    op.create_table(
        "apitoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", UTF8CharField(length=255), nullable=False),
        sa.Column("subject_user_id", sa.Integer(), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=True),
        sa.Column("token_name", UTF8CharField(length=255), nullable=False),
        sa.Column("token_code", UTF8CharField(length=255), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("display_name", UTF8CharField(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("last_accessed", sa.DateTime(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["subject_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["creator_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("apitoken_subject_user_id", "apitoken", ["subject_user_id"])
    op.create_index("apitoken_token_name", "apitoken", ["token_name"], unique=True)
    op.create_index(
        "apitoken_subject_user_id_revoked_at_expires_at",
        "apitoken",
        ["subject_user_id", "revoked_at", "expires_at"],
    )
    op.bulk_insert(
        tables.logentrykind,
        [{"name": "create_robot_api_token"}, {"name": "revoke_robot_api_token"}],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(["create_robot_api_token", "revoke_robot_api_token"])
        )
    )
    op.drop_table("apitoken")
