import json
import logging
import time

from peewee import fn

import features
from app import app
from data.database import Manifest
from image.shared.schemas import ManifestException, parse_manifest_from_bytes
from util.bytes import Bytes
from util.log import logfile_path
from util.migrate.allocator import yield_random_entries
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

WORKER_FREQUENCY = app.config.get("MANIFEST_SUBJECT_BACKFILL_WORKER_FREQUENCY", 60)


class ManifestSubjectBackfillWorker(Worker):
    """
    Worker which backfills the newly added subject fields onto Manifest.
    """

    def __init__(self):
        super().__init__()
        self.add_operation(self._backfill_manifest_subject, WORKER_FREQUENCY)
        self.add_operation(self._backfill_manifest_artifact_type, WORKER_FREQUENCY)

    def _backfill_manifest_subject(self):
        try:
            Manifest.select().where(
                (Manifest.subject_backfilled == False) | (Manifest.subject_backfilled >> None),
            ).get()
        except Manifest.DoesNotExist:
            logger.debug("Manifest subject backfill worker has completed; skipping")
            return False

        iterator = yield_random_entries(
            lambda: Manifest.select().where(
                (Manifest.subject_backfilled == False) | (Manifest.subject_backfilled >> None)
            ),
            Manifest.id,
            250,
            Manifest.select(fn.Max(Manifest.id)).scalar(),
            1,
        )

        for manifest_row, abt, _ in iterator:
            if manifest_row.subject_backfilled:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

            logger.debug("Setting manifest subject for manifest %s", manifest_row.id)
            manifest_bytes = Bytes.for_string_or_unicode(manifest_row.manifest_bytes)

            try:
                parsed = parse_manifest_from_bytes(
                    manifest_bytes, manifest_row.media_type.name, validate=False
                )
                subject = parsed.subject
            except ManifestException as me:
                logger.warning(
                    "Got exception when trying to parse manifest %s: %s", manifest_row.id, me
                )

            updated = (
                Manifest.update(
                    subject=subject,
                    subject_backfilled=True,
                )
                .where(
                    Manifest.id == manifest_row.id,
                    (Manifest.subject_backfilled == False) | (Manifest.subject_backfilled >> None),
                )
                .execute()
            )
            if updated != 1:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

        return True

    def _backfill_manifest_artifact_type(self):
        try:
            Manifest.select().where(
                (Manifest.artifact_type_backfilled == False)
                | (Manifest.artifact_type_backfilled >> None),
            ).get()
        except Manifest.DoesNotExist:
            logger.debug("Manifest artifact_type backfill worker has completed; skipping")
            return False

        iterator = yield_random_entries(
            lambda: Manifest.select().where(
                (Manifest.artifact_type_backfilled == False)
                | (Manifest.artifact_type_backfilled >> None)
            ),
            Manifest.id,
            250,
            Manifest.select(fn.Max(Manifest.id)).scalar(),
            1,
        )

        for manifest_row, abt, _ in iterator:
            if manifest_row.artifact_type_backfilled:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

            logger.debug("Setting artifact_type for manifest %s", manifest_row.id)
            manifest_bytes = Bytes.for_string_or_unicode(manifest_row.manifest_bytes)

            try:
                parsed = parse_manifest_from_bytes(
                    manifest_bytes, manifest_row.media_type.name, validate=False
                )
                artifact_type = parsed.artifact_type
            except ManifestException as me:
                logger.warning(
                    "Got exception when trying to parse manifest %s: %s", manifest_row.id, me
                )

            updated = (
                Manifest.update(
                    artifact_type=artifact_type,
                    artifact_type_backfilled=True,
                )
                .where(
                    Manifest.id == manifest_row.id,
                    (Manifest.artifact_type_backfilled == False)
                    | (Manifest.artifact_type_backfilled >> None),
                )
                .execute()
            )
            if updated != 1:
                logger.debug("Another worker preempted this worker")
                abt.set()
                continue

        return True


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(
        __name__, app, ManifestSubjectBackfillWorker(), features.MANIFEST_SUBJECT_BACKFILL
    )
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.MANIFEST_SUBJECT_BACKFILL:
        logger.debug("Manifest backfill worker not enabled; skipping")
        while True:
            time.sleep(100000)

    worker = ManifestSubjectBackfillWorker()
    worker.start()


if __name__ == "__main__":
    main()
