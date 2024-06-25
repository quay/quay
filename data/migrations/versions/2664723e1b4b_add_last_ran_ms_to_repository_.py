"""add last_ran_ms to repository_notification_table

Revision ID: 2664723e1b4b
Revises: f67fe4871771
Create Date: 2024-05-13 15:18:54.356032

"""

# revision identifiers, used by Alembic.
revision = "2664723e1b4b"
down_revision = "f67fe4871771"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    op.add_column(
        "repositorynotification", sa.Column("last_ran_ms", sa.BigInteger(), nullable=True)
    )
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    repositorynotification_indexes = inspector.get_indexes("repositorynotification")
    if not "repositorynotification_last_ran_ms" in [
        i["name"] for i in repositorynotification_indexes
    ]:
        op.create_index(
            "repositorynotification_last_ran_ms",
            "repositorynotification",
            ["last_ran_ms"],
            unique=False,
        )


def downgrade(op, tables, tester):
    op.drop_index("repositorynotification_last_ran_ms", table_name="repositorynotification")
    op.drop_column("repositorynotification", "last_ran_ms")
