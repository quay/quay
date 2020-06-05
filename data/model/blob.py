import logging

from datetime import datetime
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
    Namespace,
    ImageStorage,
    Image,
    ImageStoragePlacement,
    BlobUpload,
    ImageStorageLocation,
    db_random_func,
)


logger = logging.getLogger(__name__)


def get_repository_blob_by_digest(repository, blob_digest):
    """
    Find the content-addressable blob linked to the specified repository.
    """
    assert blob_digest
    try:
        storage = (
            ImageStorage.select(ImageStorage.uuid)
            .join(Image)
            .where(
                Image.repository == repository,
                ImageStorage.content_checksum == blob_digest,
                ImageStorage.uploading == False,
            )
            .get()
        )

        return storage_model.get_storage_by_uuid(storage.uuid)
    except (ImageStorage.DoesNotExist, InvalidImageException):
        raise BlobDoesNotExist("Blob does not exist with digest: {0}".format(blob_digest))


def get_repo_blob_by_digest(namespace, repo_name, blob_digest):
    """
    Find the content-addressable blob linked to the specified repository.
    """
    assert blob_digest
    try:
        storage = (
            ImageStorage.select(ImageStorage.uuid)
            .join(Image)
            .join(Repository)
            .join(Namespace, on=(Namespace.id == Repository.namespace_user))
            .where(
                Repository.name == repo_name,
                Namespace.username == namespace,
                ImageStorage.content_checksum == blob_digest,
                ImageStorage.uploading == False,
            )
            .get()
        )

        return storage_model.get_storage_by_uuid(storage.uuid)
    except (ImageStorage.DoesNotExist, InvalidImageException):
        raise BlobDoesNotExist("Blob does not exist with digest: {0}".format(blob_digest))


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
                uploading=False,
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
    random_image_name = str(uuid4())

    # Create a temporary link into the repository, to be replaced by the v1 metadata later
    # and create a temporary tag to reference it
    image = Image.create(
        storage=storage, docker_image_id=random_image_name, repository=repository_id
    )
    temp_tag = tag.create_temporary_hidden_tag(repository_id, image, link_expiration_s)
    if temp_tag is None:
        image.delete_instance()


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
        return BlobUpload.select().where(BlobUpload.uuid == upload_uuid).get()
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
        return ImageStorage.get(content_checksum=digest, uploading=False)
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
        return ImageStorage.get(content_checksum=digest, uploading=False)
    except ImageStorage.DoesNotExist:
        record = ImageStorage.create(
            image_size=len(byte_data), content_checksum=digest, cas_path=True, uploading=True
        )
        preferred = storage.preferred_locations[0]
        location_obj = ImageStorageLocation.get(name=preferred)
        try:
            storage.put_content([preferred], storage_model.get_layer_path(record), byte_data)
            ImageStoragePlacement.create(storage=record, location=location_obj)

            record.uploading = False
            record.save()
        except:
            logger.exception("Exception when trying to write special layer %s", digest)
            record.delete_instance()
            raise

        return record
