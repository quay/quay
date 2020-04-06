import logging

from datetime import date, timedelta

import features

from app import app  # This is required to initialize the database.
from data import model
from data.logs_model import logs_model
from workers.worker import Worker, with_exponential_backoff


logger = logging.getLogger(__name__)


POLL_PERIOD_SECONDS = 10


class RepositoryActionCountWorker(Worker):
    def __init__(self):
        super(RepositoryActionCountWorker, self).__init__()
        self.add_operation(self._count_repository_actions, POLL_PERIOD_SECONDS)

    @with_exponential_backoff(backoff_multiplier=10, max_backoff=3600, max_retries=10)
    def _count_repository_actions(self):
        """
        Counts actions and aggregates search scores for a random repository for the previous day.
        """
        # Select a repository that needs its actions for the last day updated.
        to_count = model.repositoryactioncount.find_uncounted_repository()
        if to_count is None:
            logger.debug("No further repositories to count")
            return False

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


if __name__ == "__main__":
    worker = RepositoryActionCountWorker()
    worker.start()
