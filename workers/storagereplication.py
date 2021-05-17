import logging
import time

import features

from app import app, storage as app_storage, image_replication_queue
from data.database import CloseForLongOperation
from data import model
from workers.queueworker import QueueWorker, WorkerUnhealthyException, JobException
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 10
RESERVATION_SECONDS = app.config.get("STORAGE_REPLICATION_PROCESSING_SECONDS", 60 * 20)


class StorageReplicationWorker(QueueWorker):
    def process_queue_item(self, job_details):
        storage_uuid = job_details["storage_id"]
        namespace_id = job_details["namespace_user_id"]

        logger.debug(
            "Starting replication of image storage %s under namespace %s",
            storage_uuid,
            namespace_id,
        )
        try:
            namespace = model.user.get_namespace_user_by_user_id(namespace_id)
        except model.user.InvalidUsernameException:
            logger.exception(
                "Exception when looking up namespace %s for replication of image storage %s",
                namespace_id,
                storage_uuid,
            )
            return

        self.replicate_storage(namespace, storage_uuid, app_storage)

    def _backoff_check_exists(self, location, path, storage, backoff_check=True):
        for retry in range(0, 4):
            if storage.exists([location], path):
                return True

            if not backoff_check:
                return False

            seconds = pow(2, retry) * 2
            logger.debug(
                "Cannot find path `%s` in location %s (try #%s). Sleeping for %s seconds",
                path,
                location,
                retry,
                seconds,
            )
            time.sleep(seconds)

        return False

    def replicate_storage(self, namespace, storage_uuid, storage, backoff_check=True):
        # Lookup the namespace and its associated regions.
        if not namespace:
            logger.debug("Unknown namespace when trying to replicate storage %s", storage_uuid)
            return

        locations = model.user.get_region_locations(namespace)

        # Lookup the image storage.
        try:
            partial_storage = model.storage.get_storage_by_uuid(storage_uuid)
        except model.InvalidImageException:
            logger.debug("Unknown storage: %s", storage_uuid)
            return

        # Check to see if the image is at all the required locations.
        locations_required = locations | set(storage.default_locations)
        locations_missing = locations_required - set(partial_storage.locations)

        logger.debug(
            "For replication of storage %s under namespace %s: %s required; %s missing",
            storage_uuid,
            namespace.username,
            locations_required,
            locations_missing,
        )

        if not locations_missing:
            logger.debug(
                "No missing locations for storage %s under namespace %s. Required: %s",
                storage_uuid,
                namespace.username,
                locations_required,
            )
            return

        # For any missing storage locations, initiate a copy.
        existing_location = list(partial_storage.locations)[0]
        path_to_copy = model.storage.get_layer_path(partial_storage)

        # Lookup and ensure the existing location exists.
        if not self._backoff_check_exists(existing_location, path_to_copy, storage, backoff_check):
            logger.warning(
                "Cannot find image storage %s in existing location %s; stopping replication",
                storage_uuid,
                existing_location,
            )
            raise JobException()

        # For each missing location, copy over the storage.
        for location in locations_missing:
            logger.debug(
                "Starting copy of storage %s to location %s from %s",
                partial_storage.uuid,
                location,
                existing_location,
            )

            # Copy the binary data.
            copied = False
            try:
                with CloseForLongOperation(app.config):
                    storage.copy_between(path_to_copy, existing_location, location)
                    copied = True
            except IOError:
                logger.exception(
                    "Failed to copy path `%s` of image storage %s to location %s",
                    path_to_copy,
                    partial_storage.uuid,
                    location,
                )
                raise JobException()
            except:
                logger.exception(
                    "Unknown exception when copying path %s of image storage %s to loc %s",
                    path_to_copy,
                    partial_storage.uuid,
                    location,
                )
                raise WorkerUnhealthyException()

            if copied:
                # Verify the data was copied to the target storage, to ensure that there are no cases
                # where we write the placement without knowing the data is present.
                if not self._backoff_check_exists(location, path_to_copy, storage, backoff_check):
                    logger.warning(
                        "Failed to find path `%s` in location `%s` after copy",
                        path_to_copy,
                        location,
                    )
                    raise JobException()

                # Create the storage location record for the storage now that the copy has
                # completed.
                model.storage.add_storage_placement(partial_storage, location)

                logger.debug(
                    "Finished copy of image storage %s to location %s from %s",
                    partial_storage.uuid,
                    location,
                    existing_location,
                )

        logger.debug(
            "Completed replication of image storage %s to locations %s from %s",
            partial_storage.uuid,
            locations_missing,
            existing_location,
        )


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    has_local_storage = False

    if features.STORAGE_REPLICATION:
        for storage_type, _ in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG", {}).values()):
            if storage_type == "LocalStorage":
                has_local_storage = True
                break

    feature_flag = (features.STORAGE_REPLICATION) and (not has_local_storage)
    repl_worker = StorageReplicationWorker(
        image_replication_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker = GunicornWorker(__name__, app, repl_worker, feature_flag)
    return worker


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    has_local_storage = False

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if features.STORAGE_REPLICATION:
        for storage_type, _ in list(app.config.get("DISTRIBUTED_STORAGE_CONFIG", {}).values()):
            if storage_type == "LocalStorage":
                has_local_storage = True
                break

    if not features.STORAGE_REPLICATION or has_local_storage:
        if has_local_storage:
            logger.error("Storage replication can't be used with local storage")
        else:
            logger.debug("Full storage replication disabled; skipping")
        while True:
            time.sleep(10000)

    logger.debug("Starting replication worker")
    worker = StorageReplicationWorker(
        image_replication_queue,
        poll_period_seconds=POLL_PERIOD_SECONDS,
        reservation_seconds=RESERVATION_SECONDS,
    )
    worker.start()
