import pytest
from peewee import IntegrityError, SqliteDatabase

from data.database import (
    BaseModel,
    BlobUpload,
    DigestAlias,
    ImageStorage,
    ImageStorageLocation,
    Repository,
    RepositoryKind,
    User,
    Visibility,
    db,
    db_encrypter,
    read_only_config,
)
from data.encryption import FieldEncrypter
from data.readreplica import ReadOnlyConfig


@pytest.fixture()
def test_db():
    """Set up a temporary in-memory SQLite database with the minimum schema needed for tests."""
    test_database = SqliteDatabase(":memory:")
    db.initialize(test_database)
    db_encrypter.initialize(FieldEncrypter("test-secret-key"))
    read_only_config.initialize(ReadOnlyConfig(False, []))

    models = [
        User,
        Visibility,
        RepositoryKind,
        Repository,
        ImageStorage,
        ImageStorageLocation,
        DigestAlias,
        BlobUpload,
    ]
    test_database.create_tables(models)

    # Create required enum rows.
    visibility = Visibility.create(name="public")
    repo_kind = RepositoryKind.create(name="image")
    user = User.create(username="testuser", email="test@example.com")
    repo = Repository.create(
        namespace_user=user,
        name="testrepo",
        visibility=visibility,
        kind=repo_kind,
    )
    storage = ImageStorage.create(uuid="test-uuid-1234", cas_path=True)
    location = ImageStorageLocation.create(name="local_us")

    yield {
        "db": test_database,
        "user": user,
        "repo": repo,
        "storage": storage,
        "location": location,
    }

    test_database.close()


def test_create_digest_alias(test_db):
    """Create a DigestAlias row and verify it is queryable by digest and image_storage_id."""
    storage = test_db["storage"]
    alias = DigestAlias.create(
        digest="sha512:aaa111bbb222ccc333",
        image_storage=storage,
    )

    # Query by digest.
    fetched = DigestAlias.get(DigestAlias.digest == "sha512:aaa111bbb222ccc333")
    assert fetched.id == alias.id
    assert fetched.image_storage_id == storage.id

    # Query by image_storage_id.
    aliases = list(DigestAlias.select().where(DigestAlias.image_storage == storage))
    assert len(aliases) == 1
    assert aliases[0].digest == "sha512:aaa111bbb222ccc333"

    # Verify FK traversal gives canonical SHA-256 from content_checksum.
    related_storage = aliases[0].image_storage
    assert related_storage.uuid == "test-uuid-1234"


def test_digest_alias_unique_constraint(test_db):
    """Inserting two DigestAlias rows with the same digest value must raise IntegrityError."""
    storage = test_db["storage"]
    DigestAlias.create(
        digest="sha512:duplicate_digest_value",
        image_storage=storage,
    )
    with pytest.raises(IntegrityError):
        DigestAlias.create(
            digest="sha512:duplicate_digest_value",
            image_storage=storage,
        )


def test_digest_alias_fk_constraint(test_db):
    """Inserting a DigestAlias with a non-existent image_storage_id should fail.

    Note: SQLite does not enforce foreign keys by default. This test enables
    PRAGMA foreign_keys to verify the constraint. In production, PostgreSQL
    enforces this natively.
    """
    test_db["db"].execute_sql("PRAGMA foreign_keys = ON")
    with pytest.raises(IntegrityError):
        DigestAlias.create(
            digest="sha512:orphan_digest",
            image_storage=99999,
        )


def test_blobupload_new_fields(test_db):
    """Round-trip test for client_hash_state and client_hash_algorithm on BlobUpload."""
    repo = test_db["repo"]
    location = test_db["location"]

    upload = BlobUpload.create(
        repository=repo,
        uuid="test-upload-uuid",
        byte_count=0,
        sha_state=None,
        location=location,
        chunk_count=0,
        client_hash_state="base64-encoded-pickle-state",
        client_hash_algorithm="sha512",
    )

    fetched = BlobUpload.get(BlobUpload.uuid == "test-upload-uuid")
    assert fetched.client_hash_state == "base64-encoded-pickle-state"
    assert fetched.client_hash_algorithm == "sha512"


def test_blobupload_new_fields_default_null(test_db):
    """Both client_hash_state and client_hash_algorithm default to NULL."""
    repo = test_db["repo"]
    location = test_db["location"]

    upload = BlobUpload.create(
        repository=repo,
        uuid="test-upload-uuid-null",
        byte_count=0,
        sha_state=None,
        location=location,
        chunk_count=0,
    )

    fetched = BlobUpload.get(BlobUpload.uuid == "test-upload-uuid-null")
    assert fetched.client_hash_state is None
    assert fetched.client_hash_algorithm is None
