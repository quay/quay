from image.docker.interfaces import ContentRetriever
from data.database import Manifest
from data.model.oci.blob import get_repository_blob_by_digest
from data.model.storage import get_layer_path


class RepositoryContentRetriever(ContentRetriever):
    """ Implementation of the ContentRetriever interface for manifests that retrieves
      config blobs and child manifests for the specified repository.
  """

    def __init__(self, repository_id, storage):
        self.repository_id = repository_id
        self.storage = storage

    @classmethod
    def for_repository(cls, repository_id, storage):
        return RepositoryContentRetriever(repository_id, storage)

    def get_manifest_bytes_with_digest(self, digest):
        """ Returns the bytes of the manifest with the given digest or None if none found. """
        query = (
            Manifest.select()
            .where(Manifest.repository == self.repository_id)
            .where(Manifest.digest == digest)
        )

        try:
            return query.get().manifest_bytes
        except Manifest.DoesNotExist:
            return None

    def get_blob_bytes_with_digest(self, digest):
        """ Returns the bytes of the blob with the given digest or None if none found. """
        blob = get_repository_blob_by_digest(self.repository_id, digest)
        if blob is None:
            return None

        assert blob.locations is not None
        return self.storage.get_content(blob.locations, get_layer_path(blob))
