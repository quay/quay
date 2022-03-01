"""quota_management_reporting

Revision ID: e9f3e4dbb979
Revises: 909d725887d3
Create Date: 2021-12-16 15:14:43.054705

"""

# revision identifiers, used by Alembic.
revision = "e9f3e4dbb979"
down_revision = "909d725887d3"

import sqlalchemy as sa


def upgrade(op, tables, tester):

    op.create_table(
        "userorganizationquota",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("namespace_id", sa.Integer, nullable=False),
        sa.Column("limit_bytes", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_userorganizationquota")),
        sa.ForeignKeyConstraint(
            ["namespace_id"], ["user.id"], name=op.f("fk_userorganizationquota_organization")
        ),
    )

    op.create_index(
        "userorganizationquota_organization",
        "userorganizationquota",
        ["namespace_id"],
        unique=True,
    )

    op.create_table(
        "quotatype",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotatype")),
    )

    op.bulk_insert(tables.quotatype, [{"name": "Warning"}, {"name": "Reject"}])

    op.create_table(
        "quotalimits",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("quota_id", sa.Integer, nullable=False),
        sa.Column("quota_type_id", sa.Integer, nullable=False),
        sa.Column("percent_of_limit", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotalimits")),
        sa.ForeignKeyConstraint(
            ["quota_type_id"], ["quotatype.id"], name=op.f("fk_quotalimit_type")
        ),
        sa.ForeignKeyConstraint(
            ["quota_id"],
            ["userorganizationquota.id"],
            name=op.f("fk_quotalimit_id"),
        ),
    )

    op.create_index("quotalimits_quota_id", "quotalimits", ["quota_id"], unique=False)

    op.create_table(
        "repositorysize",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("repository_id", sa.Integer, nullable=False),
        sa.Column("size_bytes", sa.NUMERIC, nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"],
            ["repository.id"],
            name=op.f("fk_repositorysize_repository_id_repository"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_repositorysizeid")),
    )

    op.create_index(
        "repositorysize_repository_id",
        "repositorysize",
        ["repository_id"],
        unique=True,
    )

    op.bulk_insert(tables.notificationkind, [{"name": "quota_warning"}, {"name": "quota_error"}])


def downgrade(op, tables, tester):
    pass
