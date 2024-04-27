"""test npm table

Revision ID: 16c8b6f647c1
Revises: 
Create Date: 2024-03-11 10:14:39.986398

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '16c8b6f647c1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "npmtoken",
        sa.Column("id", sa.Integer, nullable=False),
        sa.Column("token_key", sa.String, nullable=False),
        sa.Column("token_name", sa.String, nullable=False),
        sa.Column("read_only", sa.Boolean),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("cidr_whitelist", sa.ARRAY(sa.String)),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("user.id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_npmtoken")),
    )


def downgrade():
    op.drop_table("npm_token")
