import logging

from peewee import fn

import features

from app import app
from data.database import Manifest
from image.shared.schemas import parse_manifest_from_bytes, ManifestException
from workers.worker import Worker
from util.migrate.allocator import yield_random_entries
from util.bytes import Bytes
from util.log import logfile_path


logger = logging.getLogger(__name__)

WORKER_FREQUENCY = app.config.get("MANIFEST_BACKFILL_WORKER_FREQUENCY", 60 * 60)


class ManifestBackfillWorker(Worker):
    """
    Worker which backfills the newly added layers compressed size and config media type
    fields onto Manifest.
    """

    def __init__(self):
        super(ManifestBackfillWorker, self).__init__()
        self.add_operation(self._backfill_manifests, WORKER_FREQUENCY)

    def _backfill_manifests(self):
        try:
            Manifest.select().where(Manifest.layers_compressed_size >> None).get()
        except Manifest.DoesNotExist:
            logger.debug("Manifest backfill worker has completed; skipping")
            return False

        iterator = yield_random_entries(
            lambda: Manifest.select().where(Manifest.layers_compressed_size >> None),
            Manifest.id,
            250,
            Manifest.select(fn.Max(Manifest.id)).scalar(),
            1,
        )

        for manifest_row, abt, _ in iterator:
            if manifest_row.layers_compressed_size is not None:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

            logger.debug("Setting layers compressed size for manifest %s", manifest_row.id)
            layers_compressed_size = -1
            config_media_type = None
            manifest_bytes = Bytes.for_string_or_unicode(manifest_row.manifest_bytes)

            try:
                parsed = parse_manifest_from_bytes(
                    manifest_bytes, manifest_row.media_type.name, validate=False
                )
                layers_compressed_size = parsed.layers_compressed_size
                if layers_compressed_size is None:
                    layers_compressed_size = 0

                config_media_type = parsed.config_media_type or None
            except ManifestException as me:
                logger.warning(
                    "Got exception when trying to parse manifest %s: %s", manifest_row.id, me
                )

            assert layers_compressed_size is not None
            updated = (
                Manifest.update(
                    layers_compressed_size=layers_compressed_size,
                    config_media_type=config_media_type,
                )
                .where(Manifest.id == manifest_row.id, Manifest.layers_compressed_size >> None)
                .execute()
            )
            if updated != 1:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

        return True


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not features.MANIFEST_SIZE_BACKFILL:
        logger.debug("Manifest backfill worker not enabled; skipping")
        while True:
            time.sleep(100000)

    worker = ManifestBackfillWorker()
    worker.start()


if __name__ == "__main__":
    main()
