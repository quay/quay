import logging
import itertools

from data.logs_model.datatypes import AggregatedLogCount, LogEntriesPage
from data.logs_model.interface import ActionLogsDataInterface
from data.logs_model.shared import SharedModel

logger = logging.getLogger(__name__)


def _merge_aggregated_log_counts(*args):
    """
    Merge two lists of AggregatedLogCount based on the value of their kind_id and datetime.
    """
    matching_keys = {}
    aggregated_log_counts_list = itertools.chain.from_iterable(args)

    def canonical_key_from_kind_date_tuple(kind_id, dt):
        """
        Return a comma separated key from an AggregatedLogCount's kind_id and datetime.
        """
        return str(kind_id) + "," + str(dt)

    for kind_id, count, dt in aggregated_log_counts_list:
        kind_date_key = canonical_key_from_kind_date_tuple(kind_id, dt)
        if kind_date_key in matching_keys:
            existing_count = matching_keys[kind_date_key][2]
            matching_keys[kind_date_key] = (kind_id, dt, existing_count + count)
        else:
            matching_keys[kind_date_key] = (kind_id, dt, count)

    return [
        AggregatedLogCount(kind_id, count, dt)
        for (kind_id, dt, count) in list(matching_keys.values())
    ]


class CombinedLogsModel(SharedModel, ActionLogsDataInterface):
    """
    CombinedLogsModel implements the data model that logs to the first logs model and reads from
    both.
    """

    def __init__(self, read_write_logs_model, read_only_logs_model):
        self.read_write_logs_model = read_write_logs_model
        self.read_only_logs_model = read_only_logs_model

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
        return self.read_write_logs_model.log_action(
            kind_name,
            namespace_name,
            performer,
            ip,
            metadata,
            repository,
            repository_name,
            timestamp,
            is_free_namespace,
        )

    def count_repository_actions(self, repository, day):
        rw_count = self.read_write_logs_model.count_repository_actions(repository, day)
        ro_count = self.read_only_logs_model.count_repository_actions(repository, day)
        return rw_count + ro_count

    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ):
        rw_model = self.read_write_logs_model
        ro_model = self.read_only_logs_model
        rw_count = rw_model.get_aggregated_log_counts(
            start_datetime,
            end_datetime,
            performer_name=performer_name,
            repository_name=repository_name,
            namespace_name=namespace_name,
            filter_kinds=filter_kinds,
        )
        ro_count = ro_model.get_aggregated_log_counts(
            start_datetime,
            end_datetime,
            performer_name=performer_name,
            repository_name=repository_name,
            namespace_name=namespace_name,
            filter_kinds=filter_kinds,
        )
        return _merge_aggregated_log_counts(rw_count, ro_count)

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        rw_model = self.read_write_logs_model
        ro_model = self.read_only_logs_model
        rw_logs = rw_model.yield_logs_for_export(
            start_datetime, end_datetime, repository_id, namespace_id, max_query_time
        )
        ro_logs = ro_model.yield_logs_for_export(
            start_datetime, end_datetime, repository_id, namespace_id, max_query_time
        )
        for batch in itertools.chain(rw_logs, ro_logs):
            yield batch

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
        rw_model = self.read_write_logs_model
        ro_model = self.read_only_logs_model

        page_token = page_token or {}

        new_page_token = {}
        if page_token is None or not page_token.get("under_readonly_model", False):
            rw_page_token = page_token.get("readwrite_page_token")
            rw_logs = rw_model.lookup_logs(
                start_datetime,
                end_datetime,
                performer_name,
                repository_name,
                namespace_name,
                filter_kinds,
                rw_page_token,
                max_page_count,
            )
            logs, next_page_token = rw_logs
            new_page_token["under_readonly_model"] = next_page_token is None
            new_page_token["readwrite_page_token"] = next_page_token
            return LogEntriesPage(logs, new_page_token)
        else:
            readonly_page_token = page_token.get("readonly_page_token")
            ro_logs = ro_model.lookup_logs(
                start_datetime,
                end_datetime,
                performer_name,
                repository_name,
                namespace_name,
                filter_kinds,
                readonly_page_token,
                max_page_count,
            )
            logs, next_page_token = ro_logs
            if next_page_token is None:
                return LogEntriesPage(logs, None)

            new_page_token["under_readonly_model"] = True
            new_page_token["readonly_page_token"] = next_page_token
            return LogEntriesPage(logs, new_page_token)

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        latest_logs = []
        rw_model = self.read_write_logs_model
        ro_model = self.read_only_logs_model

        rw_logs = rw_model.lookup_latest_logs(
            performer_name, repository_name, namespace_name, filter_kinds, size
        )
        latest_logs.extend(rw_logs)
        if len(latest_logs) < size:
            ro_logs = ro_model.lookup_latest_logs(
                performer_name,
                repository_name,
                namespace_name,
                filter_kinds,
                size - len(latest_logs),
            )
            latest_logs.extend(ro_logs)

        return latest_logs

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        ro_model = self.read_only_logs_model
        rw_model = self.read_write_logs_model
        ro_ctx = ro_model.yield_log_rotation_context(cutoff_date, min_logs_per_rotation)
        rw_ctx = rw_model.yield_log_rotation_context(cutoff_date, min_logs_per_rotation)
        for ctx in itertools.chain(ro_ctx, rw_ctx):
            yield ctx
