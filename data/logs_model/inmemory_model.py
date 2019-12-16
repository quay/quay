import logging
import json

from collections import namedtuple
from datetime import datetime
from tzlocal import get_localzone
from dateutil.relativedelta import relativedelta

from data import model
from data.logs_model.datatypes import AggregatedLogCount, LogEntriesPage, Log
from data.logs_model.interface import (
    ActionLogsDataInterface,
    LogRotationContextInterface,
    LogsIterationTimeout,
)

logger = logging.getLogger(__name__)

LogAndRepository = namedtuple("LogAndRepository", ["log", "stored_log", "repository"])

StoredLog = namedtuple(
    "StoredLog",
    ["kind_id", "account_id", "performer_id", "ip", "metadata_json", "repository_id", "datetime"],
)


class InMemoryModel(ActionLogsDataInterface):
    """
    InMemoryModel implements the data model for logs in-memory.

    FOR TESTING ONLY.
    """

    def __init__(self):
        self.logs = []

    def _filter_logs(
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

        for log_and_repo in self.logs:
            if (
                log_and_repo.log.datetime < start_datetime
                or log_and_repo.log.datetime > end_datetime
            ):
                continue

            if performer_name and log_and_repo.log.performer_username != performer_name:
                continue

            if repository_name and (
                not log_and_repo.repository or log_and_repo.repository.name != repository_name
            ):
                continue

            if namespace_name and log_and_repo.log.account_username != namespace_name:
                continue

            if filter_kinds:
                kind_map = model.log.get_log_entry_kinds()
                ignore_ids = [kind_map[kind_name] for kind_name in filter_kinds]
                if log_and_repo.log.kind_id in ignore_ids:
                    continue

            yield log_and_repo

    def _filter_latest_logs(
        self, performer_name=None, repository_name=None, namespace_name=None, filter_kinds=None
    ):
        if filter_kinds is not None:
            assert all(isinstance(kind_name, str) for kind_name in filter_kinds)

        for log_and_repo in sorted(self.logs, key=lambda t: t.log.datetime, reverse=True):
            if performer_name and log_and_repo.log.performer_username != performer_name:
                continue

            if repository_name and (
                not log_and_repo.repository or log_and_repo.repository.name != repository_name
            ):
                continue

            if namespace_name and log_and_repo.log.account_username != namespace_name:
                continue

            if filter_kinds:
                kind_map = model.log.get_log_entry_kinds()
                ignore_ids = [kind_map[kind_name] for kind_name in filter_kinds]
                if log_and_repo.log.kind_id in ignore_ids:
                    continue

            yield log_and_repo

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
        logs = []
        for log_and_repo in self._filter_logs(
            start_datetime,
            end_datetime,
            performer_name,
            repository_name,
            namespace_name,
            filter_kinds,
        ):
            logs.append(log_and_repo.log)
        return LogEntriesPage(logs, None)

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        latest_logs = []
        for log_and_repo in self._filter_latest_logs(
            performer_name, repository_name, namespace_name, filter_kinds
        ):
            if size is not None and len(latest_logs) == size:
                break

            latest_logs.append(log_and_repo.log)

        return latest_logs

    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ):
        entries = {}
        for log_and_repo in self._filter_logs(
            start_datetime,
            end_datetime,
            performer_name,
            repository_name,
            namespace_name,
            filter_kinds,
        ):
            entry = log_and_repo.log
            synthetic_date = datetime(
                start_datetime.year,
                start_datetime.month,
                int(entry.datetime.day),
                tzinfo=get_localzone(),
            )
            if synthetic_date.day < start_datetime.day:
                synthetic_date = synthetic_date + relativedelta(months=1)

            key = "%s-%s" % (entry.kind_id, entry.datetime.day)

            if key in entries:
                entries[key] = AggregatedLogCount(
                    entry.kind_id, entries[key].count + 1, synthetic_date
                )
            else:
                entries[key] = AggregatedLogCount(entry.kind_id, 1, synthetic_date)

        return list(entries.values())

    def count_repository_actions(self, repository, day):
        count = 0
        for log_and_repo in self.logs:
            if log_and_repo.repository != repository:
                continue

            if log_and_repo.log.datetime.day != day.day:
                continue

            count += 1

        return count

    def queue_logs_export(
        self,
        start_datetime,
        end_datetime,
        export_action_logs_queue,
        namespace_name=None,
        repository_name=None,
        callback_url=None,
        callback_email=None,
        filter_kinds=None,
    ):
        raise NotImplementedError

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
        timestamp = timestamp or datetime.today()

        if not repository and repository_name and namespace_name:
            repository = model.repository.get_repository(namespace_name, repository_name)

        account = None
        account_id = None
        performer_id = None
        repository_id = None

        if namespace_name is not None:
            account = model.user.get_namespace_user(namespace_name)
            account_id = account.id

        if performer is not None:
            performer_id = performer.id

        if repository is not None:
            repository_id = repository.id

        metadata_json = json.dumps(metadata or {})
        kind_id = model.log.get_log_entry_kinds()[kind_name]

        stored_log = StoredLog(
            kind_id, account_id, performer_id, ip, metadata_json, repository_id, timestamp
        )

        log = Log(
            metadata_json=metadata,
            ip=ip,
            datetime=timestamp,
            performer_email=performer.email if performer else None,
            performer_username=performer.username if performer else None,
            performer_robot=performer.robot if performer else None,
            account_organization=account.organization if account else None,
            account_username=account.username if account else None,
            account_email=account.email if account else None,
            account_robot=account.robot if account else None,
            kind_id=kind_id,
        )

        self.logs.append(LogAndRepository(log, stored_log, repository))

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        # Just for testing.
        if max_query_time is not None:
            raise LogsIterationTimeout()

        logs = []
        for log_and_repo in self._filter_logs(start_datetime, end_datetime):
            if repository_id and (
                not log_and_repo.repository or log_and_repo.repository.id != repository_id
            ):
                continue

            if namespace_id:
                if log_and_repo.log.account_username is None:
                    continue

                namespace = model.user.get_namespace_user(log_and_repo.log.account_username)
                if namespace.id != namespace_id:
                    continue

            logs.append(log_and_repo.log)

        yield logs

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        expired_logs = [
            log_and_repo for log_and_repo in self.logs if log_and_repo.log.datetime <= cutoff_date
        ]
        while True:
            if not expired_logs:
                break
            context = InMemoryLogRotationContext(expired_logs[:min_logs_per_rotation], self.logs)
            expired_logs = expired_logs[min_logs_per_rotation:]
            yield context


class InMemoryLogRotationContext(LogRotationContextInterface):
    def __init__(self, expired_logs, all_logs):
        self.expired_logs = expired_logs
        self.all_logs = all_logs

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type is None and ex_value is None and ex_traceback is None:
            for log in self.expired_logs:
                self.all_logs.remove(log)

    def yield_logs_batch(self):
        """
        Yield a batch of logs and a filename for that batch.
        """
        filename = "inmemory_model_filename_placeholder"
        filename = ".".join((filename, "txt.gz"))
        yield [log_and_repo.stored_log for log_and_repo in self.expired_logs], filename
