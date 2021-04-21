"""Drop uploading column from ImageStorage

Revision ID: fdc4231fbcc1
Revises: 88e64904d000
Create Date: 2021-04-19 13:52:11.840254

"""

# revision identifiers, used by Alembic.
revision = "fdc4231fbcc1"
down_revision = "88e64904d000"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.drop_column("imagestorage", "uploading")
    op.drop_column("imagestoragesignature", "uploading")


def downgrade(op, tables, tester):
    op.add_column(
        "imagestorage",
        sa.Column(
            "checksum", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
    )
    op.add_column(
        "imagestoragesignature",
        sa.Column(
            "checksum", sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()
        ),
    )
