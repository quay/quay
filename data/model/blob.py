import logging

from datetime import datetime, timedelta
from uuid import uuid4

from data.model import (
    tag,
    _basequery,
    BlobDoesNotExist,
    InvalidBlobUpload,
    db_transaction,
    storage as storage_model,
    InvalidImageException,
)
from data.database import (
    Repository,
    RepositoryState,
    Namespace,
    ImageStorage,
    Image,
    ImageStoragePlacement,
    BlobUpload,
    UploadedBlob,
    ImageStorageLocation,
    db_random_func,
)


logger = logging.getLogger(__name__)


def store_blob_record_and_temp_link(
    namespace,
    repo_name,
    blob_digest,
    location_obj,
    byte_count,
    link_expiration_s,
    uncompressed_byte_count=None,
):
    repo = _basequery.get_existing_repository(namespace, repo_name)
    assert repo

    return store_blob_record_and_temp_link_in_repo(
        repo.id, blob_digest, location_obj, byte_count, link_expiration_s, uncompressed_byte_count
    )


def store_blob_record_and_temp_link_in_repo(
    repository_id,
    blob_digest,
    location_obj,
    byte_count,
    link_expiration_s,
    uncompressed_byte_count=None,
):
    """
    Store a record of the blob and temporarily link it to the specified repository.
    """
    assert blob_digest
    assert byte_count is not None

    with db_transaction():
        try:
            storage = ImageStorage.get(content_checksum=blob_digest)
            save_changes = False

            if storage.image_size is None:
                storage.image_size = byte_count
                save_changes = True

            if storage.uncompressed_size is None and uncompressed_byte_count is not None:
                storage.uncompressed_size = uncompressed_byte_count
                save_changes = True

            if save_changes:
                storage.save()

            ImageStoragePlacement.get(storage=storage, location=location_obj)
        except ImageStorage.DoesNotExist:
            storage = ImageStorage.create(
                content_checksum=blob_digest,
                image_size=byte_count,
                uncompressed_size=uncompressed_byte_count,
            )
            ImageStoragePlacement.create(storage=storage, location=location_obj)
        except ImageStoragePlacement.DoesNotExist:
            ImageStoragePlacement.create(storage=storage, location=location_obj)

        _temp_link_blob(repository_id, storage, link_expiration_s)
        return storage


def temp_link_blob(repository_id, blob_digest, link_expiration_s):
    """
    Temporarily links to the blob record from the given repository.

    If the blob record is not found, return None.
    """
    assert blob_digest

    with db_transaction():
        try:
            storage = ImageStorage.get(content_checksum=blob_digest)
        except ImageStorage.DoesNotExist:
            return None

        _temp_link_blob(repository_id, storage, link_expiration_s)
        return storage


def _temp_link_blob(repository_id, storage, link_expiration_s):
    """ Note: Should *always* be called by a parent under a transaction. """
    try:
        repository = Repository.get(id=repository_id)
    except Repository.DoesNotExist:
        return None

    if repository.state == RepositoryState.MARKED_FOR_DELETION:
        return None

    return UploadedBlob.create(
        repository=repository_id,
        blob=storage,
        expires_at=datetime.utcnow() + timedelta(seconds=link_expiration_s),
    )


def lookup_expired_uploaded_blobs(repository):
    """ Looks up all expired uploaded blobs in a repository. """
    return UploadedBlob.select().where(
        UploadedBlob.repository == repository, UploadedBlob.expires_at <= datetime.utcnow()
    )


def get_stale_blob_upload(stale_timespan):
    """
    Returns a blob upload which was created before the stale timespan.
    """
    stale_threshold = datetime.now() - stale_timespan

    try:
        candidates = (
            BlobUpload.select(BlobUpload, ImageStorageLocation)
            .join(ImageStorageLocation)
            .where(BlobUpload.created <= stale_threshold)
        )

        return candidates.get()
    except BlobUpload.DoesNotExist:
        return None


def get_blob_upload_by_uuid(upload_uuid):
    """
    Loads the upload with the given UUID, if any.
    """
    try:
        return (
            BlobUpload.select(BlobUpload, ImageStorageLocation)
            .join(ImageStorageLocation)
            .where(BlobUpload.uuid == upload_uuid)
            .get()
        )
    except BlobUpload.DoesNotExist:
        return None


def get_blob_upload(namespace, repo_name, upload_uuid):
    """
    Load the upload which is already in progress.
    """
    try:
        return (
            BlobUpload.select(BlobUpload, ImageStorageLocation)
            .join(ImageStorageLocation)
            .switch(BlobUpload)
            .join(Repository)
            .join(Namespace, on=(Namespace.id == Repository.namespace_user))
            .where(
                Repository.name == repo_name,
                Namespace.username == namespace,
                BlobUpload.uuid == upload_uuid,
            )
            .get()
        )
    except BlobUpload.DoesNotExist:
        raise InvalidBlobUpload()


def initiate_upload(namespace, repo_name, uuid, location_name, storage_metadata):
    """
    Initiates a blob upload for the repository with the given namespace and name, in a specific
    location.
    """
    repo = _basequery.get_existing_repository(namespace, repo_name)
    return initiate_upload_for_repo(repo, uuid, location_name, storage_metadata)


def initiate_upload_for_repo(repo, uuid, location_name, storage_metadata):
    """
    Initiates a blob upload for a specific repository object, in a specific location.
    """
    location = storage_model.get_image_location_for_name(location_name)
    return BlobUpload.create(
        repository=repo, location=location.id, uuid=uuid, storage_metadata=storage_metadata
    )


def get_shared_blob(digest):
    """
    Returns the ImageStorage blob with the given digest or, if not present, returns None.

    This method is *only* to be used for shared blobs that are globally accessible, such as the
    special empty gzipped tar layer that Docker no longer pushes to us.
    """
    assert digest
    try:
        return ImageStorage.get(content_checksum=digest)
    except ImageStorage.DoesNotExist:
        return None


def get_or_create_shared_blob(digest, byte_data, storage):
    """
    Returns the ImageStorage blob with the given digest or, if not present, adds a row and writes
    the given byte data to the storage engine.

    This method is *only* to be used for shared blobs that are globally accessible, such as the
    special empty gzipped tar layer that Docker no longer pushes to us.
    """
    assert digest
    assert byte_data is not None and isinstance(byte_data, bytes)
    assert storage

    try:
        return ImageStorage.get(content_checksum=digest)
    except ImageStorage.DoesNotExist:
        preferred = storage.preferred_locations[0]
        location_obj = ImageStorageLocation.get(name=preferred)

        record = ImageStorage.create(image_size=len(byte_data), content_checksum=digest)

        try:
            storage.put_content([preferred], storage_model.get_layer_path(record), byte_data)
            ImageStoragePlacement.create(storage=record, location=location_obj)
        except:
            logger.exception("Exception when trying to write special layer %s", digest)
            record.delete_instance()
            raise

        return record
