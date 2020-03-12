"""
Backfill new appr tables.

Revision ID: 5d463ea1e8a8
Revises: 610320e9dacf
Create Date: 2018-07-08 10:01:19.756126
"""

# revision identifiers, used by Alembic.
revision = "5d463ea1e8a8"
down_revision = "610320e9dacf"

import sqlalchemy as sa
from util.migrate.table_ops import copy_table_contents


def upgrade(op, tables, tester):
    conn = op.get_bind()

    copy_table_contents("blob", "apprblob", conn)
    copy_table_contents("manifest", "apprmanifest", conn)
    copy_table_contents("manifestlist", "apprmanifestlist", conn)
    copy_table_contents("blobplacement", "apprblobplacement", conn)
    copy_table_contents("manifestblob", "apprmanifestblob", conn)
    copy_table_contents("manifestlistmanifest", "apprmanifestlistmanifest", conn)
    copy_table_contents("tag", "apprtag", conn)


def downgrade(op, tables, tester):
    pass
