""" Change token column types for encrypted columns

Revision ID: 49e1138ed12d
Revises: 703298a825c2
Create Date: 2019-08-19 16:07:48.109889

"""
# revision identifiers, used by Alembic.
revision = "49e1138ed12d"
down_revision = "703298a825c2"

from alembic import op as original_op
from data.migrations.progress import ProgressWrapper
import sqlalchemy as sa


def upgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

    # Adjust existing fields to be nullable.
    op.alter_column("accesstoken", "code", nullable=True, existing_type=sa.String(length=255))
    op.alter_column(
        "oauthaccesstoken", "access_token", nullable=True, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "oauthauthorizationcode", "code", nullable=True, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "appspecificauthtoken", "token_code", nullable=True, existing_type=sa.String(length=255)
    )

    # Adjust new fields to be non-nullable.
    op.alter_column(
        "accesstoken", "token_name", nullable=False, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "accesstoken", "token_code", nullable=False, existing_type=sa.String(length=255)
    )

    op.alter_column(
        "appspecificauthtoken", "token_name", nullable=False, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "appspecificauthtoken", "token_secret", nullable=False, existing_type=sa.String(length=255)
    )

    op.alter_column(
        "oauthaccesstoken", "token_name", nullable=False, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "oauthaccesstoken", "token_code", nullable=False, existing_type=sa.String(length=255)
    )

    op.alter_column(
        "oauthauthorizationcode", "code_name", nullable=False, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "oauthauthorizationcode",
        "code_credential",
        nullable=False,
        existing_type=sa.String(length=255),
    )


def downgrade(tables, tester, progress_reporter):
    op = ProgressWrapper(original_op, progress_reporter)

    op.alter_column("accesstoken", "token_name", nullable=True, existing_type=sa.String(length=255))
    op.alter_column("accesstoken", "token_code", nullable=True, existing_type=sa.String(length=255))

    op.alter_column(
        "appspecificauthtoken", "token_name", nullable=True, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "appspecificauthtoken", "token_secret", nullable=True, existing_type=sa.String(length=255)
    )

    op.alter_column(
        "oauthaccesstoken", "token_name", nullable=True, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "oauthaccesstoken", "token_code", nullable=True, existing_type=sa.String(length=255)
    )

    op.alter_column(
        "oauthauthorizationcode", "code_name", nullable=True, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "oauthauthorizationcode",
        "code_credential",
        nullable=True,
        existing_type=sa.String(length=255),
    )
