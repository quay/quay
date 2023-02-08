"""add manifestsubject table

Revision ID: b741d890db16
Revises: b2d1e4b95fc2
Create Date: 2022-11-15 13:58:44.151142

"""

# revision identifiers, used by Alembic.
revision = "b741d890db16"
down_revision = "b2d1e4b95fc2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "manifestsubject",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("manifest_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["manifest_id"], ["manifest.id"], name=op.f("fk_manifestsubject_manifest_id_manifest")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manifestsubject")),
    )


def downgrade(op, tables, tester):
    op.drop_table("manifestsubject")
