# pylint: disable=protected-access

import json
import logging
import uuid

from time import time
from datetime import timedelta, datetime, date
from dateutil.parser import parse as parse_datetime

from abc import ABCMeta, abstractmethod
from six import add_metaclass

from elasticsearch.exceptions import ConnectionTimeout, NotFoundError

from data import model
from data.database import CloseForLongOperation
from data.model import config
from data.model.log import (
    _json_serialize,
    ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING,
    DataModelException,
)
from data.logs_model.elastic_logs import LogEntry, configure_es
from data.logs_model.datatypes import Log, AggregatedLogCount, LogEntriesPage
from data.logs_model.interface import (
    ActionLogsDataInterface,
    LogRotationContextInterface,
    LogsIterationTimeout,
)
from data.logs_model.shared import SharedModel, epoch_ms

from data.logs_model.logs_producer import LogProducerProxy, LogSendException
from data.logs_model.logs_producer.kafka_logs_producer import KafkaLogsProducer
from data.logs_model.logs_producer.elasticsearch_logs_producer import ElasticsearchLogsProducer
from data.logs_model.logs_producer.kinesis_stream_logs_producer import KinesisStreamLogsProducer


logger = logging.getLogger(__name__)

PAGE_SIZE = 20
DEFAULT_RESULT_WINDOW = 5000
MAX_RESULT_WINDOW = 10000

# DATE_RANGE_LIMIT is to limit the query date time range to at most 1 month.
DATE_RANGE_LIMIT = 32

# Timeout for count_repository_actions
COUNT_REPOSITORY_ACTION_TIMEOUT = 30


def _date_range_descending(start_datetime, end_datetime, includes_end_datetime=False):
    """
    Generate the dates between `end_datetime` and `start_datetime`.

    If `includes_end_datetime` is set, the generator starts at `end_datetime`, otherwise, starts the
    generator at `end_datetime` minus 1 second.
    """
    assert end_datetime >= start_datetime
    start_date = start_datetime.date()

    if includes_end_datetime:
        current_date = end_datetime.date()
    else:
        current_date = (end_datetime - timedelta(seconds=1)).date()

    while current_date >= start_date:
        yield current_date
        current_date = current_date - timedelta(days=1)


def _date_range_in_single_index(dt1, dt2):
    """
    Determine whether a single index can be searched given a range of dates or datetimes. If date
    instances are given, difference should be 1 day.

    NOTE: dt2 is exclusive to the search result set.
    i.e. The date range is larger or equal to dt1 and strictly smaller than dt2
    """
    assert isinstance(dt1, date) and isinstance(dt2, date)

    dt = dt2 - dt1

    # Check if date or datetime
    if not isinstance(dt1, datetime) and not isinstance(dt2, datetime):
        return dt == timedelta(days=1)

    if dt < timedelta(days=1) and dt >= timedelta(days=0):
        return dt2.day == dt1.day

    # Check if datetime can be interpreted as a date: hour, minutes, seconds or microseconds set to 0
    if dt == timedelta(days=1):
        return dt1.hour == 0 and dt1.minute == 0 and dt1.second == 0 and dt1.microsecond == 0

    return False


def _for_elasticsearch_logs(logs, repository_id=None, namespace_id=None):
    namespace_ids = set()
    for log in logs:
        namespace_ids.add(log.account_id)
        namespace_ids.add(log.performer_id)
        assert namespace_id is None or log.account_id == namespace_id
        assert repository_id is None or log.repository_id == repository_id

    id_user_map = model.user.get_user_map_by_ids(namespace_ids)
    return [Log.for_elasticsearch_log(log, id_user_map) for log in logs]


def _random_id():
    """
    Generates a unique uuid4 string for the random_id field in LogEntry.

    It is used as tie-breaker for sorting logs based on datetime:
    https://www.elastic.co/guide/en/elasticsearch/reference/current/search-request-search-after.html
    """
    return str(uuid.uuid4())


@add_metaclass(ABCMeta)
class ElasticsearchLogsModelInterface(object):
    """
    Interface for Elasticsearch specific operations with the logs model.

    These operations are usually index based.
    """

    @abstractmethod
    def can_delete_index(self, index, cutoff_date):
        """
        Return whether the given index is older than the given cutoff date.
        """

    @abstractmethod
    def list_indices(self):
        """
        List the logs model's indices.
        """


