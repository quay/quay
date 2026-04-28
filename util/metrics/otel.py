import logging
import os
import threading
from functools import wraps

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

import features

logger = logging.getLogger(__name__)

# Global flag to track whether we're running under gunicorn with preload
_IS_PRELOAD = False
# Cache the config so post_fork can access it
_APP_CONFIG = None


def _patch_gevent_thread_cleanup():
    """
    Under gevent monkey-patching, BatchSpanProcessor's daemon thread becomes
    a greenlet.  When it terminates, threading._delete() raises KeyError
    because the greenlet ID was never registered in threading._active.
    Patch Thread._delete to suppress that KeyError.
    """
    original = threading.Thread._delete

    def _safe_delete(self):
        try:
            original(self)
        except KeyError:
            logger.debug("Suppressed KeyError in Thread._delete (likely gevent greenlet)")

    threading.Thread._delete = _safe_delete


def _init_tracer_provider(app_config):
    """
    Initialize the OpenTelemetry TracerProvider with BatchSpanProcessor.

    IMPORTANT: This must be called AFTER fork when using gunicorn with preload_app.
    The BatchSpanProcessor spawns a background thread/greenlet that does not survive
    fork correctly, causing AssertionError in gevent's _notify_links.
    """
    _patch_gevent_thread_cleanup()

    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    DT_API_URL = otel_config.get("dt_api_url", None)
    DT_API_TOKEN = otel_config.get("dt_api_token", None)

    resource = Resource.create(attributes={SERVICE_NAME: service_name})

    sample_rate = otel_config.get("sample_rate", 1 / 1000)
    if not isinstance(sample_rate, (int, float)) or not 0.0 <= float(sample_rate) <= 1.0:
        sample_rate = 1 / 1000
    sampler = TraceIdRatioBased(float(sample_rate))
    tracerProvider = TracerProvider(resource=resource, sampler=sampler)

    if DT_API_URL is not None and DT_API_TOKEN is not None:
        processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=DT_API_URL + "/v1/traces",
                headers={"Authorization": "Api-Token " + DT_API_TOKEN},
            )
        )
    else:
        endpoint = otel_config.get("endpoint", "http://jaeger:4318/v1/traces")
        spanExporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(spanExporter)

    tracerProvider.add_span_processor(processor)
    trace.set_tracer_provider(tracerProvider)
    logger.debug("Initialized OpenTelemetry TracerProvider in PID %s", os.getpid())


def init_exporter(app_config, is_gunicorn_preload=False):
    """
    Initialize OpenTelemetry exporter.

    When running under gunicorn with preload_app=True, this defers actual
    initialization to the post_fork hook to avoid fork-safety issues with
    BatchSpanProcessor's background thread.

    Args:
        app_config: The application configuration dict
        is_gunicorn_preload: Set to True when called from app.py under gunicorn preload
    """
    global _IS_PRELOAD, _APP_CONFIG

    _APP_CONFIG = app_config

    if is_gunicorn_preload:
        # Running under gunicorn with preload_app=True
        # Defer initialization to post_fork hook
        _IS_PRELOAD = True
        logger.debug("Deferring OpenTelemetry initialization to post_fork hook")
        return

    # Not using preload (hotreload mode or non-gunicorn) - initialize now
    _init_tracer_provider(app_config)


def post_fork_init():
    """
    Called from gunicorn's post_fork hook to initialize OpenTelemetry in each worker.

    This ensures the BatchSpanProcessor's background thread is created in the
    worker process, not inherited from the pre-forked master.
    """
    global _APP_CONFIG

    if _APP_CONFIG is None:
        logger.warning("post_fork_init called but no app_config cached")
        return

    logger.debug("Initializing OpenTelemetry in worker PID %s", os.getpid())
    _init_tracer_provider(_APP_CONFIG)


def traced(span_name=None):
    """
    Decorator for tracing function calls using OpenTelemetry.
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if features.OTEL_TRACING:
                tracer = trace.get_tracer(__name__)
                name = span_name if span_name else func.__name__
                with tracer.start_as_current_span(name) as span:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR))
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorate
