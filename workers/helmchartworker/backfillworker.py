import json
import logging
import logging.config
import time

from peewee import JOIN, fn

import features
from app import app, helm_chart_metadata_queue
from data.database import HelmChartMetadata, Manifest, Repository, User
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from util.metrics.prometheus import helm_backfill_enqueued, helm_backfill_remaining
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

HELM_CHART_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"

BACKFILL_FREQUENCY = app.config.get("HELM_CHART_BACKFILL_WORKER_FREQUENCY", 60 * 60)
BACKFILL_BATCH_SIZE = app.config.get("HELM_CHART_BACKFILL_BATCH_SIZE", 500)
BACKFILL_QUEUE_LIMIT = app.config.get("HELM_CHART_BACKFILL_QUEUE_LIMIT", 1000)
LOCK_TTL = BACKFILL_FREQUENCY + 60


class HelmChartBackfillWorker(Worker):
    """
    Periodic worker that scans for existing Helm chart manifests without
    HelmChartMetadata rows and enqueues them for extraction.
    """

    def __init__(self):
        super(HelmChartBackfillWorker, self).__init__()
        self._cursor_id = 0
        self.add_operation(self._backfill_helm_charts, BACKFILL_FREQUENCY)

    def _backfill_helm_charts(self):
        try:
            with GlobalLock("HELM_CHART_BACKFILL", lock_ttl=LOCK_TTL):
                return self._do_backfill()
        except LockNotAcquiredException:
            logger.debug("Could not acquire global lock for Helm chart backfill")
            return False

    def _do_backfill(self):
        if not features.HELM_CHART_METADATA_EXTRACTION:
            logger.debug("Helm chart metadata extraction is disabled; skipping backfill enqueue")
            return False

        _, available_not_running, _ = helm_chart_metadata_queue.get_metrics()
        if available_not_running >= BACKFILL_QUEUE_LIMIT:
            logger.debug(
                "Queue has %d items pending; skipping backfill cycle",
                available_not_running,
            )
            return False

        max_manifest_id = Manifest.select(fn.Max(Manifest.id)).scalar() or 0
        if max_manifest_id == 0:
            return False

        if self._cursor_id >= max_manifest_id:
            self._cursor_id = 0
            logger.debug("Backfill cursor wrapped; starting new pass")

        # Bound the PK range scanned per cycle so the query cost is independent
        # of total table size.  Within the window the planner walks the PK index,
        # checks config_media_type, and probes the HelmChartMetadata unique index.
        scan_start = self._cursor_id
        scan_end = self._cursor_id + BACKFILL_BATCH_SIZE * 20

        unprocessed = (
            Manifest.select(
                Manifest.id,
                Manifest.digest,
                Manifest.repository,
                Manifest.config_media_type,
                Repository.id,
                Repository.name,
                Repository.namespace_user,
                User.id,
                User.username,
                HelmChartMetadata.id,
            )
            .join(Repository, on=(Manifest.repository == Repository.id))
            .join(User, on=(Repository.namespace_user == User.id))
            .switch(Manifest)
            .join(
                HelmChartMetadata,
                JOIN.LEFT_OUTER,
                on=(Manifest.id == HelmChartMetadata.manifest),
            )
            .where(
                Manifest.id > self._cursor_id,
                Manifest.id <= scan_end,
                Manifest.config_media_type == HELM_CHART_CONFIG_TYPE,
                HelmChartMetadata.id.is_null(),
            )
            .order_by(Manifest.id)
            .limit(BACKFILL_BATCH_SIZE)
        )

        enqueued = 0
        last_seen_id = self._cursor_id
        for manifest_row in unprocessed:
            last_seen_id = manifest_row.id
            try:
                namespace_name = manifest_row.repository.namespace_user.username
                repo_name = manifest_row.repository.name
            except Exception:
                logger.warning(
                    "Could not resolve namespace for manifest %s, skipping",
                    manifest_row.id,
                )
                continue

            manifest_key = [namespace_name, repo_name, str(manifest_row.id)]
            if helm_chart_metadata_queue.alive(manifest_key):
                continue

            helm_chart_metadata_queue.put(
                manifest_key,
                json.dumps(
                    {
                        "manifest_id": manifest_row.id,
                        "repository_id": manifest_row.repository_id,
                        "manifest_digest": manifest_row.digest,
                    }
                ),
            )
            enqueued += 1
            helm_backfill_enqueued.inc()

            _, current_pending, _ = helm_chart_metadata_queue.get_metrics()
            if current_pending >= BACKFILL_QUEUE_LIMIT:
                logger.debug(
                    "Queue reached %d items (limit %d); stopping enqueue",
                    current_pending,
                    BACKFILL_QUEUE_LIMIT,
                )
                break

        if last_seen_id == self._cursor_id:
            self._cursor_id = scan_end
        else:
            self._cursor_id = last_seen_id

        remaining_pk_range = max(0, max_manifest_id - self._cursor_id)
        helm_backfill_remaining.set(remaining_pk_range)

        if enqueued == 0:
            logger.debug(
                "No unprocessed Helm manifests in range %d–%d",
                scan_start,
                scan_end,
            )
            return False

        logger.info(
            "Backfill enqueued %d Helm charts (cursor at %d / %d)",
            enqueued,
            self._cursor_id,
            max_manifest_id,
        )
        return True


def create_gunicorn_worker():
    worker = GunicornWorker(
        __name__,
        app,
        HelmChartBackfillWorker(),
        features.HELM_CHART_METADATA_BACKFILL,
    )
    return worker


def main():
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.HELM_CHART_METADATA_BACKFILL:
        logger.debug("Helm chart backfill worker not enabled; skipping")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    worker = HelmChartBackfillWorker()
    worker.start()


if __name__ == "__main__":
    main()
