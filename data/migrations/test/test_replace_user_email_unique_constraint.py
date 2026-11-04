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

import logging
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


def test_upgrade_skips_organizations_that_share_a_contact_email():
    """
    Two organizations with placeholder emails and the same stored contact email, which no row
    holds today, would both be given that address by one UPDATE and the second write would
    violate user_email. No member of such a group is restored. An organization with a contact
    email of its own is still restored.
    """
    placeholder_1 = str(uuid.uuid4())
    placeholder_2 = str(uuid.uuid4())
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, "acme", placeholder_1, True)
        _add_user(connection, 2, "globex", placeholder_2, True)
        _add_user(connection, 3, "initech", str(uuid.uuid4()), True)
        _add_contact_email(connection, 1, "dup@example.com")
        _add_contact_email(connection, 2, "dup@example.com")
        _add_contact_email(connection, 3, "initech@example.com")

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 1) == placeholder_1
        assert _email_of(connection, 2) == placeholder_2
        assert _email_of(connection, 3) == "initech@example.com"


def test_upgrade_logs_the_organizations_it_skips(caplog):
    """
    Each filter's skipped organizations are logged by id, so an administrator can see why Step 0
    restored some organizations and not others. Email addresses are never logged.
    """
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        # 1: contact email held by a live account.
        _add_user(connection, 1, "acme", str(uuid.uuid4()), True)
        _add_contact_email(connection, 1, "held@example.com")
        _add_user(connection, 2, "alice", "held@example.com", False)
        # 3 and 4: the same contact email, held by nobody.
        _add_user(connection, 3, "globex", str(uuid.uuid4()), True)
        _add_user(connection, 4, "hooli", str(uuid.uuid4()), True)
        _add_contact_email(connection, 3, "dup@example.com")
        _add_contact_email(connection, 4, "dup@example.com")
        # 5: deleted organization with a free contact email.
        _add_user(connection, 5, str(uuid.uuid4()), str(uuid.uuid4()), True)
        _add_contact_email(connection, 5, "gone@example.com")
        _mark_deleted(connection, 5, "oldorg", "gone@example.com")
        # 6: restored, so it must not be reported.
        _add_user(connection, 6, "initech", str(uuid.uuid4()), True)
        _add_contact_email(connection, 6, "initech@example.com")

        with caplog.at_level(logging.WARNING, logger=migration.__name__):
            migration.upgrade(_operations(connection), None, NoopTester())

    messages = [r.getMessage() for r in caplog.records if r.name == migration.__name__]
    assert len(messages) == 3
    by_reason = {}
    for reason in ("already used", "share a contact email", "marked for deletion"):
        matching = [m for m in messages if reason in m]
        assert len(matching) == 1, (reason, messages)
        by_reason[reason] = matching[0]
    assert "1 organization" in by_reason["already used"] and "[1]" in by_reason["already used"]
    assert "2 organization" in by_reason["share a contact email"]
    assert "[3, 4]" in by_reason["share a contact email"]
    assert "1 organization" in by_reason["marked for deletion"]
    assert "[5]" in by_reason["marked for deletion"]
    assert "@" not in " ".join(messages)


def test_upgrade_logs_nothing_when_no_organization_is_skipped(caplog):
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        _add_user(connection, 1, "acme", str(uuid.uuid4()), True)
        _add_contact_email(connection, 1, "billing@example.com")

        with caplog.at_level(logging.WARNING, logger=migration.__name__):
            migration.upgrade(_operations(connection), None, NoopTester())

        assert _email_of(connection, 1) == "billing@example.com"

    assert [r for r in caplog.records if r.name == migration.__name__] == []


def test_upgrade_rerun_after_step_three_failed():
    """
    Installation state 7: an earlier attempt committed Step 0 and both new indexes, then failed
    at Step 3, so user_email_unique_non_org and user_email_idx exist next to user_email. The
    rerun must skip Steps 1 and 2, drop user_email, and leave the restored emails alone.
    """
    engine = sa.create_engine("sqlite://")
    with engine.begin() as connection:
        _create_pre_migration_schema(connection)
        connection.execute(
            sa.text(
                "CREATE UNIQUE INDEX user_email_unique_non_org "
                'ON "user"(email) WHERE organization = false'
            )
        )
        connection.execute(sa.text('CREATE INDEX user_email_idx ON "user"(email)'))
        # Restored by the first attempt, still restored on the rerun.
        _add_user(connection, 1, "acme", "billing@example.com", True)
        _add_contact_email(connection, 1, "billing@example.com")
        # Still a placeholder: restoring it would be allowed, and happens on the rerun.
        _add_user(connection, 2, "globex", str(uuid.uuid4()), True)
        _add_contact_email(connection, 2, "globex@example.com")
        assert "user_email" in _index_names(connection)

        migration.upgrade(_operations(connection), None, NoopTester())

        _assert_index_swap_done(connection)
        assert _email_of(connection, 1) == "billing@example.com"
        assert _email_of(connection, 2) == "globex@example.com"

        # A second rerun on the finished schema changes nothing.
        migration.upgrade(_operations(connection), None, NoopTester())
        _assert_index_swap_done(connection)
