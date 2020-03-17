import logging
import time

import features

from app import app
from data.database import UseThenDisconnect, Repository
from data.registry_model import registry_model
from data.model.repository import get_random_gc_policy
from data.model.gc import garbage_collect_repo
from workers.worker import Worker


logger = logging.getLogger(__name__)


class GarbageCollectionWorker(Worker):
    def __init__(self):
        super(GarbageCollectionWorker, self).__init__()
        self.add_operation(
            self._garbage_collection_repos, app.config.get("GARBAGE_COLLECTION_FREQUENCY", 30)
        )

    def _garbage_collection_repos(self):
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
                repository = Repository.get(id=repo_ref.id)
            except Repository.DoesNotExist:
                return

            logger.debug("Starting GC of repository #%s (%s)", repository.id, repository.name)
            garbage_collect_repo(repository)
            logger.debug("Finished GC of repository #%s (%s)", repository.id, repository.name)


if __name__ == "__main__":
    if not features.GARBAGE_COLLECTION:
        logger.debug("Garbage collection is disabled; skipping")
        while True:
            time.sleep(100000)

    worker = GarbageCollectionWorker()
    worker.start()
