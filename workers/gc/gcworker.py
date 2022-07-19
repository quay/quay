import logging

from contextlib import contextmanager

import features

from data.database import UseThenDisconnect, Repository
from data.registry_model import registry_model
from data.model.repository import get_random_gc_policy
from data.model.gc import garbage_collect_repo
from singletons.config import app_config
from workers.worker import Worker
from util.locking import GlobalLock, LockNotAcquiredException
from workers.gunicorn_worker import GunicornWorker
from util.metrics.prometheus import gc_iterations

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
            self._garbage_collection_repos, app_config.get("GARBAGE_COLLECTION_FREQUENCY", 30)
        )

    def _garbage_collection_repos(self, skip_lock_for_testing=False):
        """
        Performs garbage collection on repositories.
        """
        with UseThenDisconnect(app_config):
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
                with GlobalLock(
                    "REPO_GARBAGE_COLLECTION_%s" % repo_ref.id,
                    lock_ttl=REPOSITORY_GC_TIMEOUT + LOCK_TIMEOUT_PADDING,
                ) if not skip_lock_for_testing else empty_context():
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


def create_gunicorn_worker() -> GunicornWorker:
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(__name__, GarbageCollectionWorker())
    return worker


if __name__ == "__main__":
    GlobalLock.configure(app_config)
    worker = GarbageCollectionWorker()
    worker.start()
