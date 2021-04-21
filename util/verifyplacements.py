"""
Usage (from the root in the container): venv/bin/python -m util.verifyplacements.

This script verifies that if a blob is listed as being in a specific storage location, the file
actually exists there. If the file is not found in that storage location, the placement entry in the
database is removed.
"""

import logging

from peewee import fn

from app import storage
from data import model
from data.database import ImageStorage, ImageStoragePlacement, ImageStorageLocation
from util.migrate.allocator import yield_random_entries

logger = logging.getLogger(__name__)

LOCATION_MAP = {}


def _get_location_row(location):
    if location in LOCATION_MAP:
        return LOCATION_MAP[location]

    location_row = ImageStorageLocation.get(name=location)
    LOCATION_MAP[location] = location_row
    return location_row


def verify_placements():
    encountered = set()

    iterator = yield_random_entries(
        lambda: ImageStorage.select(),
        ImageStorage.id,
        1000,
        ImageStorage.select(fn.Max(ImageStorage.id)).scalar(),
        1,
    )

    for storage_row, abt, _ in iterator:
        if storage_row.id in encountered:
            continue

        encountered.add(storage_row.id)

        logger.info("Checking placements for storage `%s`", storage_row.uuid)
        try:
            with_locations = model.storage.get_storage_by_uuid(storage_row.uuid)
        except model.InvalidImageException:
            logger.exception("Could not find storage `%s`", storage_row.uuid)
            continue

        storage_path = model.storage.get_layer_path(storage_row)
        locations_to_check = set(with_locations.locations)
        if locations_to_check:
            logger.info(
                "Checking locations `%s` for storage `%s`", locations_to_check, storage_row.uuid
            )
            for location in locations_to_check:
                logger.info("Checking location `%s` for storage `%s`", location, storage_row.uuid)
                if not storage.exists([location], storage_path):
                    location_row = _get_location_row(location)
                    logger.info(
                        "Location `%s` is missing for storage `%s`; removing",
                        location,
                        storage_row.uuid,
                    )
                    (
                        ImageStoragePlacement.delete()
                        .where(
                            ImageStoragePlacement.storage == storage_row,
                            ImageStoragePlacement.location == location_row,
                        )
                        .execute()
                    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    verify_placements()
