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
)
from data import model
from util.registry.replication import queue_storage_replication


def backfill_replication():
    encountered = set()
    query = (
        Image.select(Image, ImageStorage, Repository, User)
        .join(ImageStorage)
        .switch(Image)
        .join(Repository)
        .join(User)
    )

    for image in query:
        if image.storage.uuid in encountered:
            continue

        namespace = image.repository.namespace_user
        locations = model.user.get_region_locations(namespace)
        locations_required = locations | set(storage.default_locations)

        query = (
            ImageStoragePlacement.select(ImageStoragePlacement, ImageStorageLocation)
            .where(ImageStoragePlacement.storage == image.storage)
            .join(ImageStorageLocation)
        )

        existing_locations = set([p.location.name for p in query])
        locations_missing = locations_required - existing_locations
        if locations_missing:
            print("Enqueueing image storage %s to be replicated" % (image.storage.uuid))
            encountered.add(image.storage.uuid)

            if not image_replication_queue.alive([image.storage.uuid]):
                queue_storage_replication(image.repository.namespace_user.username, image.storage)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not features.STORAGE_REPLICATION:
        print("Storage replication is not enabled")
    else:
        backfill_replication()
