import json
import logging
import time
from datetime import datetime, timedelta
from typing import Generator, List, Optional

from data import model
from data.logs_model.datatypes import AggregatedLogCount, Log, LogEntriesPage
from data.logs_model.interface import ActionLogsDataInterface, LogsIterationTimeout
from data.logs_model.logs_producer import LogProducerProxy, LogSendException
from data.logs_model.logs_producer.splunk_hec_logs_producer import SplunkHECLogsProducer
from data.logs_model.logs_producer.splunk_logs_producer import SplunkLogsProducer
from data.logs_model.shared import InvalidLogsDateRangeError, SharedModel
from data.logs_model.splunk_field_mapper import SplunkLogMapper
from data.logs_model.splunk_search_client import SplunkSearchClient
from data.model import config
from data.model.log import ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING

logger = logging.getLogger(__name__)


def _escape_spl_value(value: Optional[str]) -> Optional[str]:
    """
    Escape special characters in a value for safe use in SPL queries.

    Prevents SPL injection by escaping backslashes and double quotes
    before interpolating user-supplied values into SPL strings.

    Args:
        value: The string value to escape

    Returns:
        The escaped string safe for use in SPL double-quoted strings
    """
    if value is None:
        return value
    # Escape backslashes first (before they're used in other escapes)
    value = value.replace("\\", "\\\\")
    # Escape double quotes
    value = value.replace('"', '\\"')
    return value


