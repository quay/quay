import logging
import time

from peewee import fn

import features
from app import app, proxy_cache_blob_queue
from data.database import (
    ImageStorage,
    ImageStoragePlacement,
    IndexStatus,
    Manifest,
    ManifestBlob,
    ManifestSecurityStatus,
    db_transaction,
)
from data.model import repository, user
from data.registry_model.datatypes import RepositoryReference
from data.registry_model.registry_proxy_model import ProxyModel
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.queueworker import (
    JobException,
    QueueWorker,
    WorkerSleepException,
    WorkerUnhealthyException,
)
from workers.worker import with_exponential_backoff

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 10
RESERVATION_SECONDS = 60 * 20


class ProxyCacheBlobWorker(QueueWorker):
    def _all_blobs_downloaded_for_manifest(self, manifest_id, repo_id):
        """
        Check if all blobs associated with a manifest have ImageStoragePlacement.
        Returns True if all blobs are downloaded, False otherwise.
        """
        # Check if there exists a blob in the manifest that does not have a placement.
        missing_placement = ManifestBlob.select().where(
            ManifestBlob.manifest == manifest_id,
            ManifestBlob.repository == repo_id,
            ~fn.EXISTS(
                ImageStoragePlacement.select().where(
                    ImageStoragePlacement.storage == ManifestBlob.blob
                )
            ),
        )

        return not missing_placement.exists()

    def _reset_security_status_if_complete(self, blob_digest, repo_id):
        """
        Check if the downloaded blob completes all blobs for any manifest.
        If so, reset the security status to allow Clair scanning.
        """
        # Find all manifests that include this blob
        manifests = (
            Manifest.select(Manifest.id)
            .join(ManifestBlob)
            .join(ImageStorage)
            .where(
                ManifestBlob.repository_id == repo_id,
                ImageStorage.content_checksum == blob_digest,
            )
            .distinct()
        )

        for manifest in manifests:
            # Check if all blobs for this manifest are downloaded
            if self._all_blobs_downloaded_for_manifest(manifest.id, repo_id):
                # Delete MANIFEST_UNSUPPORTED status to allow rescanning
                with db_transaction():
                    deleted = (
                        ManifestSecurityStatus.delete()
                        .where(
                            ManifestSecurityStatus.manifest == manifest.id,
                            ManifestSecurityStatus.repository == repo_id,
                            ManifestSecurityStatus.index_status == IndexStatus.MANIFEST_UNSUPPORTED,
                        )
                        .execute()
                    )

                    if deleted > 0:
                        logger.info(
                            "Reset security status for manifest %s in repo %s - all blobs downloaded",
                            manifest.id,
                            repo_id,
                        )

    def process_queue_item(self, job_details):
        repo_id = job_details["repo_id"]
        namespace_name = job_details["namespace"]
        digest = job_details["digest"]
        username = job_details["username"]

        repo_name = repository.lookup_repository(repo_id).name
        repo_ref = RepositoryReference.for_id(repo_id)
        user_ref = user.get_username(username) if username else None

        registry_proxy_model = ProxyModel(
            namespace_name,
            repo_name,
            user_ref,
        )

        logger.debug(
            "Starting proxy cache blob download for digest %s for repo id %s",
            digest,
            repo_id,
        )

        if self._should_download_blob(digest, repo_id, registry_proxy_model):
            try:
                registry_proxy_model._download_blob(
                    repo_ref,
                    digest,
                )

                # Check if this blob completes all blobs for any manifest
                # If so, reset the security status to allow Clair scanning
                self._reset_security_status_if_complete(digest, repo_id)

            except:
                logger.exception(
                    "Exception when downloading blob %s for repo id %s for proxy cache",
                    digest,
                    repo_id,
                )

        return

    def _should_download_blob(self, digest, repo_id, registry_proxy_model):
        blob = registry_proxy_model._get_shared_storage(digest)
        if blob is None:
            try:
                blob = (
                    ImageStorage.select()
                    .join(ManifestBlob)
                    .where(
                        ManifestBlob.repository_id == repo_id,
                        ImageStorage.content_checksum == digest,
                    )
                    .get()
                )
            except ImageStorage.DoesNotExist:
                # There should be placeholder blobs after manifest requests
                return False

        try:
            ImageStoragePlacement.select().where(ImageStoragePlacement.storage == blob).get()
        except ImageStoragePlacement.DoesNotExist:
            return True

        return False


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    proxy_cache_blob_worker = ProxyCacheBlobWorker(
        proxy_cache_blob_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker = GunicornWorker(__name__, app, proxy_cache_blob_worker, features.PROXY_CACHE)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.PROXY_CACHE or not features.PROXY_CACHE_BLOB_DOWNLOAD:
        while True:
            time.sleep(100000)

    logger.debug("Starting proxy cache blob worker")
    worker = ProxyCacheBlobWorker(
        proxy_cache_blob_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker.start()
