"""increase upstreamregistry's password length (PROJQUAY-7430)

Revision ID: a32e17bfad20
Revises: 3f8d7acdf7f9
Create Date: 2024-07-13 20:47:26.649828

"""

# revision identifiers, used by Alembic.
revision = "a32e17bfad20"
down_revision = "3f8d7acdf7f9"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.add_column(
            sa.Column("external_registry_password_new", sa.String(length=9000), nullable=True)
        )

    # Copyy data from the old column to the new column
    op.execute(
        """
        UPDATE repomirrorconfig
        SET external_registry_password_new = external_registry_password
    """
    )

    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.drop_column("external_registry_password")
        batch_op.alter_column(
            "external_registry_password_new",
            new_column_name="external_registry_password",
            existing_type=sa.String(length=4096),
        )
    # ### end Alembic commands ###


def downgrade(op, tables, tester):
    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.add_column(
            sa.Column("external_registry_password_old", sa.String(length=4096), nullable=True)
        )

    # Copy data from the new column to the old column
    op.execute(
        """
        UPDATE repomirrorconfig
        SET external_registry_password_old = external_registry_password
    """
    )

    with op.batch_alter_table("repomirrorconfig") as batch_op:
        batch_op.drop_column("external_registry_password")
        batch_op.alter_column(
            "external_registry_password_old",
            new_column_name="external_registry_password",
            existing_type=sa.String(length=9000),
        )
