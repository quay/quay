"""Drop checksum on ImageStorage

Revision ID: c91c564aad34
Revises: 152bb29a1bb3
Create Date: 2018-02-21 12:17:52.405644

"""

# revision identifiers, used by Alembic.
revision = "c91c564aad34"
down_revision = "152bb29a1bb3"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.drop_column("imagestorage", "checksum")


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)
    op.add_column("imagestorage", sa.Column("checksum", sa.String(length=255), nullable=True))
