"""add tag immutability column

Revision ID: 5b8dc452f5c3
Revises: a32e17bfad20
Create Date: 2023-05-21 13:13:10.565161

"""

# revision identifiers, used by Alembic.
revision = "5b8dc452f5c3"
down_revision = "a32e17bfad20"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # add column to track tack immutability
    op.add_column(
        table_name="tag",
        column=sa.Column(
            name="immutable",
            type_=sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )

    with op.get_context().autocommit_block():
        # needed to quickly find repositories with immutable tags (can't make those be a mirror)
        op.create_index(
            table_name="tag",
            index_name="tag_repository_id_immutable",
            columns=["repository_id", "immutable"],
            unique=False,
            postgresql_concurrently=True,
        )

        # needed to quickly find manifests with immutable tags (can't expire those via label)
        op.create_index(
            table_name="tag",
            index_name="tag_manifest_id_immutable",
            columns=["manifest_id", "immutable"],
            unique=False,
            postgresql_concurrently=True,
        )

        # needed to quickly find manifests with expiring tags (can't make those immutable)
        op.create_index(
            table_name="tag",
            index_name="tag_manifest_id_lifetime_end_ms",
            columns=["manifest_id", "lifetime_end_ms"],
            unique=False,
            postgresql_concurrently=True,
        )

    # add logentrykind for tag immutability changes
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "change_tag_immutability"},
        ],
    )


def downgrade(op, tables, tester):
    op.drop_index(table_name="tag", index_name="tag_repository_id_immutable")
    op.drop_index(table_name="tag", index_name="tag_manifest_id_immutable")
    op.drop_index(table_name="tag", index_name="tag_manifest_id_lifetime_end_ms")
    op.drop_column(table_name="tag", column_name="immutable")
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.name == op.inline_literal("change_tag_immutability")
        )
    )
