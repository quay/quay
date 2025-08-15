import opentelemetry.exporter.otlp.proto.grpc.trace_exporter
import opentelemetry.exporter.otlp.proto.http.trace_exporter
import pytest
from opentelemetry import context, trace

from util.metrics.otel import init_exporter

# check various configuration options
app_configs = [
    {
        "OTEL_CONFIG": {
            "service_name": "unittest",
            "OTEL_EXPORTER_OTLP_HEADERS": {
                "Authorization": "Api-Token abcdef",
                "Tenant-Id": "Tenant 1",
            },
            "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otlp.example.com",
            "OTEL_EXPORTER_OTLP_INSECURE": False,
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http",
            "OTEL_TRACES_SAMPLER_ARG": 0.005,
        },
        "FEATURE_ENABLE_OTEL": True,
    },
]


@pytest.fixture()
def test_otel_config():
    # since we can set tracer_provider only once, we go with the default one
    app.config["OTEL_CONFIG"] = app_configs[0]["OTEL_CONFIG"]
    app.config["FEATURE_OTEL_TRACING"] = True
    init_exporter(app)
    tracer = trace.get_tracer("unittest")
    assert tracer.sampler.rate == 0.005
    assert tracer.resource.attributes.get("service.name") == "unittest"
    assert tracer.resource.attributes.get("service.namespace") == "standalone"
    assert tracer.resource.attributes.get("service.version", False)
    # convert to dict so we do not need to differentiate between http/grpc headers
    assert (
        dict(tracer.span_processor._span_processors[0].span_exporter._headers).get("Authorization")
        == "Api-Token abcdef"
    )
    assert (
        dict(tracer.span_processor._span_processors[0].span_exporter._headers).get("Tenant-Id")
        == "Tenant 1"
    )

    # http exporter
    assert (
        tracer.span_processor._span_processors[0].span_exporter._endpoint
        == "https://otlp.example.com/v1/traces"
    )

    # grpc exporter
    # assert tracer.span_processor._span_processors[0].span_exporter._endpoint == "otlp.example.com"

    assert isinstance(
        tracer.span_processor._span_processors[0].span_exporter,
        opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter,
    )
    # assert isinstance(tracer.span_processor._span_processors[0].span_exporter, opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter)
