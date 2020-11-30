from image.oci import OCI_CONTENT_TYPES

"""Add OCI content types

Revision ID: 04b9d2191450
Revises: 8e6a363784bb
Create Date: 2020-03-23 16:03:39.789177

"""

# revision identifiers, used by Alembic.
revision = "04b9d2191450"
down_revision = "8e6a363784bb"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(op, tables, tester):
    for media_type in OCI_CONTENT_TYPES:
        op.bulk_insert(
            tables.mediatype,
            [
                {"name": media_type},
            ],
        )


def downgrade(op, tables, tester):
    for media_type in OCI_CONTENT_TYPES:
        op.execute(
            tables.mediatype.delete().where(
                tables.mediatype.c.name == op.inline_literal(media_type)
            )
        )
