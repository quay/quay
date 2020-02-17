from abc import ABCMeta, abstractmethod
from six import add_metaclass


class LogsIterationTimeout(Exception):
    """
    Exception raised if logs iteration times out.
    """


@add_metaclass(ABCMeta)
class ActionLogsDataInterface(object):
    """
    Interface for code to work with the logs data model.

    The logs data model consists of all access for reading and writing action logs.
    """

    @abstractmethod
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
        """
        Looks up all logs between the start_datetime and end_datetime, filtered by performer (a
        user), repository or namespace.

        Note that one (and only one) of the three can be specified. Returns a LogEntriesPage.
        `filter_kinds`, if specified, is a set/list of the kinds of logs to filter out.
        """

    @abstractmethod
    def lookup_latest_logs(
        self,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
        size=20,
    ):
        """
        Looks up latest logs of a specific kind, filtered by performer (a user), repository or
        namespace.

        Note that one (and only one) of the three can be specified. Returns a list of `Log`.
        """

    @abstractmethod
    def get_aggregated_log_counts(
        self,
        start_datetime,
        end_datetime,
        performer_name=None,
        repository_name=None,
        namespace_name=None,
        filter_kinds=None,
    ):
        """
        Returns the aggregated count of logs, by kind, between the start_datetime and end_datetime,
        filtered by performer (a user), repository or namespace.

        Note that one (and only one) of the three can be specified. Returns a list of
        AggregatedLogCount.
        """

    @abstractmethod
    def count_repository_actions(self, repository, day):
        """
        Returns the total number of repository actions over the given day, in the given repository
        or None on error.
        """

    @abstractmethod
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
        """
        Queues logs between the start_datetime and end_time, filtered by a repository or namespace,
        for export to the specified URL and/or email address.

        Returns the ID of the export job queued or None if error.
        """

    @abstractmethod
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
        """
        Logs a single action as having taken place.
        """

    @abstractmethod
    def yield_logs_for_export(
        self,
        start_datetime,
        end_datetime,
        repository_id=None,
        namespace_id=None,
        max_query_time=None,
    ):
        """
        Returns an iterator that yields bundles of all logs found between the start_datetime and
        end_datetime, optionally filtered by the repository or namespace. This function should be
        used for any bulk lookup operations, and should be implemented by implementors to put
        minimal strain on the backing storage for large operations. If there was an error in setting
        up, returns None.

        If max_query_time is specified, each iteration that yields a log bundle will have its
        queries run with a maximum timeout of that specified, and, if any exceed that threshold,
        LogsIterationTimeout will be raised instead of returning the logs bundle.
        """

    @abstractmethod
    def yield_log_rotation_context(self, cutoff_date, min_logs_per_rotation):
        """
        A generator that yields contexts implementing the LogRotationContextInterface. Each context
        represents a set of logs to be archived and deleted once the context completes without
        exceptions.

        For database logs, the LogRotationContext abstracts over a set of rows. When the context
        finishes, its associated rows get deleted.

        For Elasticsearch logs, the LogRotationContext abstracts over indices. When the context
        finishes, its associated index gets deleted.
        """


@add_metaclass(ABCMeta)
class LogRotationContextInterface(object):
    """
    Interface for iterating over a set of logs to be archived.
    """

    @abstractmethod
    def yield_logs_batch(self):
        """
        Generator yielding batch of logs and a filename for that batch.

        A batch is a subset of the logs part of the context.
        """
