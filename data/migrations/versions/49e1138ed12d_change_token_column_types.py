"""
Change token column types for encrypted columns.

Revision ID: 49e1138ed12d
Revises: 703298a825c2
Create Date: 2019-08-19 16:07:48.109889
"""
# revision identifiers, used by Alembic.
revision = "49e1138ed12d"
down_revision = "703298a825c2"

import sqlalchemy as sa


def upgrade(op, tables, tester):

    # Adjust existing fields to be nullable.
    with op.batch_alter_table("accesstoken") as batch_op:
        batch_op.alter_column("code", nullable=True, existing_type=sa.String(length=255))
    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.alter_column("access_token", nullable=True, existing_type=sa.String(length=255))
    with op.batch_alter_table("oauthauthorizationcode") as batch_op:
        batch_op.alter_column("code", nullable=True, existing_type=sa.String(length=255))
    with op.batch_alter_table("appspecificauthtoken") as batch_op:
        batch_op.alter_column("token_code", nullable=True, existing_type=sa.String(length=255))

    # Adjust new fields to be non-nullable.
    with op.batch_alter_table("accesstoken") as batch_op:
        batch_op.alter_column("token_name", nullable=False, existing_type=sa.String(length=255))
        batch_op.alter_column("token_code", nullable=False, existing_type=sa.String(length=255))

    with op.batch_alter_table("appspecificauthtoken") as batch_op:
        batch_op.alter_column("token_name", nullable=False, existing_type=sa.String(length=255))
        batch_op.alter_column("token_secret", nullable=False, existing_type=sa.String(length=255))

    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.alter_column("token_name", nullable=False, existing_type=sa.String(length=255))
        batch_op.alter_column("token_code", nullable=False, existing_type=sa.String(length=255))

    with op.batch_alter_table("oauthauthorizationcode") as batch_op:
        batch_op.alter_column("code_name", nullable=False, existing_type=sa.String(length=255))
        batch_op.alter_column(
            "code_credential",
            nullable=False,
            existing_type=sa.String(length=255),
        )


def downgrade(op, tables, tester):

    with op.batch_alter_table("accesstoken") as batch_op:
        batch_op.alter_column("token_name", nullable=True, existing_type=sa.String(length=255))
        batch_op.alter_column("token_code", nullable=True, existing_type=sa.String(length=255))

    with op.batch_alter_table("appspecificauthtoken") as batch_op:
        batch_op.alter_column("token_name", nullable=True, existing_type=sa.String(length=255))
        batch_op.alter_column("token_secret", nullable=True, existing_type=sa.String(length=255))

    with op.batch_alter_table("oauthaccesstoken") as batch_op:
        batch_op.alter_column("token_name", nullable=True, existing_type=sa.String(length=255))
        batch_op.alter_column("token_code", nullable=True, existing_type=sa.String(length=255))

    with op.batch_alter_table("oauthauthorizationcode") as batch_op:
        batch_op.alter_column("code_name", nullable=True, existing_type=sa.String(length=255))
        batch_op.alter_column(
            "code_credential",
            nullable=True,
            existing_type=sa.String(length=255),
        )
