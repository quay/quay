# pylint: disable=protected-access

import logging

from datetime import datetime, timedelta

from tzlocal import get_localzone
from dateutil.relativedelta import relativedelta

from data import model
from data.model import config
from data.database import LogEntry, LogEntry2, LogEntry3, BaseModel, UseThenDisconnect
from data.logs_model.interface import (
    ActionLogsDataInterface,
    LogsIterationTimeout,
    LogRotationContextInterface,
)
from data.logs_model.datatypes import Log, AggregatedLogCount, LogEntriesPage
from data.logs_model.shared import SharedModel
from data.model.log import get_stale_logs, get_stale_logs_start_id, delete_stale_logs

logger = logging.getLogger(__name__)

MINIMUM_RANGE_SIZE = 1  # second
MAXIMUM_RANGE_SIZE = 60 * 60 * 24 * 31  # seconds ~= 1 month
EXPECTED_ITERATION_LOG_COUNT = 1000


LOG_MODELS = [LogEntry3, LogEntry2, LogEntry]


class TableLogsModel(SharedModel, ActionLogsDataInterface):
    """
    TableLogsModel implements the data model for the logs API backed by a single table in the
    database.
    """

    def __init__(self, should_skip_logging=None, **kwargs):
        self._should_skip_logging = should_skip_logging

    def lookup_logs(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        page_token=None,
        max_page_count=None,
    ):
        if filter_kinds is not None:
            assert all(isinstance(kind_name, str) for kind_name in filter_kinds)

        assert start_datetime is not None
        assert end_datetime is not None

        repository = None
        if repository_name and namespace_name:
            repository = model.repository.get_repository(namespace_name, repository_name)
            assert repository

        performer = None
        if performer_name:
            performer = model.user.get_user(performer_name)
            assert performer

        def get_logs(m, page_token):
            logs_query = model.log.get_logs_query(
                start_datetime,
                end_datetime,
                performer=performer,
                repository=repository,
                namespace=namespace_name,
                ignore=filter_kinds,
                model=m,
            )

            logs, next_page_token = model.modelutil.paginate(
                logs_query,
                m,
                descending=True,
                page_token=page_token,
                limit=20,
                max_page=max_page_count,
                sort_field_name="datetime",
            )

            return logs, next_page_token

        TOKEN_TABLE_ID = "tti"
        table_index = 0
        logs = []
        next_page_token = page_token or None

        # Skip empty pages (empty table)
        while len(logs) == 0 and table_index < len(LOG_MODELS) - 1:
            table_specified = (
                next_page_token is not None and next_page_token.get(TOKEN_TABLE_ID) is not None
            )
            if table_specified:
                table_index = next_page_token.get(TOKEN_TABLE_ID)

            logs_result, next_page_token = get_logs(LOG_MODELS[table_index], next_page_token)
            logs.extend(logs_result)

            if next_page_token is None and table_index < len(LOG_MODELS) - 1:
                next_page_token = {TOKEN_TABLE_ID: table_index + 1}

        return LogEntriesPage([Log.for_logentry(log) for log in logs], next_page_token)

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        if filter_kinds is not None:
            assert all(isinstance(kind_name, str) for kind_name in filter_kinds)

        repository = None
        if repository_name and namespace_name:
            repository = model.repository.get_repository(namespace_name, repository_name)
            assert repository

        performer = None
        if performer_name:
            performer = model.user.get_user(performer_name)
            assert performer

        def get_latest_logs(m):
            logs_query = model.log.get_latest_logs_query(
                performer=performer,
                repository=repository,
                namespace=namespace_name,
                ignore=filter_kinds,
                model=m,
                size=size,
            )

            logs = list(logs_query)
            return [Log.for_logentry(log) for log in logs]

        return get_latest_logs(LOG_MODELS[0])

    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ):
        if filter_kinds is not None:
            assert all(isinstance(kind_name, str) for kind_name in filter_kinds)

        if end_datetime - start_datetime > timedelta(seconds=MAXIMUM_RANGE_SIZE):
            raise Exception("Cannot lookup aggregated logs over a period longer than a month")

        repository = None
        if repository_name and namespace_name:
            repository = model.repository.get_repository(namespace_name, repository_name)

        performer = None
        if performer_name:
            performer = model.user.get_user(performer_name)

        entries = {}
        for log_model in LOG_MODELS:
            aggregated = model.log.get_aggregated_logs(
                start_datetime,
                end_datetime,
                performer=performer,
                repository=repository,
                namespace=namespace_name,
                ignore=filter_kinds,
                model=log_model,
            )

            for entry in aggregated:
                synthetic_date = datetime(
                    start_datetime.year,
                    start_datetime.month,
                    int(entry.day),
                    tzinfo=get_localzone(),
                )
                if synthetic_date.day < start_datetime.day:
                    synthetic_date = synthetic_date + relativedelta(months=1)

                key = "%s-%s" % (entry.kind_id, entry.day)

                if key in entries:
                    entries[key] = AggregatedLogCount(
                        entry.kind_id, entry.count + entries[key].count, synthetic_date
                    )
                else:
                    entries[key] = AggregatedLogCount(entry.kind_id, entry.count, synthetic_date)

        return list(entries.values())

    def count_repository_actions(self, repository, day):
        return model.repositoryactioncount.count_repository_actions(repository, day)

    def log_action(
        self,
        kind_name,
        namespace_name=None,
        performer=None,
        ip=None,
        metadata=None,
        repository=None,
        repository_name=None,
        timestamp=None,
        is_free_namespace=False,
    ):
        if self._should_skip_logging and self._should_skip_logging(
            kind_name, namespace_name, is_free_namespace
        ):
            return

        if repository_name is not None:
            assert repository is None
            assert namespace_name is not None
            repository = model.repository.get_repository(namespace_name, repository_name)

        model.log.log_action(
            kind_name,
            namespace_name,
            performer=performer,
            repository=repository,
            ip=ip,
            metadata=metadata or {},
            timestamp=timestamp,
        )

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        assert namespace_id is None or isinstance(namespace_id, int)
        assert repository_id is None or isinstance(repository_id, int)

        # Using an adjusting scale, start downloading log rows in batches, starting at
        # MINIMUM_RANGE_SIZE and doubling until we've reached EXPECTED_ITERATION_LOG_COUNT or
        # the lookup range has reached MAXIMUM_RANGE_SIZE. If at any point this operation takes
        # longer than the MAXIMUM_WORK_PERIOD_SECONDS, terminate the batch operation as timed out.
        batch_start_time = datetime.utcnow()

        current_start_datetime = start_datetime
        current_batch_size = timedelta(seconds=MINIMUM_RANGE_SIZE)

        while current_start_datetime < end_datetime:
            # Verify we haven't been working for too long.
            work_elapsed = datetime.utcnow() - batch_start_time
            if max_query_time is not None and work_elapsed > max_query_time:
                logger.error(
                    "Retrieval of logs `%s/%s` timed out with time of `%s`",
                    namespace_id,
                    repository_id,
                    work_elapsed,
                )
                raise LogsIterationTimeout()

            current_end_datetime = current_start_datetime + current_batch_size
            current_end_datetime = min(current_end_datetime, end_datetime)

            # Load the next set of logs.
            def load_logs():
                logger.debug(
                    "Retrieving logs over range %s -> %s with namespace %s and repository %s",
                    current_start_datetime,
                    current_end_datetime,
                    namespace_id,
                    repository_id,
                )

                logs_query = model.log.get_logs_query(
                    namespace_id=namespace_id,
                    repository=repository_id,
                    start_time=current_start_datetime,
                    end_time=current_end_datetime,
                )
                logs = list(logs_query)
                for log in logs:
                    assert isinstance(log, BaseModel)
                    if namespace_id is not None:
                        assert log.account_id == namespace_id, "Expected %s, Found: %s" % (
                            namespace_id,
                            log.account.id,
                        )

                    if repository_id is not None:
                        assert log.repository_id == repository_id

                logs = [Log.for_logentry(log) for log in logs]
                return logs

            logs, elapsed = _run_and_time(load_logs)
            if max_query_time is not None and elapsed > max_query_time:
                logger.error(
                    "Retrieval of logs for export `%s/%s` with range `%s-%s` timed out at `%s`",
                    namespace_id,
                    repository_id,
                    current_start_datetime,
                    current_end_datetime,
                    elapsed,
                )
                raise LogsIterationTimeout()

            yield logs

            # Move forward.
            current_start_datetime = current_end_datetime

            # Increase the batch size if necessary.
            if len(logs) < EXPECTED_ITERATION_LOG_COUNT:
                seconds = min(MAXIMUM_RANGE_SIZE, current_batch_size.total_seconds() * 2)
                current_batch_size = timedelta(seconds=seconds)

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        """
        Yield a context manager for a group of outdated logs.
        """
        for log_model in LOG_MODELS:
            while True:
                with UseThenDisconnect(config.app_config):
                    start_id = get_stale_logs_start_id(log_model)

                    if start_id is None:
                        logger.warning("Failed to find start id")
                        break

                    logger.debug("Found starting ID %s", start_id)
                    lookup_end_id = start_id + min_logs_per_rotation
                    logs = [
                        log
                        for log in get_stale_logs(start_id, lookup_end_id, log_model, cutoff_date)
                    ]

                if not logs:
                    logger.debug("No further logs found")
                    break

                end_id = max([log.id for log in logs])
                context = DatabaseLogRotationContext(logs, log_model, start_id, end_id)
                yield context


def _run_and_time(fn):
    start_time = datetime.utcnow()
    result = fn()
    return result, datetime.utcnow() - start_time


table_logs_model = TableLogsModel()


class DatabaseLogRotationContext(LogRotationContextInterface):
    """
    DatabaseLogRotationContext represents a batch of logs to be archived together. i.e A set of logs
    to be archived in the same file (based on the number of logs per rotation).

    When completed without exceptions, this context will delete the stale logs from rows `start_id`
    to `end_id`.
    """

    def __init__(self, logs, log_model, start_id, end_id):
        self.logs = logs
        self.log_model = log_model
        self.start_id = start_id
        self.end_id = end_id

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type is None and ex_value is None and ex_traceback is None:
            with UseThenDisconnect(config.app_config):
                logger.debug("Deleting logs from IDs %s to %s", self.start_id, self.end_id)
                delete_stale_logs(self.start_id, self.end_id, self.log_model)

    def yield_logs_batch(self):
        """
        Yield a batch of logs and a filename for that batch.
        """
        filename = "%d-%d-%s.txt.gz" % (self.start_id, self.end_id, self.log_model.__name__.lower())
        yield self.logs, filename
