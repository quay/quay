from data.database import ImageStorage, ManifestBlob, UploadedBlob
from data.model import BlobDoesNotExist
from data.model.storage import get_storage_by_uuid, InvalidImageException


def get_repository_blob_by_digest(repository, blob_digest):
    """
    Find the content-addressable blob linked to the specified repository and returns it or None if
    none.
    """
    # First try looking for a recently uploaded blob. If none found that is matching,
    # check the repository itself.
    storage = _lookup_blob_uploaded(repository, blob_digest)
    if storage is None:
        storage = _lookup_blob_in_repository(repository, blob_digest)

    return get_storage_by_uuid(storage.uuid) if storage is not None else None


def _lookup_blob_uploaded(repository, blob_digest):
    try:
        return (
            ImageStorage.select(ImageStorage.uuid)
            .join(UploadedBlob)
            .where(
                UploadedBlob.repository == repository,
                ImageStorage.content_checksum == blob_digest,
                ImageStorage.uploading == False,
            )
            .get()
        )
    except ImageStorage.DoesNotExist:
        return None


def _lookup_blob_in_repository(repository, blob_digest):
    try:
        return (
            ImageStorage.select(ImageStorage.uuid)
            .join(ManifestBlob)
            .where(
                ManifestBlob.repository == repository,
                ImageStorage.content_checksum == blob_digest,
                ImageStorage.uploading == False,
            )
            .get()
        )
    except ImageStorage.DoesNotExist:
        return None
