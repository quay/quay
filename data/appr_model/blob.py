import logging

from peewee import IntegrityError

from data.model import db_transaction

logger = logging.getLogger(__name__)


def _ensure_sha256_header(digest):
    if digest.startswith("sha256:"):
        return digest
    return "sha256:" + digest


def get_blob(digest, models_ref):
    """
    Find a blob by its digest.
    """
    Blob = models_ref.Blob
    return Blob.select().where(Blob.digest == _ensure_sha256_header(digest)).get()


def get_or_create_blob(digest, size, media_type_name, locations, models_ref):
    """
    Try to find a blob by its digest or create it.
    """
    Blob = models_ref.Blob
    BlobPlacement = models_ref.BlobPlacement

    # Get or create the blog entry for the digest.
    try:
        blob = get_blob(digest, models_ref)
        logger.debug("Retrieved blob with digest %s", digest)
    except Blob.DoesNotExist:
        blob = Blob.create(
            digest=_ensure_sha256_header(digest),
            media_type_id=Blob.media_type.get_id(media_type_name),
            size=size,
        )
        logger.debug("Created blob with digest %s", digest)

    # Add the locations to the blob.
    for location_name in locations:
        location_id = BlobPlacement.location.get_id(location_name)
        try:
            BlobPlacement.create(blob=blob, location=location_id)
        except IntegrityError:
            logger.debug("Location %s already existing for blob %s", location_name, blob.id)

    return blob


def get_blob_locations(digest, models_ref):
    """
    Find all locations names for a blob.
    """
    Blob = models_ref.Blob
    BlobPlacement = models_ref.BlobPlacement
    BlobPlacementLocation = models_ref.BlobPlacementLocation

    return [
        x.name
        for x in BlobPlacementLocation.select()
        .join(BlobPlacement)
        .join(Blob)
        .where(Blob.digest == _ensure_sha256_header(digest))
    ]


def ensure_blob_locations(models_ref, *names):
    BlobPlacementLocation = models_ref.BlobPlacementLocation

    with db_transaction():
        locations = BlobPlacementLocation.select().where(BlobPlacementLocation.name << names)

        insert_names = list(names)

        for location in locations:
            insert_names.remove(location.name)

        if not insert_names:
            return

        data = [{"name": name} for name in insert_names]
        BlobPlacementLocation.insert_many(data).execute()
