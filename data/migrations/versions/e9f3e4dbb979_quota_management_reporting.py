"""quota_management_reporting

Revision ID: e9f3e4dbb979
Revises: 909d725887d3
Create Date: 2021-12-16 15:14:43.054705

"""

# revision identifiers, used by Alembic.
revision = 'e9f3e4dbb979'
down_revision = '909d725887d3'

import sqlalchemy as sa


def upgrade(op, tables, tester):

    op.create_table(
        "quotalimitgroups",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("group_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotalimitgroups"))
    )

    op.create_table(
        "userorganizationquota",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("organization", sa.Integer, nullable=False),
        sa.Column("limit_bytes", sa.Integer, nullable=False),
        sa.Column("quota_limit_group", sa.Integer, nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_userorganizationquota")),
        sa.ForeignKeyConstraint(
            ["quota_limit_group"], ["quotalimitgroups.id"], name=op.f("fk_userorganizationquota_limit_group")
        ),
        sa.ForeignKeyConstraint(
            ["organization"], ["user.id"], name=op.f("fk_userorganizationquota_organization")
        )
    )

    op.create_index(
        "userorganizationquota_organization", "userorganizationquota", ["organization"], unique=True
    )
    op.create_index(
        "userorganizationquota_limitgroup", "userorganizationquota", ["quota_limit_group"], unique=False
    )

    op.create_table(
        "quotatype",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotatype"))
    )


    op.create_table(
        "quotalimits",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("limit_group_id", sa.Integer, nullable=False),
        sa.Column("type", sa.Integer, nullable=False),
        sa.Column("percent_of_limit", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["type"], ["quotatype.id"], name=op.f("fk_quotalimit_type")),
        sa.ForeignKeyConstraint(["limit_group_id"], ["quotalimitgroups.id"], name=op.f("fk_quotalimit_limit_group"))
    )

    op.create_index(
        "quotalimits_limitgroupid", "quotalimits", ["limit_group_id"], unique=False
    )

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




def downgrade(op, tables, tester):
    pass
