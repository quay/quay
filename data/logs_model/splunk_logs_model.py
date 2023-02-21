import json
import logging

from datetime import datetime

from data import model
from data.logs_model.interface import ActionLogsDataInterface
from data.logs_model.logs_producer import LogProducerProxy, LogSendException
from data.logs_model.logs_producer.splunk_logs_producer import SplunkLogsProducer
from data.logs_model.shared import SharedModel
from data.model import config
from data.model.log import ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING

logger = logging.getLogger(__name__)


class SplunkLogsModel(SharedModel, ActionLogsDataInterface):
    """
    SplunkLogsModel implements model for establishing connection and sending events to Splunk cluster
    """

    def __init__(self, producer, splunk_config, should_skip_logging=None):
        self._should_skip_logging = should_skip_logging
        self._logs_producer = LogProducerProxy()
        if producer == "splunk":
            self._logs_producer.initialize(SplunkLogsProducer(**splunk_config))
        else:
            raise Exception("Invalid log producer: %s" % producer)

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
            if repository is None or namespace_name is not None:
                raise ValueError(
                    "Incorrect argument provided when logging action logs, namespace name should not be "
                    "empty"
                )
            repository = model.repository.get_repository(namespace_name, repository_name)

        if timestamp is None:
            timestamp = datetime.today()

        account_id = None
        performer_id = None
        repository_id = None

        if namespace_name is not None:
            ns_user = model.user.get_namespace_user(namespace_name)
            if ns_user is not None:
                account_id = ns_user.id

        if performer is not None:
            performer_id = performer.id

        if repository is not None:
            repository_id = repository.id

        kind_id = model.log._get_log_entry_kind(kind_name)

        metadata_json = metadata or {}

        log_data = {
            "kind": kind_id,
            "account": account_id,
            "performer": performer_id,
            "repository": repository_id,
            "ip": ip,
            "metadata_json": metadata_json or {},
            "datetime": timestamp,
        }

        try:
            self._logs_producer.send(json.dumps(log_data, sort_keys=True, default=str))
        except LogSendException as lse:
            strict_logging_disabled = config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
            logger.exception("log_action failed", extra=({"exception": lse}).update(log_data))
            if not (strict_logging_disabled and kind_name in ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING):
                raise

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
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")

    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")

    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ):
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")

    def count_repository_actions(self, repository, day):
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")

    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")

    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        raise NotImplementedError("Method not implemented, Splunk does not support log lookups")
