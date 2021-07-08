import logging
import features

from app import storage, image_replication_queue
from data.database import (
    Image,
    ImageStorage,
    Repository,
    User,
    ImageStoragePlacement,
    ImageStorageLocation,
    Manifest,
    ManifestBlob,
)
from data import model
from util.registry.replication import queue_storage_replication


def backfill_replication():
    encountered = set()

    query = (
        ManifestBlob.select(ManifestBlob, Repository, User)
        .join(ImageStorage)
        .switch(ManifestBlob)
        .join(Repository)
        .join(User)
    )

    for manifest in query:
        if manifest.blob.uuid in encountered:
            continue

        namespace = manifest.repository.namespace_user
        locations = model.user.get_region_locations(namespace)
        locations_required = locations | set(storage.default_locations)

        query = (
            ImageStoragePlacement.select(ImageStoragePlacement, ImageStorageLocation)
            .where(ImageStoragePlacement.storage == manifest.blob)
            .join(ImageStorageLocation)
        )

        existing_locations = set([p.location.name for p in query])
        locations_missing = locations_required - existing_locations
        if locations_missing:
            print("Enqueueing manifest blob %s to be replicated" % (manifest.blob.uuid))
            encountered.add(manifest.blob.uuid)

            if not image_replication_queue.alive([manifest.blob.uuid]):
                queue_storage_replication(
                    manifest.repository.namespace_user.username, manifest.blob
                )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not features.STORAGE_REPLICATION:
        print("Storage replication is not enabled")
    else:
        backfill_replication()
