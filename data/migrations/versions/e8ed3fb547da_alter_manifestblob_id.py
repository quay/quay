"""alter manifestblob id

Revision ID: e8ed3fb547da
Revises: 3634f2df3c5b
Create Date: 2025-05-13 09:45:39.152681

"""

# revision identifiers, used by Alembic.
revision = "e8ed3fb547da"
down_revision = "3634f2df3c5b"

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = sa_inspect(bind)

    if bind.engine.name == "postgresql":
        columns = inspector.get_columns("manifestblob")

        for col in columns:
            if col["name"] == "id":
                if str(col["type"]).lower() == "bigint":
                    return

        op.execute(sa.text("ALTER TABLE manifestblob ALTER COLUMN id TYPE BIGINT;"))
        op.execute(sa.text("ALTER SEQUENCE manifestblob_id_seq AS BIGINT;"))
        op.execute(sa.text("ALTER SEQUENCE manifestblob_id_seq MAXVALUE 9223372036854775807;"))


def downgrade(op, tables, tester):
    # upgrade() only changes anything on PostgreSQL, so there is nothing to revert elsewhere.
    if op.get_bind().engine.name == "postgresql":
        op.execute(sa.text("ALTER TABLE manifestblob ALTER COLUMN id TYPE INTEGER;"))
        op.execute(sa.text("ALTER SEQUENCE manifestblob_id_seq AS INTEGER;"))
        op.execute(sa.text("ALTER SEQUENCE manifestblob_id_seq MAXVALUE 2147483647;"))
