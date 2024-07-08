import logging
import time
from contextlib import contextmanager

import features
from app import app
from data.database import Repository, RepositoryState, UseThenDisconnect
from data.model.gc import garbage_collect_repo
from data.model.repository import get_random_gc_policy
from data.registry_model import registry_model
from notifications.notificationevent import RepoImageExpiryEvent
from util.locking import GlobalLock, LockNotAcquiredException
from util.metrics.prometheus import gc_iterations
from util.notification import scan_for_image_expiry_notifications
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

REPOSITORY_GC_TIMEOUT = 3 * 60 * 60  # 3h
LOCK_TIMEOUT_PADDING = 60  # 60 seconds


@contextmanager
def empty_context():
    yield None


class GarbageCollectionWorker(Worker):
    def __init__(self):
        super(GarbageCollectionWorker, self).__init__()
        self.add_operation(
            self._garbage_collection_repos, app.config.get("GARBAGE_COLLECTION_FREQUENCY", 30)
        )
        if features.IMAGE_EXPIRY_TRIGGER:
            self.add_operation(
                self._scan_notifications, app.config.get("GARBAGE_COLLECTION_FREQUENCY", 30)
            )

    def _scan_notifications(self):
        # scan for tags that are expiring based on configured RepositoryNotifications
        scan_for_image_expiry_notifications(event_name=RepoImageExpiryEvent.event_name())

    def _garbage_collection_repos(self, skip_lock_for_testing=False):
        """
        Performs garbage collection on repositories.
        """
        with UseThenDisconnect(app.config):
            policy = get_random_gc_policy()
            if policy is None:
                logger.debug("No GC policies found")
                return

            repo_ref = registry_model.find_repository_with_garbage(policy)
            if repo_ref is None:
                logger.debug("No repository with garbage found")
                return

            assert features.GARBAGE_COLLECTION

            try:
                with (
                    GlobalLock(
                        "REPO_GARBAGE_COLLECTION_%s" % repo_ref.id,
                        lock_ttl=REPOSITORY_GC_TIMEOUT + LOCK_TIMEOUT_PADDING,
                    )
                    if not skip_lock_for_testing
                    else empty_context()
                ):
                    try:
                        repository = Repository.get(id=repo_ref.id)
                    except Repository.DoesNotExist:
                        return

                    logger.debug(
                        "Starting GC of repository #%s (%s)", repository.id, repository.name
                    )
                    garbage_collect_repo(repository)
                    logger.debug(
                        "Finished GC of repository #%s (%s)", repository.id, repository.name
                    )
                    gc_iterations.inc()
            except LockNotAcquiredException:
                logger.debug("Could not acquire repo lock for garbage collection")


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, app, GarbageCollectionWorker(), features.GARBAGE_COLLECTION)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.GARBAGE_COLLECTION:
        logger.debug("Garbage collection is disabled; skipping")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    worker = GarbageCollectionWorker()
    worker.start()
