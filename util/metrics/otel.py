from functools import wraps

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

import features


def init_exporter(app_config):

    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    DT_API_URL = otel_config.get("dt_api_url", None)
    DT_API_TOKEN = otel_config.get("dt_api_token", None)

    resource = Resource.create(attributes={SERVICE_NAME: service_name})

    tracerProvider = TracerProvider(resource=resource)

    if DT_API_URL is not None and DT_API_TOKEN is not None:
        spanExporter = BatchSpanProcessor(
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
    Decorator for tracing functino calls using OpenTelemetry.
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
