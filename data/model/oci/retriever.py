import time

from image.shared.interfaces import ContentRetriever
from data.database import Manifest
from data.model.oci.blob import get_repository_blob_by_digest
from data.model.storage import get_layer_path
from util.bytes import Bytes

RETRY_COUNT = 5
RETRY_DELAY = 0.3  # seconds


class RepositoryContentRetriever(ContentRetriever):
    """
    Implementation of the ContentRetriever interface for manifests that retrieves config blobs and
    child manifests for the specified repository.
    """

    def __init__(self, repository_id, storage):
        self.repository_id = repository_id
        self.storage = storage

    @classmethod
    def for_repository(cls, repository_id, storage):
        return RepositoryContentRetriever(repository_id, storage)

    def get_manifest_bytes_with_digest(self, digest):
        """
        Returns the bytes of the manifest with the given digest or None if none found.
        """
        query = (
            Manifest.select()
            .where(Manifest.repository == self.repository_id)
            .where(Manifest.digest == digest)
        )

        try:
            return Bytes.for_string_or_unicode(query.get().manifest_bytes).as_encoded_str()
        except Manifest.DoesNotExist:
            return None

    def get_blob_bytes_with_digest(self, digest):
        """
        Returns the bytes of the blob with the given digest or None if none found.
        """
        blob = get_repository_blob_by_digest(self.repository_id, digest)
        if blob is None:
            return None

        assert blob.locations is not None

        # NOTE: Some storage engines are eventually consistent, and so we add a small
        # retry here for retrieving the blobs from storage, as they may just have been
        # written as part of the push process.
        for retry in range(0, RETRY_COUNT):
            try:
                return self.storage.get_content(blob.locations, get_layer_path(blob))
            except IOError:
                time.sleep(RETRY_DELAY)

        return None