class DocumentLogsModel(SharedModel, ActionLogsDataInterface, ElasticsearchLogsModelInterface):
    """
    DocumentLogsModel implements the data model for the logs API backed by an elasticsearch service.
    """

    def __init__(
        self, should_skip_logging=None, elasticsearch_config=None, producer=None, **kwargs
    ):
        self._should_skip_logging = should_skip_logging
        self._logs_producer = LogProducerProxy()
        self._es_client = configure_es(**elasticsearch_config)

        if producer == "kafka":
            kafka_config = kwargs["kafka_config"]
            self._logs_producer.initialize(KafkaLogsProducer(**kafka_config))
        elif producer == "elasticsearch":
            self._logs_producer.initialize(ElasticsearchLogsProducer())
        elif producer == "kinesis_stream":
            kinesis_stream_config = kwargs["kinesis_stream_config"]
            self._logs_producer.initialize(KinesisStreamLogsProducer(**kinesis_stream_config))
        else:
            raise Exception("Invalid log producer: %s" % producer)

    @staticmethod
    def _get_ids_by_names(repository_name, namespace_name, performer_name):
        """
        Retrieve repository/namespace/performer ids based on their names.

        throws DataModelException when the namespace_name does not match any user in the database.
        returns database ID or None if not exists.
        """
        repository_id = None
        account_id = None
        performer_id = None

        if repository_name and namespace_name:
            repository = model.repository.get_repository(namespace_name, repository_name)
            if repository:
                repository_id = repository.id
                account_id = repository.namespace_user.id

        if namespace_name and account_id is None:
            account = model.user.get_user_or_org(namespace_name)
            if account is None:
                raise DataModelException("Invalid namespace requested")

            account_id = account.id

        if performer_name:
            performer = model.user.get_user(performer_name)
            if performer:
                performer_id = performer.id

        return repository_id, account_id, performer_id

    def _base_query(
        self, performer_id=None, repository_id=None, account_id=None, filter_kinds=None, index=None
    ):
        if filter_kinds is not None:
            assert all(isinstance(kind_name, str) for kind_name in filter_kinds)

        if index is not None:
            search = LogEntry.search(index=index)
        else:
            search = LogEntry.search()

        if performer_id is not None:
            assert isinstance(performer_id, int)
            search = search.filter("term", performer_id=performer_id)

        if repository_id is not None:
            assert isinstance(repository_id, int)
            search = search.filter("term", repository_id=repository_id)

        if account_id is not None and repository_id is None:
            assert isinstance(account_id, int)
            search = search.filter("term", account_id=account_id)

        if filter_kinds is not None:
            kind_map = model.log.get_log_entry_kinds()
            ignore_ids = [kind_map[kind_name] for kind_name in filter_kinds]
            search = search.exclude("terms", kind_id=ignore_ids)

        return search

    def _base_query_date_range(
        self,
        start_datetime,
        end_datetime,
        performer_id,
        repository_id,
        account_id,
        filter_kinds,
        index=None,
    ):
        skip_datetime_check = False
        if _date_range_in_single_index(start_datetime, end_datetime):
            index = self._es_client.index_name(start_datetime)
            skip_datetime_check = self._es_client.index_exists(index)

        if index and (skip_datetime_check or self._es_client.index_exists(index)):
            search = self._base_query(
                performer_id, repository_id, account_id, filter_kinds, index=index
            )
        else:
            search = self._base_query(performer_id, repository_id, account_id, filter_kinds)

        if not skip_datetime_check:
            search = search.query("range", datetime={"gte": start_datetime, "lt": end_datetime})

        return search

    def _load_logs_for_day(
        self,
        logs_date,
        performer_id,
        repository_id,
        account_id,
        filter_kinds,
        after_datetime=None,
        after_random_id=None,
        size=PAGE_SIZE,
    ):
        index = self._es_client.index_name(logs_date)
        if not self._es_client.index_exists(index):
            return []

        search = self._base_query(
            performer_id, repository_id, account_id, filter_kinds, index=index
        )
        search = search.sort({"datetime": "desc"}, {"random_id.keyword": "desc"})
        search = search.extra(size=size)

        if after_datetime is not None and after_random_id is not None:
            after_datetime_epoch_ms = epoch_ms(after_datetime)
            search = search.extra(search_after=[after_datetime_epoch_ms, after_random_id])

        return search.execute()

    def _load_latest_logs(self, performer_id, repository_id, account_id, filter_kinds, size):
        """
        Return the latest logs from Elasticsearch.

        Look at indices up to theset logrotateworker threshold, or up to 30 days if not defined.
        """
        # Set the last index to check to be the logrotateworker threshold, or 30 days
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(days=DATE_RANGE_LIMIT)

        latest_logs = []
        for day in _date_range_descending(start_datetime, end_datetime, includes_end_datetime=True):
            try:
                logs = self._load_logs_for_day(
                    day, performer_id, repository_id, account_id, filter_kinds, size=size
                )
                latest_logs.extend(logs)
            except NotFoundError:
                continue

            if len(latest_logs) >= size:
                break

        return _for_elasticsearch_logs(latest_logs[:size], repository_id, account_id)

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
        assert start_datetime is not None and end_datetime is not None

        # Check for a valid combined model token when migrating online from a combined model
        if page_token is not None and page_token.get("readwrite_page_token") is not None:
            page_token = page_token.get("readwrite_page_token")

        if page_token is not None and max_page_count is not None:
            page_number = page_token.get("page_number")
            if page_number is not None and page_number + 1 > max_page_count:
                return LogEntriesPage([], None)

        repository_id, account_id, performer_id = DocumentLogsModel._get_ids_by_names(
            repository_name, namespace_name, performer_name
        )

        after_datetime = None
        after_random_id = None
        if page_token is not None:
            after_datetime = parse_datetime(page_token["datetime"])
            after_random_id = page_token["random_id"]

        if after_datetime is not None:
            if after_datetime < start_datetime:
                return LogEntriesPage([], None)
            end_datetime = min(end_datetime, after_datetime)

        all_logs = []

        with CloseForLongOperation(config.app_config):
            for current_date in _date_range_descending(start_datetime, end_datetime):
                try:
                    logs = self._load_logs_for_day(
                        current_date,
                        performer_id,
                        repository_id,
                        account_id,
                        filter_kinds,
                        after_datetime,
                        after_random_id,
                        size=PAGE_SIZE + 1,
                    )

                    all_logs.extend(logs)
                except NotFoundError:
                    continue

                if len(all_logs) > PAGE_SIZE:
                    break

        next_page_token = None
        all_logs = all_logs[0 : PAGE_SIZE + 1]

        if len(all_logs) == PAGE_SIZE + 1:
            # The last element in the response is used to check if there's more elements.
            # The second element in the response is used as the pagination token because search_after does
            # not include the exact match, and so the next page will start with the last element.
            # This keeps the behavior exactly the same as table_logs_model, so that
            # the caller can expect when a pagination token is non-empty, there must be
            # at least 1 log to be retrieved.
            next_page_token = {
                "datetime": all_logs[-2].datetime.isoformat(),
                "random_id": all_logs[-2].random_id,
                "page_number": page_token["page_number"] + 1 if page_token else 1,
            }

        return LogEntriesPage(
            _for_elasticsearch_logs(all_logs[:PAGE_SIZE], repository_id, account_id),
            next_page_token,
        )

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        repository_id, account_id, performer_id = DocumentLogsModel._get_ids_by_names(
            repository_name, namespace_name, performer_name
        )

        with CloseForLongOperation(config.app_config):
            latest_logs = self._load_latest_logs(
                performer_id, repository_id, account_id, filter_kinds, size
            )

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
        if end_datetime - start_datetime >= timedelta(days=DATE_RANGE_LIMIT):
            raise Exception("Cannot lookup aggregated logs over a period longer than a month")

        repository_id, account_id, performer_id = DocumentLogsModel._get_ids_by_names(
            repository_name, namespace_name, performer_name
        )

        with CloseForLongOperation(config.app_config):
            search = self._base_query_date_range(
                start_datetime, end_datetime, performer_id, repository_id, account_id, filter_kinds
            )
            search.aggs.bucket("by_id", "terms", field="kind_id").bucket(
                "by_date", "date_histogram", field="datetime", interval="day"
            )
            # es returns all buckets when size=0
            search = search.extra(size=0)
            resp = search.execute()

        if not resp.aggregations:
            return []

        counts = []
        by_id = resp.aggregations["by_id"]

        for id_bucket in by_id.buckets:
            for date_bucket in id_bucket.by_date.buckets:
                if date_bucket.doc_count > 0:
                    counts.append(
                        AggregatedLogCount(id_bucket.key, date_bucket.doc_count, date_bucket.key)
                    )

        return counts

    def count_repository_actions(self, repository, day):
        index = self._es_client.index_name(day)
        search = self._base_query_date_range(
            day, day + timedelta(days=1), None, repository.id, None, None, index=index
        )
        search = search.params(request_timeout=COUNT_REPOSITORY_ACTION_TIMEOUT)

        try:
            return search.count()
        except NotFoundError:
            return 0

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

        if timestamp is None:
            timestamp = datetime.today()

        account_id = None
        performer_id = None
        repository_id = None

        if namespace_name is not None:
            account_id = model.user.get_namespace_user(namespace_name).id

        if performer is not None:
            performer_id = performer.id

        if repository is not None:
            repository_id = repository.id

        kind_id = model.log._get_log_entry_kind(kind_name)
        log = LogEntry(
            random_id=_random_id(),
            kind_id=kind_id,
            account_id=account_id,
            performer_id=performer_id,
            ip=ip,
            metadata=metadata or {},
            repository_id=repository_id,
            datetime=timestamp,
        )

        try:
            self._logs_producer.send(log)
        except LogSendException as lse:
            strict_logging_disabled = config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
            logger.exception("log_action failed", extra=({"exception": lse}).update(log.to_dict()))
            if not (strict_logging_disabled and kind_name in ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING):
                raise

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        max_query_time = max_query_time.total_seconds() if max_query_time is not None else 300
        search = self._base_query_date_range(
            start_datetime, end_datetime, None, repository_id, namespace_id, None
        )

        def raise_on_timeout(batch_generator):
            start = time()
            for batch in batch_generator:
                elapsed = time() - start
                if elapsed > max_query_time:
                    logger.error(
                        "Retrieval of logs `%s/%s` timed out with time of `%s`",
                        namespace_id,
                        repository_id,
                        elapsed,
                    )
                    raise LogsIterationTimeout()

                yield batch
                start = time()

        def read_batch(scroll):
            batch = []
            for log in scroll:
                batch.append(log)
                if len(batch) == DEFAULT_RESULT_WINDOW:
                    yield _for_elasticsearch_logs(
                        batch, repository_id=repository_id, namespace_id=namespace_id
                    )
                    batch = []

            if batch:
                yield _for_elasticsearch_logs(
                    batch, repository_id=repository_id, namespace_id=namespace_id
                )

        search = search.params(size=DEFAULT_RESULT_WINDOW, request_timeout=max_query_time)

        try:
            with CloseForLongOperation(config.app_config):
                for batch in raise_on_timeout(read_batch(search.scan())):
                    yield batch
        except ConnectionTimeout:
            raise LogsIterationTimeout()

    def can_delete_index(self, index, cutoff_date):
        return self._es_client.can_delete_index(index, cutoff_date)

    def list_indices(self):
        return self._es_client.list_indices()

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        """
        Yield a context manager for a group of outdated logs.
        """
        all_indices = self.list_indices()
        for index in all_indices:
            if not self.can_delete_index(index, cutoff_date):
                continue

            context = ElasticsearchLogRotationContext(index, min_logs_per_rotation, self._es_client)
            yield context


