import json
import logging
from datetime import datetime

from data import model
from data.logs_model.interface import ActionLogsDataInterface
from data.logs_model.logs_producer import LogProducerProxy, LogSendException
from data.logs_model.logs_producer.splunk_hec_logs_producer import SplunkHECLogsProducer
from data.logs_model.logs_producer.splunk_logs_producer import SplunkLogsProducer
from data.logs_model.shared import SharedModel
from data.model import config
from data.model.log import ACTIONS_ALLOWED_WITHOUT_AUDIT_LOGGING

logger = logging.getLogger(__name__)


class SplunkLogsModel(SharedModel, ActionLogsDataInterface):
    """
    SplunkLogsModel implements model for establishing connection and sending events to Splunk cluster
    """

    def __init__(
        self, producer, splunk_config=None, splunk_hec_config=None, should_skip_logging=None
    ):
        self._should_skip_logging = should_skip_logging
        self._logs_producer = LogProducerProxy()
        if producer == "splunk":
            if splunk_config is None:
                raise Exception("splunk_config must be provided for 'splunk' producer")
            self._logs_producer.initialize(SplunkLogsProducer(**splunk_config))
        elif producer == "splunk_hec":
            if splunk_hec_config is None:
                raise Exception("splunk_hec_config must be provided for 'splunk_hec' producer")
            self._logs_producer.initialize(SplunkHECLogsProducer(**splunk_hec_config))
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

        log_data = {
            "kind": kind_name,
            "account": username,
            "performer": performer_name,
            "repository": repo_name,
            "ip": ip,
            "metadata_json": metadata_json or {},
            "datetime": timestamp,
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
