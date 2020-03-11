"""
Change BlobUpload fields to BigIntegers to allow layers > 8GB.

Revision ID: b8ae68ad3e52
Revises: 7a525c68eb13
Create Date: 2017-02-27 11:26:49.182349
"""

# revision identifiers, used by Alembic.
revision = "b8ae68ad3e52"
down_revision = "7a525c68eb13"

import sqlalchemy as sa
from sqlalchemy.dialects import mysql


def upgrade(op, tables, tester):
    op.alter_column("blobupload", "byte_count", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column(
        "blobupload", "uncompressed_byte_count", existing_type=sa.Integer(), type_=sa.BigInteger()
    )

    # ### population of test data ### #
    tester.populate_column("blobupload", "byte_count", tester.TestDataType.BigInteger)
    tester.populate_column("blobupload", "uncompressed_byte_count", tester.TestDataType.BigInteger)
    # ### end population of test data ### #


def downgrade(op, tables, tester):
    # ### population of test data ### #
    tester.populate_column("blobupload", "byte_count", tester.TestDataType.Integer)
    tester.populate_column("blobupload", "uncompressed_byte_count", tester.TestDataType.Integer)
    # ### end population of test data ### #

    op.alter_column("blobupload", "byte_count", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column(
        "blobupload", "uncompressed_byte_count", existing_type=sa.BigInteger(), type_=sa.Integer()
    )
