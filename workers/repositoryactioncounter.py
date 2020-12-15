import logging
import time

from datetime import date, timedelta
from math import log10

import features

from app import app  # This is required to initialize the database.
from data import model, database
from data.logs_model import logs_model
from util.migrate.allocator import yield_random_entries
from workers.worker import Worker, with_exponential_backoff
from workers.gunicorn_worker import GunicornWorker

logger = logging.getLogger(__name__)

POLL_PERIOD_SECONDS = 4 * 60 * 60  # 4 hours


class RepositoryActionCountWorker(Worker):
    def __init__(self):
        super(RepositoryActionCountWorker, self).__init__()
        self.add_operation(self._run_counting, POLL_PERIOD_SECONDS)

    def _run_counting(self):
        yesterday = date.today() - timedelta(days=1)

        def batch_query():
            return model.repositoryactioncount.missing_counts_query(yesterday)

        min_id = model.repository.get_min_id()
        max_id = model.repository.get_max_id()
        if min_id is None or max_id is None:
            return

        # Check for the number RAC entries vs number of repos. If they are the same,
        # nothing more to do.
        repo_count = model.repository.get_repository_count()
        rac_count = model.repositoryactioncount.found_entry_count(yesterday)
        if rac_count >= repo_count:
            logger.debug("All RAC entries found; nothing more to do")
            return

        # This gives us a scalable batch size into the millions.
        batch_size = int(3 ** log10(max(10, max_id - min_id)))

        iterator = yield_random_entries(
            batch_query,
            database.Repository.id,
            batch_size,
            max_id,
            min_id,
        )

        for candidate, abt, num_remaining in iterator:
            if model.repositoryactioncount.has_repository_action_count(candidate, yesterday):
                abt.set()
                continue

            if not self._count_repository_actions(candidate):
                abt.set()

    def _count_repository_actions(self, to_count):
        """
        Counts actions and aggregates search scores for a random repository for the previous day.
        """
        logger.debug("Found repository #%s to count", to_count.id)

        # Count the number of actions that occurred yesterday for the repository.
        yesterday = date.today() - timedelta(days=1)
        daily_count = logs_model.count_repository_actions(to_count, yesterday)
        if daily_count is None:
            logger.debug("Could not load count for repository #%s", to_count.id)
            return False

        # Store the count for the repository.
        was_counted = model.repositoryactioncount.store_repository_action_count(
            to_count, yesterday, daily_count
        )
        if not was_counted:
            logger.debug("Repository #%s was counted by another worker", to_count.id)
            return False

        # Update the search score for the repository now that its actions have been counted.
        logger.debug("Updating search score for repository #%s", to_count.id)
        was_updated = model.repositoryactioncount.update_repository_score(to_count)
        if not was_updated:
            logger.debug(
                "Repository #%s had its search score updated by another worker", to_count.id
            )
            return False

        logger.debug("Repository #%s search score updated", to_count.id)

        # Delete any entries older than the retention period for the repository.
        if features.CLEAR_EXPIRED_RAC_ENTRIES:
            while True:
                found = model.repositoryactioncount.delete_expired_entries(to_count, 30)
                if found <= 0:
                    break

            logger.debug("Repository #%s old entries removed", to_count.id)

        return True


def create_gunicorn_worker():
    """
    follows the gunicorn application factory pattern, enabling
    a quay worker to run as a gunicorn worker thread.

    this is useful when utilizing gunicorn's hot reload in local dev.

    utilizing this method will enforce a 1:1 quay worker to gunicorn worker ratio.
    """
    worker = GunicornWorker(
        __name__, app, RepositoryActionCountWorker(), features.REPOSITORY_ACTION_COUNTER
    )
    return worker


if __name__ == "__main__":
    if not features.REPOSITORY_ACTION_COUNTER:
        logger.info("Repository action count is disabled; skipping")
        while True:
            time.sleep(100000)

    worker = RepositoryActionCountWorker()
    worker.start()
