"""Make BlodUpload byte_count not nullable

Revision ID: 152edccba18c
Revises: c91c564aad34
Create Date: 2018-02-23 12:41:25.571835

"""

# revision identifiers, used by Alembic.
revision = "152edccba18c"
down_revision = "c91c564aad34"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.alter_column("blobupload", "byte_count", existing_type=sa.BigInteger(), nullable=False)


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.alter_column("blobupload", "byte_count", existing_type=sa.BigInteger(), nullable=True)
