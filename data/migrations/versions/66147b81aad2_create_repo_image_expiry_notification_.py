"""create repo_image_expiry notification type

Revision ID: 66147b81aad2
Revises: 0988213e0885
Create Date: 2024-05-13 14:28:58.794953

"""

# revision identifiers, used by Alembic.
revision = "66147b81aad2"
down_revision = "0988213e0885"


def upgrade(op, tables, tester):
    op.bulk_insert(
        tables.externalnotificationevent,
        [
            {"name": "repo_image_expiry"},
        ],
    )


def downgrade(op, tables, tester):
    op.execute(
        tables.externalnotificationevent.delete().where(
            tables.externalnotificationevent.c.name == op.inline_literal("repo_image_expiry")
        )
    )
