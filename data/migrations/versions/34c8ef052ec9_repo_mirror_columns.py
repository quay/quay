"""
repo mirror columns.

Revision ID: 34c8ef052ec9
Revises: c059b952ed76
Create Date: 2019-10-07 13:11:20.424715
"""

# revision identifiers, used by Alembic.
revision = "34c8ef052ec9"
down_revision = "cc6778199cdb"

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from peewee import ForeignKeyField, DateTimeField, BooleanField
from data.database import (
    BaseModel,
    RepoMirrorType,
    RepoMirrorStatus,
    RepoMirrorRule,
    uuid_generator,
    QuayUserField,
    Repository,
    IntegerField,
    JSONField,
)
from data.fields import EnumField as ClientEnumField, CharField, EncryptedCharField, DecryptedValue
from data.encryption import FieldEncrypter, DecryptionFailureException

import logging

logger = logging.getLogger(__name__)

BATCH_SIZE = 10


# Original model
class RepoMirrorConfig(BaseModel):
    """
    Represents a repository to be mirrored and any additional configuration required to perform the
    mirroring.
    """

    repository = ForeignKeyField(Repository, index=True, unique=True, backref="mirror")
    creation_date = DateTimeField(default=datetime.utcnow)
    is_enabled = BooleanField(default=True)

    # Mirror Configuration
    mirror_type = ClientEnumField(RepoMirrorType, default=RepoMirrorType.PULL)
    internal_robot = QuayUserField(
        allows_robots=True, null=True, backref="mirrorpullrobot", robot_null_delete=True
    )
    external_reference = CharField()
    external_registry = CharField()
    external_namespace = CharField()
    external_repository = CharField()
    external_registry_username = EncryptedCharField(max_length=2048, null=True)
    external_registry_password = EncryptedCharField(max_length=2048, null=True)
    external_registry_config = JSONField(default={})

    # Worker Queuing
    sync_interval = IntegerField()  # seconds between syncs
    sync_start_date = DateTimeField(null=True)  # next start time
    sync_expiration_date = DateTimeField(null=True)  # max duration
    sync_retries_remaining = IntegerField(default=3)
    sync_status = ClientEnumField(RepoMirrorStatus, default=RepoMirrorStatus.NEVER_RUN)
    sync_transaction_id = CharField(default=uuid_generator, max_length=36)

    # Tag-Matching Rules
    root_rule = ForeignKeyField(RepoMirrorRule)


def _iterate(model_class, clause):
    while True:
        has_rows = False
        for row in list(model_class.select().where(clause).limit(BATCH_SIZE)):
            has_rows = True
            yield row

        if not has_rows:
            break


def upgrade(op, tables, tester):
    from app import app

    logger.info("Migrating to external_reference from existing columns")
    op.add_column("repomirrorconfig", sa.Column("external_reference", sa.Text(), nullable=True))

    logger.info("Reencrypting existing columns")
    if app.config.get("SETUP_COMPLETE", False) and not tester.is_testing():
        old_key_encrypter = FieldEncrypter(app.config.get("SECRET_KEY"))

        starting_id = 0
        has_additional = True
        while has_additional:
            has_additional = False

            query = RepoMirrorConfig.select().where(RepoMirrorConfig.id >= starting_id).limit(10)
            for row in query:
                starting_id = max(starting_id, row.id + 1)
                has_additional = True
                logger.debug("Re-encrypting information for row %s", row.id)

                has_changes = False
                try:
                    if row.external_registry_username:
                        row.external_registry_username.decrypt()
                except DecryptionFailureException:
                    # Encrypted using the older SECRET_KEY. Migrate it.
                    decrypted = row.external_registry_username.decrypt(old_key_encrypter)
                    row.external_registry_username = DecryptedValue(decrypted)
                    has_changes = True

                try:
                    if row.external_registry_password:
                        row.external_registry_password.decrypt()
                except DecryptionFailureException:
                    # Encrypted using the older SECRET_KEY. Migrate it.
                    decrypted = row.external_registry_password.decrypt(old_key_encrypter)
                    row.external_registry_password = DecryptedValue(decrypted)
                    has_changes = True

                if has_changes:
                    logger.debug("Saving re-encrypted information for row %s", row.id)
                    row.save()

    if app.config.get("SETUP_COMPLETE", False) or tester.is_testing():
        for repo_mirror in _iterate(
            RepoMirrorConfig, (RepoMirrorConfig.external_reference >> None)
        ):
            repo = "%s/%s/%s" % (
                repo_mirror.external_registry,
                repo_mirror.external_namespace,
                repo_mirror.external_repository,
            )
            logger.info("migrating %s" % repo)
            repo_mirror.external_reference = repo
            repo_mirror.save()

    op.drop_column("repomirrorconfig", "external_registry")
    op.drop_column("repomirrorconfig", "external_namespace")
    op.drop_column("repomirrorconfig", "external_repository")

    op.alter_column(
        "repomirrorconfig", "external_reference", nullable=False, existing_type=sa.Text()
    )

    tester.populate_column("repomirrorconfig", "external_reference", tester.TestDataType.String)


def downgrade(op, tables, tester):

    """
  This will downgrade existing data but may not exactly match previous data structure. If the
  external_reference does not have three parts (registry, namespace, repository) then a failed
  value is inserted.
  """

    op.add_column(
        "repomirrorconfig", sa.Column("external_registry", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "repomirrorconfig", sa.Column("external_namespace", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "repomirrorconfig", sa.Column("external_repository", sa.String(length=255), nullable=True)
    )

    from app import app

    if app.config.get("SETUP_COMPLETE", False):
        logger.info("Restoring columns from external_reference")
        for repo_mirror in _iterate(RepoMirrorConfig, (RepoMirrorConfig.external_registry >> None)):
            logger.info("Restoring %s" % repo_mirror.external_reference)
            parts = repo_mirror.external_reference.split("/", 2)
            repo_mirror.external_registry = parts[0] if len(parts) >= 1 else "DOWNGRADE-FAILED"
            repo_mirror.external_namespace = parts[1] if len(parts) >= 2 else "DOWNGRADE-FAILED"
            repo_mirror.external_repository = parts[2] if len(parts) >= 3 else "DOWNGRADE-FAILED"
            repo_mirror.save()

    op.drop_column("repomirrorconfig", "external_reference")

    op.alter_column(
        "repomirrorconfig", "external_registry", nullable=False, existing_type=sa.String(length=255)
    )
    op.alter_column(
        "repomirrorconfig",
        "external_namespace",
        nullable=False,
        existing_type=sa.String(length=255),
    )
    op.alter_column(
        "repomirrorconfig",
        "external_repository",
        nullable=False,
        existing_type=sa.String(length=255),
    )
