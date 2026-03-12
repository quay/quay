"""add immutability audit log kinds

Revision ID: c3d4e5f6a7b8
Revises: 414c5e2fc487
Create Date: 2026-03-11 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "414c5e2fc487"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "tag_made_immutable_by_policy"},
            {"name": "tags_made_immutable_by_policy"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "tag_made_immutable_by_policy",
                    "tags_made_immutable_by_policy",
                ]
            )
        )
    )
