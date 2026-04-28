import logging
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


def _patch_gevent_thread_cleanup():
    """
    Under gevent monkey-patching, BatchSpanProcessor's daemon thread becomes
    a greenlet.  When it terminates, threading._delete() raises KeyError
    because the greenlet ID was never registered in threading._active.
    Patch Thread._delete to suppress that KeyError.

    Guarded: only applies when gevent has monkey-patched threading.
    Idempotent: a marker attribute prevents re-wrapping on repeated calls.
    """
    if getattr(threading.Thread._delete, "_quay_gevent_patched", False):
        return

    try:
        from gevent import monkey
    except ImportError:
        return

    if not monkey.is_module_patched("threading"):
        return

    original = threading.Thread._delete

    def _safe_delete(self):
        try:
            original(self)
        except KeyError:
            logger.debug("Suppressed KeyError in Thread._delete (likely gevent greenlet)")

    _safe_delete._quay_gevent_patched = True
    threading.Thread._delete = _safe_delete


def init_exporter(app_config):

    _patch_gevent_thread_cleanup()

    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    DT_API_URL = otel_config.get("dt_api_url", None)
    DT_API_TOKEN = otel_config.get("dt_api_token", None)

    resource = Resource.create(attributes={SERVICE_NAME: service_name})

    sampler = TraceIdRatioBased(1 / 1000)
    tracerProvider = TracerProvider(resource=resource, sampler=sampler)

    if DT_API_URL is not None and DT_API_TOKEN is not None:
        processor = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=DT_API_URL + "/v1/traces",
                headers={"Authorization": "Api-Token " + DT_API_TOKEN},
            )
        )
    else:
        spanExporter = OTLPSpanExporter(endpoint="http://jaeger:4317")
        processor = BatchSpanProcessor(spanExporter)

    tracerProvider.add_span_processor(processor)
    trace.set_tracer_provider(tracerProvider)


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