class SplunkLogsModel(SharedModel, ActionLogsDataInterface):
    """
    SplunkLogsModel implements model for establishing connection and sending events to Splunk cluster.

    Supports both writing logs (via SplunkLogsProducer or SplunkHECLogsProducer) and reading logs
    (via SplunkSearchClient and SplunkLogMapper).
    """

    def __init__(
        self, producer, splunk_config=None, splunk_hec_config=None, should_skip_logging=None
    ):
        self._should_skip_logging = should_skip_logging
        self._logs_producer = LogProducerProxy()
        self._search_client: Optional[SplunkSearchClient] = None
        self._field_mapper: Optional[SplunkLogMapper] = None
        self._splunk_config = splunk_config
        self._splunk_hec_config = splunk_hec_config
        self._producer = producer

        if producer == "splunk":
            if splunk_config is None:
                raise Exception("splunk_config must be provided for 'splunk' producer")
            self._logs_producer.initialize(SplunkLogsProducer(**splunk_config))
            self._field_mapper = SplunkLogMapper()
        elif producer == "splunk_hec":
            if splunk_hec_config is None:
                raise Exception("splunk_hec_config must be provided for 'splunk_hec' producer")
            if "search_token" not in splunk_hec_config:
                raise Exception(
                    "search_token is required in splunk_hec_config. "
                    "HEC tokens are ingest-only and cannot be used for searching. "
                    "See: https://docs.splunk.com/Documentation/SplunkCloud/latest/Config/ManageHECtokens"
                )
            self._logs_producer.initialize(SplunkHECLogsProducer(**splunk_hec_config))
            self._field_mapper = SplunkLogMapper()
        else:
            raise Exception("Invalid log producer: %s" % producer)

    def _get_search_client(self) -> SplunkSearchClient:
        """
        Get or create the Splunk search client.

        For 'splunk' producer, uses splunk_config directly.
        For 'splunk_hec' producer, builds search config from HEC config,
        using search_token (required) and optionally search_host/search_port.

        Returns:
            SplunkSearchClient instance

        Raises:
            Exception: If no valid config is available
        """
        if self._search_client is not None:
            return self._search_client

        if self._producer == "splunk" and self._splunk_config is not None:
            self._search_client = SplunkSearchClient(**self._splunk_config)
        elif self._producer == "splunk_hec" and self._splunk_hec_config is not None:
            # Build search client config from HEC config
            # search_token is required (validated in __init__) because HEC tokens cannot search
            hec_config = self._splunk_hec_config
            search_config = {
                "host": hec_config.get("search_host", hec_config.get("host")),
                "port": hec_config.get("search_port", 8089),
                "bearer_token": hec_config["search_token"],
                "url_scheme": hec_config.get("url_scheme", "https"),
                "verify_ssl": hec_config.get("verify_ssl", True),
                "ssl_ca_path": hec_config.get("ssl_ca_path"),
                "index_prefix": hec_config.get("index"),
                "search_timeout": hec_config.get("search_timeout", 60),
                "max_results": hec_config.get("max_results", 10000),
            }
            self._search_client = SplunkSearchClient(**search_config)
        else:
            raise Exception("Splunk search requires splunk_config or splunk_hec_config")

        return self._search_client

    def _get_field_mapper(self) -> SplunkLogMapper:
        """
        Get the field mapper instance.

        Returns:
            SplunkLogMapper instance
        """
        if self._field_mapper is None:
            self._field_mapper = SplunkLogMapper()
        return self._field_mapper

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
        # Enhanced logging fields for ESS EOI compliance
        request_url=None,
        http_method=None,
        auth_type=None,
        user_agent=None,
        performer_kind=None,
        request_id=None,
        x_forwarded_for=None,
    ):

        if self._should_skip_logging and self._should_skip_logging(
            kind_name, namespace_name, is_free_namespace
        ):
            return

        if repository_name is not None:
            if repository is not None or namespace_name is None:
                raise ValueError(
                    "Incorrect argument provided when logging action logs, namespace name should not be "
                    "empty"
                )
            repository = model.repository.get_repository(namespace_name, repository_name)

        if timestamp is None:
            timestamp = datetime.today()

        username = None
        performer_name = None
        repo_name = None

        if namespace_name is not None:
            ns_user = model.user.get_namespace_user(namespace_name)
            if ns_user is not None:
                username = ns_user.username

        if performer is not None and performer.username:
            performer_name = performer.username

        if repository is not None and repository.name:
            repo_name = repository.name

        metadata_json = metadata or {}

        # Get performer email if available
        performer_email = None
        if performer is not None:
            performer_email = getattr(performer, "email", None)

        log_data = {
            "kind": kind_name,
            "account": username,
            "performer": performer_name,
            "repository": repo_name,
            "ip": ip,
            "metadata_json": metadata_json or {},
            "datetime": timestamp,
            # Enhanced logging fields for ESS EOI compliance
            "request_url": request_url,
            "http_method": http_method,
            "performer_username": performer_name,
            "performer_email": performer_email,
            "performer_kind": performer_kind,
            "auth_type": auth_type,
            "user_agent": user_agent,
            "namespace_name": namespace_name,
            "repository_name": repo_name,
            "request_id": request_id,
            "x_forwarded_for": x_forwarded_for,
        }

        try:
            self._logs_producer.send(log_data)
        except LogSendException as lse:
            strict_logging_disabled = config.app_config.get("ALLOW_WITHOUT_STRICT_LOGGING") or (
                config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
                and kind_name in ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING
            )
            if strict_logging_disabled:
                logger.exception("log_action failed", extra=({"exception": lse}).update(log_data))
            else:
                raise

    def _build_base_query(
        self,
        namespace_name=None,
        performer_name=None,
        repository_name=None,
        filter_kinds=None,
    ) -> str:
        """Build base SPL query string with filters.

        All user-supplied values are escaped to prevent SPL injection.
        """
        parts = []

        if namespace_name:
            escaped = _escape_spl_value(namespace_name)
            parts.append(f'account="{escaped}"')
        if performer_name:
            escaped = _escape_spl_value(performer_name)
            parts.append(f'performer="{escaped}"')
        if repository_name:
            escaped = _escape_spl_value(repository_name)
            parts.append(f'repository="{escaped}"')
        if filter_kinds:
            for kind_name in filter_kinds:
                escaped = _escape_spl_value(kind_name)
                parts.append(f'kind!="{escaped}"')

        return " ".join(parts)

    def _build_lookup_query(self, **kwargs) -> str:
        """Build SPL query for log lookups with sorting."""
        base = self._build_base_query(**kwargs)
        return f"{base} | sort -_time" if base else "| sort -_time"

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
    ) -> LogEntriesPage:
        """Retrieve paginated logs from Splunk within the specified date range."""
        PAGE_SIZE = 20

        if start_datetime is None or end_datetime is None:
            raise ValueError("start_datetime and end_datetime are required")

        # Handle combined model token format
        if page_token is not None and page_token.get("readwrite_page_token") is not None:
            page_token = page_token.get("readwrite_page_token")

        # Handle page limit
        if page_token is not None and max_page_count is not None:
            page_number = page_token.get("page_number", 0)
            if page_number + 1 > max_page_count:
                return LogEntriesPage([], None)

        # Build SPL query with filters
        spl_query = self._build_lookup_query(
            namespace_name=namespace_name,
            performer_name=performer_name,
            repository_name=repository_name,
            filter_kinds=filter_kinds,
        )

        # Calculate offset from page token
        offset = page_token.get("offset", 0) if page_token else 0

        # Execute search with pagination
        search_client = self._get_search_client()
        results = search_client.search(
            query=spl_query,
            earliest_time=start_datetime.isoformat(),
            latest_time=end_datetime.isoformat(),
            max_count=PAGE_SIZE + 1,
            offset=offset,
        )

        # Map results to Log objects
        field_mapper = self._get_field_mapper()
        logs = field_mapper.map_logs(results.results[:PAGE_SIZE], namespace_name=namespace_name)

        # Build next page token if more results exist
        next_page_token = None
        if len(results.results) > PAGE_SIZE:
            next_page_token = {
                "offset": offset + PAGE_SIZE,
                "page_number": (page_token.get("page_number", 0) + 1) if page_token else 1,
            }

        return LogEntriesPage(logs, next_page_token)

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ) -> List[Log]:
        """Retrieve the most recent logs from Splunk (last 32 days)."""
        DATE_RANGE_LIMIT = 32

        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(days=DATE_RANGE_LIMIT)

        spl_query = self._build_lookup_query(
            namespace_name=namespace_name,
            performer_name=performer_name,
            repository_name=repository_name,
            filter_kinds=filter_kinds,
        )

        search_client = self._get_search_client()
        results = search_client.search(
            query=spl_query,
            earliest_time=start_datetime.isoformat(),
            latest_time=end_datetime.isoformat(),
            max_count=size,
            offset=0,
        )

        field_mapper = self._get_field_mapper()
        return field_mapper.map_logs(results.results, namespace_name=namespace_name)

    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ) -> List[AggregatedLogCount]:
        """Get aggregated log counts grouped by kind and date."""
        DATE_RANGE_LIMIT = 32

        if end_datetime - start_datetime > timedelta(days=DATE_RANGE_LIMIT):
            raise InvalidLogsDateRangeError(
                "Cannot lookup aggregated logs over a period longer than a month"
            )

        base_query = self._build_base_query(
            namespace_name=namespace_name,
            performer_name=performer_name,
            repository_name=repository_name,
            filter_kinds=filter_kinds,
        )

        # SPL aggregation query
        spl_query = (
            f"{base_query} "
            f'| eval log_date=strftime(_time, "%Y-%m-%d") '
            f"| stats count by kind, log_date"
        )

        search_client = self._get_search_client()
        results = search_client.search_with_stats(
            query=spl_query,
            earliest_time=start_datetime.isoformat(),
            latest_time=end_datetime.isoformat(),
        )

        kind_map = model.log.get_log_entry_kinds()
        counts = []

        for result in results:
            kind_name = result.get("kind")
            kind_id = kind_map.get(kind_name, 0) if kind_name else 0
            count = int(result.get("count", 0))
            log_date_str = result.get("log_date")
            if log_date_str:
                log_date = datetime.strptime(log_date_str, "%Y-%m-%d")
                counts.append(AggregatedLogCount(kind_id, count, log_date))

        return counts

    def count_repository_actions(self, repository, day) -> int:
        """Count audit log entries for a repository on a specific day."""
        COUNT_TIMEOUT = 30

        if isinstance(day, datetime):
            start_datetime = day.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_datetime = datetime.combine(day, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)

        repo_name = repository.name
        namespace_name = repository.namespace_user.username

        # Escape values to prevent SPL injection
        escaped_namespace = _escape_spl_value(namespace_name)
        escaped_repo = _escape_spl_value(repo_name)
        spl_query = f'account="{escaped_namespace}" repository="{escaped_repo}"'

        try:
            search_client = self._get_search_client()
            return search_client.count(
                query=spl_query,
                earliest_time=start_datetime.isoformat(),
                latest_time=end_datetime.isoformat(),
                timeout=COUNT_TIMEOUT,
            )
        except Exception as e:
            logger.warning("count_repository_actions failed: %s", e)
            return 0

    def _get_export_batch_size(self) -> int:
        """Get the export batch size from config, with default fallback."""
        DEFAULT_BATCH_SIZE = 5000
        if self._splunk_config:
            return self._splunk_config.get("export_batch_size", DEFAULT_BATCH_SIZE)
        elif self._splunk_hec_config:
            return self._splunk_hec_config.get("export_batch_size", DEFAULT_BATCH_SIZE)
        return DEFAULT_BATCH_SIZE

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ) -> Generator[List[Log], None, None]:
        """Yield batches of logs for export."""
        batch_size = self._get_export_batch_size()
        DEFAULT_MAX_QUERY_TIME = 300

        max_query_seconds = (
            max_query_time.total_seconds() if max_query_time else DEFAULT_MAX_QUERY_TIME
        )
        start_time = time.time()

        # Resolve IDs to names using existing model functions
        namespace_name = None
        repository_name = None

        if namespace_id:
            namespace_user = model.user.get_user_by_id(namespace_id)
            if namespace_user:
                namespace_name = namespace_user.username

        if repository_id:
            repository = model.repository.lookup_repository(repository_id)
            if repository:
                repository_name = repository.name
                if not namespace_name:
                    namespace_name = repository.namespace_user.username

        spl_query = self._build_base_query(
            namespace_name=namespace_name,
            repository_name=repository_name,
        )

        search_client = self._get_search_client()
        field_mapper = self._get_field_mapper()
        offset = 0

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_query_seconds:
                raise LogsIterationTimeout()

            results = search_client.search(
                query=spl_query,
                earliest_time=start_datetime.isoformat(),
                latest_time=end_datetime.isoformat(),
                max_count=batch_size,
                offset=offset,
            )

            if not results.results:
                break

            logs = field_mapper.map_logs(results.results, namespace_name=namespace_name)
            yield logs

            offset += len(results.results)
            if not results.has_more:
                break

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        """
        Splunk log rotation is handled by Splunk's retention policies.

        This method is not applicable for Splunk as log retention and cleanup
        are managed by Splunk's data management features.
        """
        # Splunk handles log rotation internally through retention policies
        # This is a no-op generator that yields nothing
        yield from []
