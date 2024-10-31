"""add oauth assigned token table

Revision ID: 0988213e0885
Revises: 0cdd1f27a450
Create Date: 2024-05-15 09:09:58.088599

"""

# revision identifiers, used by Alembic.
revision = "0988213e0885"
down_revision = "0cdd1f27a450"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "oauthassignedtoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=255), nullable=False),
        sa.Column("assigned_user_id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("redirect_uri", sa.String(length=255), nullable=True),
        sa.Column("scope", sa.String(length=255), nullable=False),
        sa.Column("response_type", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["oauthapplication.id"],
            name=op.f("fk_oauthassignedtoken_application_oauthapplication"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["user.id"],
            name=op.f("fk_oauthassignedtoken_assigned_user_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauthassignedtoken")),
    )
    op.create_index("oauthassignedtoken_uuid", "oauthassignedtoken", ["uuid"], unique=True)
    op.create_index(
        "oauthassignedtoken_application_id", "oauthassignedtoken", ["application_id"], unique=False
    )
    op.create_index(
        "oauthassignedtoken_assigned_user", "oauthassignedtoken", ["assigned_user_id"], unique=False
    )

    op.bulk_insert(
        tables.notificationkind,
        [
            {"name": "assigned_authorization"},
        ],
    )


def downgrade(op, tables, tester):
    op.drop_table("oauthassignedtoken")
    op.execute(
        tables.notificationkind.delete().where(
            tables.notificationkind.c.name == op.inline_literal("assigned_authorization")
        )
    )
