"""create tag_notification_sent table

Revision ID: f67fe4871771
Revises: 66147b81aad2
Create Date: 2024-05-13 14:50:11.171686

"""

# revision identifiers, used by Alembic.
revision = "f67fe4871771"
down_revision = "66147b81aad2"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "tagnotificationsuccess",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column("method_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["repositorynotification.id"],
            name=op.f("fk_tag_notification_success_notification_id"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tag.id"],
            name=op.f("fk_tag_notification_success_tag_id"),
        ),
        sa.ForeignKeyConstraint(
            ["method_id"],
            ["externalnotificationmethod.id"],
            name=op.f("fk_tag_notification_success_method_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tag_notification_success")),
    )
    op.create_index(
        "tagnotificationsuccess_notification_id",
        "tagnotificationsuccess",
        ["notification_id"],
        unique=False,
    )
    op.create_index(
        "tagnotificationsuccess_tag_id", "tagnotificationsuccess", ["tag_id"], unique=False
    )


def downgrade(op, tables, tester):
    op.drop_table("tagnotificationsuccess")
