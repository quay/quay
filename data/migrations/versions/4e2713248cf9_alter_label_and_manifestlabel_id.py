"""alter label and manifestlabel id

Revision ID: 4e2713248cf9
Revises: 9fa37f66a9b6
Create Date: 2026-09-15 02:28:21.647181

"""

# revision identifiers, used by Alembic.
revision = "4e2713248cf9"
down_revision = "9fa37f66a9b6"

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    if bind.engine.name == "postgresql":
        label_columns = {
            col["name"]: str(col["type"]).lower() for col in inspector.get_columns("label")
        }
        manifestlabel_columns = {
            col["name"]: str(col["type"]).lower() for col in inspector.get_columns("manifestlabel")
        }

        if label_columns["id"] != "bigint":
            op.execute("""
                ALTER TABLE label ALTER COLUMN id TYPE BIGINT;
            """)
        op.execute("""
            ALTER SEQUENCE label_id_seq AS BIGINT;
        """)
        op.execute("""
            ALTER SEQUENCE label_id_seq MAXVALUE 9223372036854775807;
        """)
        if manifestlabel_columns["id"] != "bigint":
            op.execute("""
                ALTER TABLE manifestlabel ALTER COLUMN id TYPE BIGINT;
            """)
        op.execute("""
            ALTER SEQUENCE manifestlabel_id_seq AS BIGINT;
        """)
        op.execute("""
            ALTER SEQUENCE manifestlabel_id_seq MAXVALUE 9223372036854775807;
        """)
        if manifestlabel_columns["label_id"] != "bigint":
            op.execute("""
                ALTER TABLE manifestlabel ALTER COLUMN label_id TYPE BIGINT;
            """)


def downgrade(op, tables, tester):
    op.execute("""
        ALTER TABLE manifestlabel ALTER COLUMN label_id TYPE INTEGER;
    """)
    op.execute("""
        ALTER TABLE manifestlabel ALTER COLUMN id TYPE INTEGER;
    """)
    op.execute("""
        ALTER SEQUENCE manifestlabel_id_seq AS INTEGER;
    """)
    op.execute("""
        ALTER SEQUENCE manifestlabel_id_seq MAXVALUE 2147483647;
    """)
    op.execute("""
        ALTER TABLE label ALTER COLUMN id TYPE INTEGER;
    """)
    op.execute("""
        ALTER SEQUENCE label_id_seq AS INTEGER;
    """)
    op.execute("""
        ALTER SEQUENCE label_id_seq MAXVALUE 2147483647;
    """)
