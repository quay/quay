from image.docker.schema2 import DOCKER_SCHEMA2_CONTENT_TYPES

"""Add schema2 media types

Revision ID: c00a1f15968b
Revises: 67f0abd172ae
Create Date: 2018-11-13 09:20:21.968503

"""

# revision identifiers, used by Alembic.
revision = "c00a1f15968b"
down_revision = "67f0abd172ae"


def upgrade(op, tables, tester):
    for media_type in DOCKER_SCHEMA2_CONTENT_TYPES:
        op.bulk_insert(
            tables.mediatype,
            [
                {"name": media_type},
            ],
        )


def downgrade(op, tables, tester):
    for media_type in DOCKER_SCHEMA2_CONTENT_TYPES:
        op.execute(
            tables.mediatype.delete().where(
                tables.mediatype.c.name == op.inline_literal(media_type)
            )
        )
