import os
from functools import wraps
from urllib.parse import urlparse

import opentelemetry.sdk.trace.id_generator as idg
from flask import request
from opentelemetry import context, trace
from opentelemetry.context.context import Context
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as grpcOTLPSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as httpOTLPSpanExporter,
)
from opentelemetry.sdk.resources import (
    SERVICE_NAME,
    SERVICE_NAMESPACE,
    SERVICE_VERSION,
    Resource,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import NonRecordingSpan, Span, SpanContext
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace.status import StatusCode

import features
from _init import _get_version_number as get_quay_version


def init_exporter(app_config):

    otel_config = app_config.get("OTEL_CONFIG", {})

    service_name = otel_config.get("service_name", "quay")
    service_namespace = os.environ.get("QE_K8S_NAMESPACE", "standalone")
    service_version = get_quay_version()
    # compile headers if present
    otel_headers = otel_config.get(
        "OTEL_EXPORTER_OTLP_HEADERS", otel_config.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS", {})
    )
    if otel_headers == {}:
        # accept Environ overwrites
        otel_headers = os.environ.get(
            "OTEL_EXPORTER_OTLP_HEADERS",
            os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS", ""),
        )
        # OTLP headers from environment are formatted as key=value,key2=value2
        # to ensure catching the format we
        # first need to split by comma ","
        # than split by equal "=" only once (example x-auth-sentry=sentry sentry_key=xxx)
        try:
            # will return a list of tuples [("x-auth-sentry", "sentry sentry_key=xxx"), ("x-tenant", "name")]
            # that we transform into a dict
            otel_headers = dict(
                list(map(lambda x: tuple(x.strip().split("=", 1)), otel_headers.strip().split(",")))
            )
        except ValueError:
            # if empty [('',)] we cannot form a dict out of the parser
            otel_headers = {}
    # according to https://opentelemetry.io/docs/specs/otel/protocol/exporter/#endpoint-urls-for-otlphttp
    # none signal specific configuration needs to append /v1/traces
    otel_endpoint = otel_config.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://127.0.0.1:80/v1/traces",
    )
    if not urlparse(otel_endpoint).path.endswith("/v1/traces"):
        otel_endpoint += "/v1/traces"

    if otel_endpoint == "http://127.0.0.1:80/v1/traces":
        # accept Environ overwrites
        # signal specific configuration needs to be unmodified
        otel_endpoint = os.environ.get(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", otel_endpoint),
        )
    otel_insecure = otel_config.get(
        "OTEL_EXPORTER_OTLP_INSECURE", otel_config.get("OTEL_EXPORTER_OTLP_TRACES_INSECURE", False)
    )
    if not otel_insecure:
        # accept Environ overwrites
        otel_insecure = bool(
            os.environ.get(
                "OTEL_EXPORTER_OTLP_INSECURE",
                os.environ.get("OTEL_EXPORTER_OTLP_TRACES_INSECURE", False),
            )
        )

    resource = Resource.create(
        attributes={
            SERVICE_NAME: service_name,
            SERVICE_NAMESPACE: service_namespace,
            SERVICE_VERSION: service_version,
        }
    )

    # according to https://opentelemetry.io/docs/specs/otel/protocol/exporter/#specify-protocol
    # http/protobuf should be the default and w should support grpc
    if otel_config.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http") == "grpc":
        OTLPSpanExporter = grpcOTLPSpanExporter
    elif otel_config.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http") in ("http", "http/protobuf"):
        OTLPSpanExporter = httpOTLPSpanExporter
    elif otel_config.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http") in ("http", "http/json"):
        # http/json is only may which is why we fallback to http/protobuf
        OTLPSpanExporter = httpOTLPSpanExporter

    # we should leave this to the collector to decide
    otel_sample_arg = float(otel_config.get("OTEL_TRACES_SAMPLER_ARG", 0.001))
    if otel_sample_arg == 0.001:
        # accept Environ overwrites
        otel_sample_arg = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", otel_sample_arg))

    sampler = TraceIdRatioBased(otel_sample_arg)
    tracerProvider = TracerProvider(resource=resource, sampler=sampler)

    processor = BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=otel_endpoint,
            headers=otel_headers,
        )
    )

    tracerProvider.add_span_processor(processor)
    trace.set_tracer_provider(tracerProvider)


def get_tracecontext(custom: str = "", headers: dict = {}) -> Context:
    # used to extract trace context from headers or generate one if empty
    # with a generated tracecontext that is inherited we do not generate multiple
    # trace contexts on methods that are not related/chained
    def create_random():
        while True:
            span_id = hex(idg.RandomIdGenerator().generate_span_id())
            if len(span_id) == 18:
                break
        return f"00-{hex(idg.RandomIdGenerator().generate_trace_id())[2:]}" + f"-{span_id[2:]}-01"

    if custom == "":
        carrier = {"traceparent": headers.get("traceparent", create_random())}
    else:
        carrier = {"traceparent": custom}
    ctx = TraceContextTextMapPropagator().extract(carrier)
    if ctx == {}:
        ctx = context.get_current()
    return ctx


def get_traceparent(_ctx) -> str:
    # used to output traceparent into logs
    try:
        span = _ctx.get(list(_ctx)[0]).get_span_context()
    except:
        try:
            span = _ctx.get_span_context()
        except:
            span = _ctx
    try:
        tp = f"00-{hex(span.trace_id)[2:]}-{hex(span.span_id)[2:]}-0{hex(span.trace_flags)[2:]}"
    except Exception as err:
        tp = ""
    return tp


def traced(span_name=None):
    """
    Decorator for tracing function calls using OpenTelemetry.
    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if features.OTEL_TRACING:
                ctx = get_tracecontext(request.headers)
                tracer = trace.get_tracer(__name__)
                name = span_name if span_name else func.__name__
                with tracer.start_as_current_span(name, context=ctx) as span:
                    try:
                        span.set_status(StatusCode.OK)
                        span.set_attribute("function", name)
                        span.set_attribute("args", str(args))
                        span.set_attribute("kwargs", str(kwargs))
                        return func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(StatusCode.ERROR)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorate
