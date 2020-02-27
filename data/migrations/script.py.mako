"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}

import sqlalchemy as sa
${imports if imports else ""}

def upgrade(op, tables, tester):
    ${upgrades if upgrades else "pass"}


def downgrade(op, tables, tester):
    ${downgrades if downgrades else "pass"}
