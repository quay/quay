"""add_organization_ai_settings

Revision ID: d068cc908da9
Revises: 9307c3d604b4
Create Date: 2024-12-16 12:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "d068cc908da9"
down_revision = "9307c3d604b4"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    # Create OrganizationAISettings table for storing AI feature configuration per organization
    op.create_table(
        "organizationaisettings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        # Feature toggles
        sa.Column(
            "description_generator_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        # Provider configuration (BYOK mode)
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("endpoint", sa.String(length=512), nullable=True),
        # Verification status
        sa.Column(
            "credentials_verified",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("credentials_verified_at", sa.DateTime(), nullable=True),
        # Metadata
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["user.id"],
            name=op.f("fk_organizationaisettings_organization_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizationaisettings")),
    )

    # Create unique index on organization_id
    op.create_index(
        "organizationaisettings_organization_id",
        "organizationaisettings",
        ["organization_id"],
        unique=True,
    )

    # Add log entry kinds for AI actions
    op.bulk_insert(
        tables.logentrykind,
        [
            {"name": "update_ai_settings"},
            {"name": "set_ai_credentials"},
            {"name": "delete_ai_credentials"},
            {"name": "generate_ai_description"},
        ],
    )


def downgrade(op, tables, tester):
    # Remove log entry kinds
    op.execute(
        tables.logentrykind.delete().where(
            tables.logentrykind.c.name.in_(
                [
                    "update_ai_settings",
                    "set_ai_credentials",
                    "delete_ai_credentials",
                    "generate_ai_description",
                ]
            )
        )
    )

    # Drop index
    op.drop_index(
        "organizationaisettings_organization_id",
        table_name="organizationaisettings",
    )

    # Drop table
    op.drop_table("organizationaisettings")
