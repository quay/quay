from data.database import ImageStorage, ManifestBlob
from data.model import BlobDoesNotExist
from data.model.storage import get_storage_by_uuid, InvalidImageException
from data.model.blob import get_repository_blob_by_digest as legacy_get


def get_repository_blob_by_digest(repository, blob_digest):
    """
    Find the content-addressable blob linked to the specified repository and returns it or None if
    none.
    """
    try:
        storage = (
            ImageStorage.select(ImageStorage.uuid)
            .join(ManifestBlob)
            .where(
                ManifestBlob.repository == repository,
                ImageStorage.content_checksum == blob_digest,
            )
            .get()
        )

        return get_storage_by_uuid(storage.uuid)
    except (ImageStorage.DoesNotExist, InvalidImageException):
        # TODO: Remove once we are no longer using the legacy tables.
        # Try the legacy call.
        try:
            return legacy_get(repository, blob_digest)
        except BlobDoesNotExist:
            return None
