"""add organization contact email

Revision ID: 414c5e2fc487
Revises: 285f36ce97fd
Create Date: 2026-02-25 00:00:00.000000

"""

# revision identifiers, used by Alembic.
revision = "414c5e2fc487"
down_revision = "285f36ce97fd"

import sqlalchemy as sa


def upgrade(op, tables, tester):
    op.create_table(
        "organizationcontactemail",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["user.id"],
            name=op.f("fk_organizationcontactemail_organization_id_user"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizationcontactemail")),
    )

    op.create_index(
        "organizationcontactemail_organization_id",
        "organizationcontactemail",
        ["organization_id"],
        unique=True,
    )

    op.create_index(
        "organizationcontactemail_contact_email",
        "organizationcontactemail",
        ["contact_email"],
        unique=False,
    )

    # Data migration: copy existing org emails to new table
    conn = op.get_bind()
    orgs_with_real_email = conn.execute(
        sa.text("""
            SELECT id, email FROM "user"
            WHERE organization = true
              AND email NOT LIKE '%placeholder.invalid'
              AND email IS NOT NULL
              AND length(email) < 64
        """)
    )
    for org_id, email in orgs_with_real_email:
        conn.execute(
            sa.text("""
                INSERT INTO organizationcontactemail (organization_id, contact_email)
                VALUES (:org_id, :email)
                ON CONFLICT (organization_id) DO NOTHING
            """),
            {"org_id": org_id, "email": email},
        )

    tester.populate_table(
        "organizationcontactemail",
        [
            ("organization_id", tester.TestDataType.Foreign("user")),
            ("contact_email", tester.TestDataType.String),
        ],
    )


def downgrade(op, tables, tester):
    op.drop_table("organizationcontactemail")
