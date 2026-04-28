from unittest.mock import patch

import pytest

from util.metrics.otel import init_exporter


@pytest.mark.parametrize(
    "sample_rate, expected",
    [
        (0.5, 0.5),
        (1, 1.0),
        (0, 0.0),
        (1 / 1000, 1 / 1000),
        ("invalid", 1 / 1000),
        (-0.1, 1 / 1000),
        (1.5, 1 / 1000),
        (None, 1 / 1000),
    ],
)
@patch("util.metrics.otel.trace")
@patch("util.metrics.otel.BatchSpanProcessor")
@patch("util.metrics.otel.OTLPSpanExporter")
def test_init_exporter_sample_rate(
    mock_exporter, mock_processor, mock_trace, sample_rate, expected
):
    config = {"OTEL_CONFIG": {"sample_rate": sample_rate}}
    init_exporter(config)

    tracer_provider = mock_trace.set_tracer_provider.call_args[0][0]
    sampler = tracer_provider.sampler
    assert sampler.rate == expected


@patch("util.metrics.otel.trace")
@patch("util.metrics.otel.BatchSpanProcessor")
@patch("util.metrics.otel.OTLPSpanExporter")
def test_init_exporter_default_endpoint(mock_exporter, mock_processor, mock_trace):
    init_exporter({})
    mock_exporter.assert_called_once_with(endpoint="http://jaeger:4318/v1/traces")


@patch("util.metrics.otel.trace")
@patch("util.metrics.otel.BatchSpanProcessor")
@patch("util.metrics.otel.OTLPSpanExporter")
def test_init_exporter_custom_endpoint(mock_exporter, mock_processor, mock_trace):
    config = {"OTEL_CONFIG": {"endpoint": "http://collector:4318/v1/traces"}}
    init_exporter(config)
    mock_exporter.assert_called_once_with(endpoint="http://collector:4318/v1/traces")
