"""
add repository kind.

Revision ID: b4df55dea4b3
Revises: 7a525c68eb13
Create Date: 2017-03-19 12:59:41.484430
"""

# revision identifiers, used by Alembic.
revision = "b4df55dea4b3"
down_revision = "b8ae68ad3e52"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.create_table(
        "repositorykind",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorykind")),
    )
    op.create_index("repositorykind_name", "repositorykind", ["name"], unique=True)

    op.bulk_insert(
        tables.repositorykind, [{"id": 1, "name": "image"}, {"id": 2, "name": "application"},],
    )

    op.add_column(
        "repository", sa.Column("kind_id", sa.Integer(), nullable=False, server_default="1")
    )
    op.create_index("repository_kind_id", "repository", ["kind_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_repository_kind_id_repositorykind"),
        "repository",
        "repositorykind",
        ["kind_id"],
        ["id"],
    )

    # ### population of test data ### #
    tester.populate_column("repository", "kind_id", tester.TestDataType.Foreign("repositorykind"))
    # ### end population of test data ### #


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.drop_constraint(
        op.f("fk_repository_kind_id_repositorykind"), "repository", type_="foreignkey"
    )
    op.drop_index("repository_kind_id", table_name="repository")
    op.drop_column("repository", "kind_id")
    op.drop_table("repositorykind")
