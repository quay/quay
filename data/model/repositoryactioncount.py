import logging

from collections import namedtuple
from peewee import IntegrityError, JOIN

from datetime import date, timedelta, datetime
from data.database import (
    Repository,
    LogEntry,
    LogEntry2,
    LogEntry3,
    RepositoryActionCount,
    RepositorySearchScore,
    db_random_func,
    fn,
)

logger = logging.getLogger(__name__)

search_bucket = namedtuple("SearchBucket", ["delta", "days", "weight"])

# Defines the various buckets for search scoring. Each bucket is computed using the given time
# delta from today *minus the previous bucket's time period*. Once all the actions over the
# bucket's time period have been collected, they are multiplied by the given modifier. The modifiers
# for this bucket were determined via the integral of (2/((x/183)+1)^2)/183 over the period of days
# in the bucket; this integral over 0..183 has a sum of 1, so we get a good normalize score result.
SEARCH_BUCKETS = [
    search_bucket(timedelta(days=1), 1, 0.010870),
    search_bucket(timedelta(days=7), 6, 0.062815),
    search_bucket(timedelta(days=31), 24, 0.21604),
    search_bucket(timedelta(days=183), 152, 0.71028),
]

RAC_RETENTION_PERIOD = timedelta(days=365)


def count_repository_actions(to_count, day):
    """
    Aggregates repository actions from the LogEntry table for the specified day.

    Returns the count or None on error.
    """
    # TODO: Clean this up a bit.
    def lookup_action_count(model):
        return (
            model.select()
            .where(
                model.repository == to_count,
                model.datetime >= day,
                model.datetime < (day + timedelta(days=1)),
            )
            .count()
        )

    actions = (
        lookup_action_count(LogEntry3)
        + lookup_action_count(LogEntry2)
        + lookup_action_count(LogEntry)
    )

    return actions


def found_entry_count(day):
    """
    Returns the number of entries for the given day in the RAC table.
    """
    return RepositoryActionCount.select().where(RepositoryActionCount.date == day).count()


def has_repository_action_count(repository, day):
    """
    Returns whether there is a stored action count for a repository for a specific day.
    """
    try:
        RepositoryActionCount.get(repository=repository, date=day)
        return True
    except RepositoryActionCount.DoesNotExist:
        return False


def store_repository_action_count(repository, day, action_count):
    """
    Stores the action count for a repository for a specific day.

    Returns False if the repository already has an entry for the specified day.
    """
    try:
        RepositoryActionCount.create(repository=repository, date=day, count=action_count)
        return True
    except IntegrityError:
        logger.debug("Count already written for repository %s", repository.id)
        return False


def update_repository_score(repo):
    """
    Updates the repository score entry for the given table by retrieving information from the
    RepositoryActionCount table.

    Note that count_repository_actions for the repo should be called first. Returns True if the row
    was updated and False otherwise.
    """
    today = date.today()

    # Retrieve the counts for each bucket and calculate the final score.
    final_score = 0.0
    last_end_timedelta = timedelta(days=0)

    for bucket in SEARCH_BUCKETS:
        start_date = today - bucket.delta
        end_date = today - last_end_timedelta
        last_end_timedelta = bucket.delta

        query = RepositoryActionCount.select(
            fn.Sum(RepositoryActionCount.count), fn.Count(RepositoryActionCount.id)
        ).where(
            RepositoryActionCount.date >= start_date,
            RepositoryActionCount.date < end_date,
            RepositoryActionCount.repository == repo,
        )

        bucket_tuple = query.tuples()[0]
        logger.debug(
            "Got bucket tuple %s for bucket %s for repository %s", bucket_tuple, bucket, repo.id
        )

        if bucket_tuple[0] is None:
            continue

        bucket_sum = float(bucket_tuple[0])
        bucket_count = int(bucket_tuple[1])
        if not bucket_count:
            continue

        bucket_score = bucket_sum / (bucket_count * 1.0)
        final_score += bucket_score * bucket.weight

    # Update the existing repo search score row or create a new one.
    normalized_score = int(final_score * 100.0)
    try:
        try:
            search_score_row = RepositorySearchScore.get(repository=repo)
            search_score_row.last_updated = datetime.now()
            search_score_row.score = normalized_score
            search_score_row.save()
            return True
        except RepositorySearchScore.DoesNotExist:
            RepositorySearchScore.create(
                repository=repo, score=normalized_score, last_updated=today
            )
            return True
    except IntegrityError:
        logger.debug("RepositorySearchScore row already existed; skipping")
        return False


def missing_counts_query(date):
    """ Returns a query to find all Repository's with missing RAC entries for the given date. """
    subquery = (
        RepositoryActionCount.select(RepositoryActionCount.id, RepositoryActionCount.repository)
        .where(RepositoryActionCount.date == date)
        .alias("rac")
    )

    return (
        Repository.select()
        .join(subquery, JOIN.LEFT_OUTER, on=(Repository.id == subquery.c.repository_id))
        .where(subquery.c.id >> None)
    )


def delete_expired_entries(repo, limit=50):
    """ Deletes expired entries from the RepositoryActionCount table for a specific repository.
        Returns the number of entries removed.
    """
    threshold_date = datetime.today() - RAC_RETENTION_PERIOD
    found = list(
        RepositoryActionCount.select()
        .where(
            RepositoryActionCount.repository == repo, RepositoryActionCount.date < threshold_date
        )
        .limit(limit)
    )

    if not found:
        return 0

    assert len(found) <= limit

    count_removed = 0
    for entry in found:
        try:
            entry.delete_instance(recursive=False)
            count_removed += 1
        except IntegrityError:
            continue

    return count_removed
