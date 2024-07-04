"""increase repomirror's upstreamregistry password length

Revision ID: f7b928ce256a
Revises: 
Create Date: 2024-07-04 15:58:43.720439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b928ce256a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade(op, tables, tester):
    op.alter_column(
        'repomirrorconfig',
        'external_registry_password',
        type_=sa.Text(),  # Use Text type for longer fields
        nullable=True,
    )

def downgrade(op, tables, tester):
    op.alter_column(
        'repomirrorconfig',
        'external_registry_password',
        type_=sa.String(length=4096),  # Revert to the original CharField length
        nullable=True,
    )
