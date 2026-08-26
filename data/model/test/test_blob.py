import hashlib
import random
from uuid import uuid4

from data.database import ImageStorage, ImageStorageLocation, ImageStoragePlacement
from data.model import repository
from data.model.blob import (
    get_blob_upload_by_uuid,
    initiate_upload,
    store_blob_record_and_temp_link_in_repo,
)
from digest.digest_tools import sha256_digest
from test.fixtures import *


def _get_digest(content_bytes):
    """
    Helper function that creates blobs with proper digests
    """
    return sha256_digest(content_bytes)


def test_blobupload_sha_state(initialized_db: None) -> None:
    bu = initiate_upload("randomuser", "randomrepo", str(uuid4()), "local_us", {})
    bu.sha_state.update(b"hello")
    bu.save()
    bu = get_blob_upload_by_uuid(bu.uuid)
    assert bu is not None
    assert bu.sha_state.hexdigest() == hashlib.sha256(b"hello").hexdigest()


def test_store_blob_record_uses_lock(initialized_db):
    """
    Tests whether store_blob_record_and_temp_link_in_repo uses the locking mechanism properly.
    """
    blob_content = random.randbytes(1024)
    blob_digest = _get_digest(blob_content)

    # create temporary repository
    repo = repository.create_repository("devtable", "test_lock_repo", None)
    assert repo is not None
    location = ImageStorageLocation.get(name="local_us")

    # store blob under the created repository
    result = store_blob_record_and_temp_link_in_repo(
        repository_id=repo.id,
        blob_digest=blob_digest,
        location_obj=location,
        byte_count=len(blob_content),
        link_expiration_s=300,
        uncompressed_byte_count=len(blob_content),
    )

    # verify blob creation
    assert result.content_checksum == blob_digest
    assert ImageStorage.select().where(ImageStorage.content_checksum == blob_digest).exists()
    assert ImageStoragePlacement.select().where(ImageStoragePlacement.storage == result).exists()
