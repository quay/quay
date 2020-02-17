import logging
import logging.config

import time

from peewee import JOIN, fn, IntegrityError

from app import app
from data.database import (
    UseThenDisconnect,
    TagManifestLabel,
    TagManifestLabelMap,
    TagManifestToManifest,
    ManifestLabel,
    db_transaction,
)
from workers.worker import Worker
from util.log import logfile_path
from util.migrate.allocator import yield_random_entries


logger = logging.getLogger(__name__)


WORKER_TIMEOUT = 600


class LabelBackfillWorker(Worker):
    def __init__(self):
        super(LabelBackfillWorker, self).__init__()
        self.add_operation(self._backfill_labels, WORKER_TIMEOUT)

    def _candidates_to_backfill(self):
        def missing_tmt_query():
            return (
                TagManifestLabel.select()
                .join(TagManifestLabelMap, JOIN.LEFT_OUTER)
                .where(TagManifestLabelMap.id >> None)
            )

        min_id = (
            TagManifestLabel.select(fn.Min(TagManifestLabel.id))
            .join(TagManifestLabelMap, JOIN.LEFT_OUTER)
            .where(TagManifestLabelMap.id >> None)
            .scalar()
        )
        max_id = TagManifestLabel.select(fn.Max(TagManifestLabel.id)).scalar()

        iterator = yield_random_entries(
            missing_tmt_query, TagManifestLabel.id, 100, max_id, min_id,
        )

        return iterator

    def _backfill_labels(self):
        with UseThenDisconnect(app.config):
            iterator = self._candidates_to_backfill()
            if iterator is None:
                logger.debug("Found no additional labels to backfill")
                time.sleep(10000)
                return None

            for candidate, abt, _ in iterator:
                if not backfill_label(candidate):
                    logger.info("Another worker pre-empted us for label: %s", candidate.id)
                    abt.set()


def lookup_map_row(tag_manifest_label):
    try:
        TagManifestLabelMap.get(tag_manifest_label=tag_manifest_label)
        return True
    except TagManifestLabelMap.DoesNotExist:
        return False


def backfill_label(tag_manifest_label):
    logger.info("Backfilling label %s", tag_manifest_label.id)

    # Ensure that a mapping row doesn't already exist. If it does, we've been preempted.
    if lookup_map_row(tag_manifest_label):
        return False

    # Ensure the tag manifest has been backfilled into the manifest table.
    try:
        tmt = TagManifestToManifest.get(tag_manifest=tag_manifest_label.annotated)
    except TagManifestToManifest.DoesNotExist:
        # We'll come back to this later.
        logger.debug(
            "Tag Manifest %s for label %s has not yet been backfilled",
            tag_manifest_label.annotated.id,
            tag_manifest_label.id,
        )
        return True

    repository = tag_manifest_label.repository

    # Create the new mapping entry and label.
    with db_transaction():
        if lookup_map_row(tag_manifest_label):
            return False

        label = tag_manifest_label.label
        if tmt.manifest:
            try:
                manifest_label = ManifestLabel.create(
                    manifest=tmt.manifest, label=label, repository=repository
                )
                TagManifestLabelMap.create(
                    manifest_label=manifest_label,
                    tag_manifest_label=tag_manifest_label,
                    label=label,
                    manifest=tmt.manifest,
                    tag_manifest=tag_manifest_label.annotated,
                )
            except IntegrityError:
                return False

    logger.info("Backfilled label %s", tag_manifest_label.id)
    return True


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if not app.config.get("BACKFILL_TAG_MANIFEST_LABELS", False):
        logger.debug("Manifest label backfill disabled; skipping")
        while True:
            time.sleep(100000)

    worker = LabelBackfillWorker()
    worker.start()
