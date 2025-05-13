"""alter manifestblob id

Revision ID: e8ed3fb547da
Revises: 3634f2df3c5b
Create Date: 2025-05-13 09:45:39.152681

"""

# revision identifiers, used by Alembic.
revision = "e8ed3fb547da"
down_revision = "3634f2df3c5b"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    bind = op.get_bind()
    if bind.engine.name == "postgresql":
        result = op.execute(
            """
            SELECT data_type FROM information_schema.columns WHERE table_name = 'manifestblob' AND column_name = 'id';
        """
        )
        if str(result[0]).lower() == "bigint":
            return

        op.execute(
            """
            ALTER TABLE manifestblob ALTER COLUMN id TYPE BIGINT;
        """
        )
        op.execute(
            """
            ALTER SEQUENCE manifestblob_id_seq AS BIGINT;
        """
        )
        op.execute(
            """
            ALTER SEQUENCE manifestblob_id_seq MAXVALUE 9223372036854775807;
        """
        )


def downgrade(op, tables, tester):
    op.execute(
        """
        ALTER TABLE manifestblob ALTER COLUMN id TYPE INTEGER;
    """
    )
    op.execute(
        """
        ALTER SEQUENCE manifestblob_id_seq AS INTEGER;
    """
    )
    op.execute(
        """
        ALTER SEQUENCE manifestblob_id_seq MAXVALUE 2147483647;
    """
    )
