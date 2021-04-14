"""Add Index on uploading column in imagestoreage table

Revision ID: 3bd8075919b9
Revises: 88e64904d000
Create Date: 2021-04-14 14:33:28.053054

"""

# revision identifiers, used by Alembic.
revision = "3bd8075919b9"
down_revision = "88e64904d000"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_index("imagestorage_uploading", "imagestorage", ["uploading"], unique=False)


def downgrade(op, tables, tester):
    op.drop_index("imagestorage_uploading", table_name="imagestorage")
