from functools import wraps

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

import features

# Service name is required for most backends

DT_API_URL = None
DT_API_TOKEN = None


def init_exporter():
    resource = Resource.create(attributes={SERVICE_NAME: "quay-mkok-dev"})

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


# decorator for tracing
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
