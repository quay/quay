"""
Tests for migration b1a79fa8e630 (replace the user email unique constraint with a partial index).

Step 0 of the migration copies organizationcontactemail.contact_email back into user.email for
organizations whose email is a placeholder (no "@"). It runs while the old full unique index
user_email still exists, so it must not write an address that another user row already holds
(PROJQUAY-14084), and it must not give a deleted organization its address back.

The pre-migration schema is the 3.17 shape: a full unique index user_email on user.email, the
organizationcontactemail table filled by migration 414c5e2fc487, and the deletednamespace table
that mark_namespace_for_deletion() writes when an organization is deleted.
"""

import uuid

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from data.migrations.tester import NoopTester
from data.migrations.versions import (
    b1a79fa8e630_replace_user_email_unique_constraint_ as migration,
)


def _operations(connection):
    context = MigrationContext.configure(
        connection, opts={"render_as_batch": True, "transactional_ddl": False}
    )
    return Operations(context)


def _index_names(connection):
    return {index["name"] for index in sa.inspect(connection).get_indexes("user")}


def _create_pre_migration_schema(connection):
    metadata = sa.MetaData()
    sa.Table(
        "user",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("organization", sa.Boolean(), nullable=False, default=False),
        sa.Index("user_email", "email", unique=True),
    )
    sa.Table(
        "organizationcontactemail",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Index("organizationcontactemail_organization_id", "organization_id", unique=True),
    )
    sa.Table(
        "deletednamespace",
        metadata,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("namespace_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("original_username", sa.String(length=255), nullable=False),
        sa.Column("original_email", sa.String(length=255), nullable=False),
        sa.Index("deletednamespace_namespace_id", "namespace_id", unique=True),
    )
    metadata.create_all(connection)


def _add_user(connection, user_id, username, email, organization):
    connection.execute(
        sa.text(
            'INSERT INTO "user"(id, username, email, organization) '
            "VALUES (:id, :username, :email, :organization)"
        ),
        {"id": user_id, "username": username, "email": email, "organization": organization},
    )


def _add_contact_email(connection, organization_id, contact_email):
    connection.execute(
        sa.text(
            "INSERT INTO organizationcontactemail(organization_id, contact_email) "
            "VALUES (:organization_id, :contact_email)"
        ),
        {"organization_id": organization_id, "contact_email": contact_email},
    )


def _mark_deleted(connection, organization_id, original_username, original_email):
    """What mark_namespace_for_deletion() leaves behind: a deletednamespace row."""
    connection.execute(
        sa.text(
            "INSERT INTO deletednamespace(namespace_id, original_username, original_email) "
            "VALUES (:namespace_id, :original_username, :original_email)"
        ),
        {
            "namespace_id": organization_id,
            "original_username": original_username,
            "original_email": original_email,
        },
    )


def _email_of(connection, user_id):
    return connection.execute(
        sa.text('SELECT email FROM "user" WHERE id = :id'), {"id": user_id}
    ).scalar()


def _assert_index_swap_done(connection):
    indexes = _index_names(connection)
    assert "user_email" not in indexes
    assert "user_email_unique_non_org" in indexes
    assert "user_email_idx" in indexes


def test_upgrade_with_stale_contact_email_already_in_use():
    """
    An organization deleted on 3.17 has a UUID email, and its stored contact email (the address
    it had before it was deleted) now belongs to a live account. The upgrade must not fail on
    user_email, and the live account must keep its address.
    """
    placeholder = str(uuid.uuid4())
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, str(uuid.uuid4()), placeholder, True)
        _add_contact_email(connection, 1, "shared@example.com")
        _mark_deleted(connection, 1, "oldorg", "shared@example.com")
        _add_user(connection, 2, "alice", "shared@example.com", False)

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 2) == "shared@example.com"
        assert _email_of(connection, 1) == placeholder


def test_upgrade_skips_live_organization_whose_contact_email_is_in_use():
    """
    A live organization (no deletednamespace row) whose email is not an address and whose stored
    contact email is held by another account keeps its current email: restoring it would
    duplicate the other account's address. This isolates the "already in use" filter from the
    "deleted organization" filter.
    """
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, "acme", "not-an-address", True)
        _add_contact_email(connection, 1, "shared@example.com")
        _add_user(connection, 2, "alice", "shared@example.com", False)

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 1) == "not-an-address"
        assert _email_of(connection, 2) == "shared@example.com"


def test_upgrade_skips_deleted_organization_whose_contact_email_is_free():
    """
    An organization that was deleted (it has a deletednamespace row) keeps its UUID email even
    when its stored contact email is free: the row is disabled and queued for garbage
    collection, and giving it a real address back would only create a duplicate for whoever
    registers that address later.
    """
    placeholder = str(uuid.uuid4())
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, str(uuid.uuid4()), placeholder, True)
        _add_contact_email(connection, 1, "free@example.com")
        _mark_deleted(connection, 1, "oldorg", "free@example.com")

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 1) == placeholder


def test_upgrade_restores_live_organization_whose_contact_email_is_free():
    """
    A live organization whose email is not an address and whose stored contact email is free is
    restored, as before the fix. This guards Step 0's purpose against over-filtering.
    """
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, "acme", str(uuid.uuid4()), True)
        _add_contact_email(connection, 1, "billing@example.com")
        _add_user(connection, 2, "alice", "alice@example.com", False)

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 1) == "billing@example.com"
        assert _email_of(connection, 2) == "alice@example.com"


def test_upgrade_and_downgrade_without_collision():
    """Guards the index swap in both directions when Step 0 has nothing to do."""
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, "acme", "org@example.com", True)

        migration.upgrade(_operations(connection), None, NoopTester())
        _assert_index_swap_done(connection)

        migration.downgrade(_operations(connection), None, NoopTester())
        indexes = _index_names(connection)
        assert "user_email" in indexes
        assert "user_email_unique_non_org" not in indexes
        assert "user_email_idx" not in indexes
