"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa
${imports if imports else ""}

def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

    ${upgrades if upgrades else "pass"}


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

    ${downgrades if downgrades else "pass"}