class ElasticsearchLogRotationContext(LogRotationContextInterface):
    """
    ElasticsearchLogRotationContext yield batch of logs from an index.

    When completed without exceptions, this context will delete its associated Elasticsearch index.
    """

    def __init__(self, index, min_logs_per_rotation, es_client):
        self._es_client = es_client
        self.min_logs_per_rotation = min_logs_per_rotation
        self.index = index

        self.start_pos = 0
        self.end_pos = 0

        self.scroll = None

    def __enter__(self):
        search = self._base_query()
        self.scroll = search.scan()
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type is None and ex_value is None and ex_traceback is None:
            logger.debug("Deleting index %s", self.index)
            self._es_client.delete_index(self.index)

    def yield_logs_batch(self):
        def batched_logs(gen, size):
            batch = []
            for log in gen:
                batch.append(log)
                if len(batch) == size:
                    yield batch
                    batch = []

            if batch:
                yield batch

        for batch in batched_logs(self.scroll, self.min_logs_per_rotation):
            self.end_pos = self.start_pos + len(batch) - 1
            yield batch, self._generate_filename()
            self.start_pos = self.end_pos + 1

    def _base_query(self):
        search = LogEntry.search(index=self.index)
        return search

    def _generate_filename(self):
        """
        Generate the filenames used to archive the action logs.
        """
        filename = "%s_%d-%d" % (self.index, self.start_pos, self.end_pos)
        filename = ".".join((filename, "txt.gz"))
        return filename
