from abc import ABCMeta, abstractmethod
from six import add_metaclass
from functools import partial, wraps

from prometheus_client import CollectorRegistry, Gauge, Counter, push_to_gateway

from util.abchelpers import nooper


@add_metaclass(ABCMeta)
class ProgressReporter(object):
    """
    Implements an interface for reporting progress with the migrations.
    """

    @abstractmethod
    def report_version_complete(self, success):
        """
        Called when an entire migration is complete.
        """

    @abstractmethod
    def report_step_progress(self):
        """
        Called when a single step in the migration has been completed.
        """


@nooper
class NullReporter(ProgressReporter):
    """
    No-op version of the progress reporter, designed for use when no progress reporting endpoint is
    provided.
    """


class PrometheusReporter(ProgressReporter):
    def __init__(self, prom_pushgateway_addr, prom_job, labels, total_steps_num=None):
        self._total_steps_num = total_steps_num
        self._completed_steps = 0.0

        registry = CollectorRegistry()

        self._migration_completion_percent = Gauge(
            "migration_completion_percent",
            "Estimate of the completion percentage of the job",
            registry=registry,
        )
        self._migration_complete_total = Counter(
            "migration_complete_total",
            "Binary value of whether or not the job is complete",
            registry=registry,
        )
        self._migration_failed_total = Counter(
            "migration_failed_total",
            "Binary value of whether or not the job has failed",
            registry=registry,
        )
        self._migration_items_completed_total = Counter(
            "migration_items_completed_total",
            "Number of items this migration has completed",
            registry=registry,
        )

        self._push = partial(
            push_to_gateway,
            prom_pushgateway_addr,
            job=prom_job,
            registry=registry,
            grouping_key=labels,
        )

    def report_version_complete(self, success=True):
        if success:
            self._migration_complete_total.inc()
        else:
            self._migration_failed_total.inc()
            self._migration_completion_percent.set(1.0)

        self._push()

    def report_step_progress(self):
        self._migration_items_completed_total.inc()

        if self._total_steps_num is not None:
            self._completed_steps += 1
            self._migration_completion_percent = self._completed_steps / self._total_steps_num

        self._push()


class ProgressWrapper(object):
    def __init__(self, delegate_module, progress_monitor):
        self._delegate_module = delegate_module
        self._progress_monitor = progress_monitor

    def __getattr__(self, attr_name):
        # Will raise proper attribute error
        maybe_callable = self._delegate_module.__dict__[attr_name]
        if callable(maybe_callable):
            # Build a callable which when executed places the request
            # onto a queue
            @wraps(maybe_callable)
            def wrapped_method(*args, **kwargs):
                result = maybe_callable(*args, **kwargs)
                self._progress_monitor.report_step_progress()
                return result

            return wrapped_method
        return maybe_callable
