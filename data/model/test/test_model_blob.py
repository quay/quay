from app import storage
from data import model, database

from test.fixtures import *

ADMIN_ACCESS_USER = "devtable"
REPO = "simple"


def test_store_blob(initialized_db):
    location = database.ImageStorageLocation.select().get()

    # Create a new blob at a unique digest.
    digest = "somecooldigest"
    blob_storage = model.blob.store_blob_record_and_temp_link(
        ADMIN_ACCESS_USER, REPO, digest, location, 1024, 0, 5000
    )
    assert blob_storage.content_checksum == digest
    assert blob_storage.image_size == 1024
    assert blob_storage.uncompressed_size == 5000

    # Link to the same digest.
    blob_storage2 = model.blob.store_blob_record_and_temp_link(
        ADMIN_ACCESS_USER, REPO, digest, location, 2048, 0, 6000
    )
    assert blob_storage2.id == blob_storage.id

    # The sizes should be unchanged.
    assert blob_storage2.image_size == 1024
    assert blob_storage2.uncompressed_size == 5000

    # Add a new digest, ensure it has a new record.
    otherdigest = "anotherdigest"
    blob_storage3 = model.blob.store_blob_record_and_temp_link(
        ADMIN_ACCESS_USER, REPO, otherdigest, location, 1234, 0, 5678
    )
    assert blob_storage3.id != blob_storage.id
    assert blob_storage3.image_size == 1234
    assert blob_storage3.uncompressed_size == 5678


def test_get_or_create_shared_blob(initialized_db):
    shared = model.blob.get_or_create_shared_blob("sha256:abcdef", b"somecontent", storage)
    assert shared.content_checksum == "sha256:abcdef"

    again = model.blob.get_or_create_shared_blob("sha256:abcdef", b"somecontent", storage)
    assert shared == again


def test_lookup_repo_storages_by_content_checksum(initialized_db):
    for image in database.Image.select():
        found = model.storage.lookup_repo_storages_by_content_checksum(
            image.repository, [image.storage.content_checksum]
        )
        assert len(found) == 1
        assert found[0].content_checksum == image.storage.content_checksum
