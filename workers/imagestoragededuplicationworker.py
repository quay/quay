import logging

import features

from app import app
from data.database import (
    ImageStorage,
    ImageStorageSignature,
    ImageStoragePlacement,
    ImageStorageLocation,
    UploadedBlob,
    ManifestBlob,
)
from data.model import db_transaction
from util.migrate.allocator import yield_random_entries

logger = logging.getLogger(__name__)

WORKER_FREQUENCY = app.config.get("IMAGESTORAGE_DEDUPUPLICATION_WORKER_FREQUENCY", 60 * 5)
BATCH_SIZE = 1000


class ImageStorageDeduplicationWorker(Worker):
    """
    """
    def __init__(self):
        super(ManifestBackfillWorker, self).__init__()
        self.add_operation(self._deduplicate_imagestorage, WORKER_FREQUENCY)

    def _deduplicate_imagestorage(self):
        duplicate_query = (
            ImageStorage.select(
                ImageStorage.image_size,
                ImageStorage.content_checksum,
                ImageStorage.uncompressed_size,
            ).group_by(
                ImageStorage.image_size, 
                ImageStorage.content_checksum,
                ImageStorage.uncompressed_size,
            ).having(
                fn.COUNT(ImageStorage.id) > 1
            )
        )

        try:
            duplicate_query.get()
        except ImageStorage.DoesNotExist:
            logger.debug("ImageStorage deduplication worker has completed; no more rows to remove")
            return False

        # Get duplicate rows for a checksum
        duplicate_rows = duplicate_query[:BATCH_SIZE]

        for duplicate_row in duplicate_rows:
            with db_transaction():
                duplicate_rows_for_checksum = (
                    ImageStorage.select().join(
                        duplicate_query,
                        JOIN.LEFT_OUTER,
                        on=(
                            (ImageStorage.image_size==duplicate_query.c.image_size) &
                            (ImageStorage.content_checksum==duplicate_query.c.content_checksum) &
                            (
                                (ImageStorage.uncompressed_size==ImageStorage.uncompressed_size) |
                                (ImageStorage.uncompressed_size.is_null() & ImageStorage.uncompressed_size.is_null())
                            ) & 
                            (ImageStorage.uploading==False) & (ImageStorage.cas_path==True) & (ImageStorage.content_checksum==duplicate_row.content_checksum)
                        )
                    ).where(
                        ~(duplicate_query.c.content_checksum >> None)
                    )
                )
    
                storage_to_keep = duplicate_rows_for_checksum.get()
    
                # Signatures
                sigs = ImageStorageSignature.select().join(ImageStorage).where(
                    (ImageStorageSignature.storage << list(duplicate_rows_for_checksum)),
                    (ImageStorageSignature.uploading == False)
                )
    
                sig_to_keep = sigs[0]
                for sig in sigs[1:]:
                    sig.delete_instance()
    
                sig_to_keep.storage = storage_to_keep
                sig_to_keep.save()
    
                # ImageStoragePlacement
                ImageStoragePlacementAlias = ImageStoragePlacement.alias()
                placements_for_checksum = ImageStoragePlacement.select().join(ImageStorage).where(
                    (ImageStoragePlacement.storage << list(duplicate_rows_for_checksum))
                )
                for location in ImageStorageLocation.select():
                    placements_for_location = ImageStoragePlacement.select().join(
                        placements_for_checksum,
                        on=(
                            (ImageStoragePlacement.location==location)
                        )
                    )

                    if len(placements_to_keep) > 0:
                        placement_to_keep = placements_for_location[0]
                        for placement in placements_for_location[1:]:
                            placement.delete_instance()

                        placement_to_keep.storage = storage_to_keep
                        placement_to_keep.save()

                # UploadedBlob
                uploaded_blobs = UploadedBlob.select().join(ImageStorage).where(
                    (UploadedBlob << list(duplicate_rows_for_checksum))
                )
                for uploaded_blob in uploaded_blobs:
                    uploaded_blob.blob = storage_to_keep
                    uploaded_blob.save()
    
                # ManifestBlob
                manifest_blobs = ManifestBlob.select().join(ImageStorage).where(
                    (ManifestBlob.blob << list(duplicate_rows_for_checksum))
                )
                for manifest_blob in manifest_blobs:
                    manifest_blob.blob = storage_to_keep
                    manifest_blob.save()
    
                # Finally delete the duplicate storage
                for duplicate_row in duplicate_rows_for_checksum[1:]:
                    duplicate_row.delete_instance()
    
        return True
