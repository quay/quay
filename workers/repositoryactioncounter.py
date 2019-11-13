import logging

from datetime import date, timedelta

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
        """ Counts actions and aggregates search scores for a random repository for the
        previous day. """
        to_count = model.repositoryactioncount.find_uncounted_repository()
        if to_count is None:
            logger.debug("No further repositories to count")
            return False

        yesterday = date.today() - timedelta(days=1)

        logger.debug("Found repository #%s to count", to_count.id)
        daily_count = logs_model.count_repository_actions(to_count, yesterday)
        if daily_count is None:
            logger.debug("Could not load count for repository #%s", to_count.id)
            return False

        was_counted = model.repositoryactioncount.store_repository_action_count(
            to_count, yesterday, daily_count
        )
        if not was_counted:
            logger.debug("Repository #%s was counted by another worker", to_count.id)
            return False

        logger.debug("Updating search score for repository #%s", to_count.id)
        was_updated = model.repositoryactioncount.update_repository_score(to_count)
        if not was_updated:
            logger.debug(
                "Repository #%s had its search score updated by another worker", to_count.id
            )
            return False

        logger.debug("Repository #%s search score updated", to_count.id)
        return True


if __name__ == "__main__":
    worker = RepositoryActionCountWorker()
    worker.start()
