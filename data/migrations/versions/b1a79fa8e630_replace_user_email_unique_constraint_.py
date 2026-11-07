"""replace user email unique constraint with partial index

Revision ID: b1a79fa8e630
Revises: c3d4e5f6a7b8
Create Date: 2026-06-23 18:18:57.906927

On large tables (e.g. quay.io), plain CREATE INDEX blocks all writes for the
duration of the index build.  This migration uses CREATE INDEX CONCURRENTLY
(via autocommit_block + postgresql_concurrently) to avoid write-locks, and
creates the new indexes BEFORE dropping the old one so there is never a window
with no email index.

The operations are idempotent: each step checks whether the index already
exists, so the migration is safe to retry if CONCURRENTLY fails partway.

NOTE on downgrade: if organizations have been created with shared emails
after this migration, the downgrade will fail because duplicate email
values cannot satisfy a full unique constraint.  De-duplicate org emails
before downgrading.
"""

# revision identifiers, used by Alembic.
revision = "b1a79fa8e630"
down_revision = "c3d4e5f6a7b8"

import logging

import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

logger = logging.getLogger(__name__)

# Step 0 restores a contact email into an organization row that has a placeholder email. The
# candidate rows, and the three reasons for leaving a candidate alone, are separate fragments so
# that the UPDATE and the warnings that report the skipped rows use the same conditions.
# NOT LIKE '%%@%%' detects UUID placeholders (no @ sign).
_STEP0_CANDIDATE = (
    "organization = true"
    " AND email NOT LIKE '%%@%%'"
    " AND EXISTS ("
    "  SELECT 1 FROM organizationcontactemail oce"
    '  WHERE oce.organization_id = "user".id'
    "  AND oce.contact_email IS NOT NULL"
    ")"
)
_STEP0_SKIP_REASONS = (
    (
        "whose contact email is already used by another user row",
        "EXISTS ("
        '  SELECT 1 FROM organizationcontactemail oce, "user" other'
        '  WHERE oce.organization_id = "user".id'
        "  AND other.email = oce.contact_email"
        '  AND other.id <> "user".id'
        ")",
    ),
    (
        "that share a contact email with another organization",
        "EXISTS ("
        "  SELECT 1 FROM organizationcontactemail oce, organizationcontactemail o2"
        '  WHERE oce.organization_id = "user".id'
        "  AND o2.contact_email = oce.contact_email"
        '  AND o2.organization_id <> "user".id'
        ")",
    ),
    (
        "marked for deletion",
        'EXISTS (SELECT 1 FROM deletednamespace dn WHERE dn.namespace_id = "user".id)',
    ),
)


def _drop_invalid_index(bind, index_name):
    """Drop an index if it exists and is marked invalid (e.g. from a failed CONCURRENTLY)."""
    is_valid = bind.execute(
        sa.text(
            "SELECT i.indisvalid FROM pg_class c "
            "JOIN pg_index i ON i.indexrelid = c.oid "
            "WHERE c.relname = :name"
        ),
        {"name": index_name},
    ).scalar()
    if is_valid is not None and not is_valid:
        bind.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
        return True
    return False


def upgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    user_indexes = {i["name"] for i in inspector.get_indexes("user")}

    # Clean up any invalid indexes left by a previous failed CONCURRENTLY attempt.
    if bind.dialect.name == "postgresql":
        for idx_name in ("user_email_unique_non_org", "user_email_idx"):
            if idx_name in user_indexes and _drop_invalid_index(bind, idx_name):
                user_indexes.discard(idx_name)

    # Step 0: If OrganizationContactEmail table exists and has data, copy contact
    # emails back into User.email for any orgs that still have UUID placeholders.
    # This handles the case where the earlier migration (414c5e2fc487) populated
    # OrganizationContactEmail but User.email was replaced with a UUID.
    #
    # NOTE: This UPDATE runs in the current transaction, which is unconditionally
    # committed when autocommit_block() is entered in Step 1. The lock window
    # is therefore limited to the UPDATE duration only.
    #
    # The UPDATE runs while the old full unique index user_email still exists, so it
    # must not write an address that another user row already holds, or the whole
    # migration fails with a unique violation (PROJQUAY-14084). Three kinds of rows are
    # skipped:
    #   - organizations whose stored contact email is already used by another user row.
    #     The contact email is a snapshot taken by 414c5e2fc487 and never updated, so
    #     the address may have been reused since.
    #   - organizations whose stored contact email is also the stored contact email of
    #     another organization. One UPDATE would give the address to all of them and the
    #     second write would violate user_email. No member of such a group is restored,
    #     because nothing says which organization owns the address.
    #   - organizations marked for deletion (they have a deletednamespace row). Their
    #     email became a UUID when they were deleted and the namespace garbage collector
    #     will remove them; restoring their old address would only duplicate it.
    # Every skipped organization keeps the email it has today. The ids of the skipped
    # organizations are logged as warnings (never the addresses), once per reason, so an
    # organization that matches more than one reason is listed under each.
    tables_list = inspector.get_table_names()
    if "organizationcontactemail" in tables_list:
        for reason, condition in _STEP0_SKIP_REASONS:
            skipped_ids = sorted(
                row[0]
                for row in bind.execute(
                    sa.text(f'SELECT id FROM "user" WHERE {_STEP0_CANDIDATE} AND {condition}')
                )
            )
            if skipped_ids:
                logger.warning(
                    "Not restoring the contact email of %d organization(s) %s: ids %s",
                    len(skipped_ids),
                    reason,
                    skipped_ids,
                )

        # Use correlated subquery syntax (works on both PostgreSQL and SQLite).
        not_skipped = "".join(f" AND NOT {condition}" for _, condition in _STEP0_SKIP_REASONS)
        op.execute(
            sa.text(
                'UPDATE "user" SET email = ('
                "  SELECT oce.contact_email FROM organizationcontactemail oce"
                '  WHERE oce.organization_id = "user".id'
                "  AND oce.contact_email IS NOT NULL"
                f") WHERE {_STEP0_CANDIDATE}{not_skipped}"
            )
        )

    # Step 1: Create the new partial unique index.
    # On PostgreSQL use CONCURRENTLY (no write locks); on SQLite use plain CREATE INDEX.
    # We do this BEFORE dropping the old index so there is never a moment with no
    # uniqueness enforcement for non-org users.
    if "user_email_unique_non_org" not in user_indexes:
        if bind.dialect.name == "postgresql":
            with op.get_context().autocommit_block():
                op.execute(
                    "CREATE UNIQUE INDEX CONCURRENTLY user_email_unique_non_org "
                    'ON "user"(email) WHERE organization = false'
                )
        else:
            op.execute(
                "CREATE UNIQUE INDEX user_email_unique_non_org "
                'ON "user"(email) WHERE organization = false'
            )

    # Step 2: Create a regular (non-unique) index for general email lookups.
    if "user_email_idx" not in user_indexes:
        if bind.dialect.name == "postgresql":
            with op.get_context().autocommit_block():
                op.create_index(
                    "user_email_idx",
                    "user",
                    ["email"],
                    unique=False,
                    postgresql_concurrently=True,
                )
        else:
            op.create_index("user_email_idx", "user", ["email"], unique=False)

    # Step 3: Drop the old full unique index. This is a fast metadata-only
    # operation — no table scan required.
    if "user_email" in user_indexes:
        op.drop_index("user_email", table_name="user")


def downgrade(op, tables, tester):
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    user_indexes = {i["name"] for i in inspector.get_indexes("user")}

    if "user_email_idx" in user_indexes:
        op.drop_index("user_email_idx", table_name="user")

    if "user_email_unique_non_org" in user_indexes:
        op.execute("DROP INDEX user_email_unique_non_org")

    if "user_email" not in user_indexes:
        if bind.dialect.name == "postgresql":
            with op.get_context().autocommit_block():
                op.create_index(
                    "user_email",
                    "user",
                    ["email"],
                    unique=True,
                    postgresql_concurrently=True,
                )
        else:
            op.create_index("user_email", "user", ["email"], unique=True)
