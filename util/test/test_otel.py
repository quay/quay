import threading
from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

import util.metrics.otel as otel_module
from util.metrics.otel import (
    _patch_gevent_thread_cleanup,
    init_exporter,
    post_fork_init,
)


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


@pytest.fixture()
def _reset_tracer_provider():
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    yield
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False


class TestPatchGeventThreadCleanup:
    def test_thread_delete_suppresses_key_error(self):
        _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()

        threading._active.pop(t.ident, None)
        t._delete()

    def test_thread_delete_still_works_normally(self):
        _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()

        if t.ident in threading._active:
            t._delete()
        assert t.ident not in threading._active

    def test_patch_is_idempotent(self):
        _patch_gevent_thread_cleanup()
        _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()
        threading._active.pop(t.ident, None)
        t._delete()


class TestInitExporterProvider:
    @pytest.fixture(autouse=True)
    def reset(self, _reset_tracer_provider):
        pass

    def test_sets_tracer_provider(self):
        config = {"OTEL_CONFIG": {"service_name": "test-quay"}}
        init_exporter(config)

        provider = trace.get_tracer_provider()
        assert isinstance(provider, TracerProvider)

    def test_configures_dynatrace_exporter(self):
        config = {
            "OTEL_CONFIG": {
                "service_name": "test-quay",
                "dt_api_url": "https://dt.example.com/api/v2/otlp",
                "dt_api_token": "fake-token",
            }
        }
        with patch("util.metrics.otel.OTLPSpanExporter") as mock_cls:
            mock_cls.return_value = InMemorySpanExporter()
            init_exporter(config)

        mock_cls.assert_called_once_with(
            endpoint="https://dt.example.com/api/v2/otlp/v1/traces",
            headers={"Authorization": "Api-Token fake-token"},
        )

    def test_uses_batch_span_processor(self):
        config = {"OTEL_CONFIG": {"service_name": "test-quay"}}
        with patch("util.metrics.otel.OTLPSpanExporter", return_value=InMemorySpanExporter()):
            init_exporter(config)

        provider = trace.get_tracer_provider()
        processors = provider._active_span_processor._span_processors
        assert any(isinstance(p, BatchSpanProcessor) for p in processors)


class TestPreloadDeferral:
    @pytest.fixture(autouse=True)
    def reset(self, _reset_tracer_provider):
        otel_module._IS_PRELOAD = False
        otel_module._APP_CONFIG = None
        yield
        otel_module._IS_PRELOAD = False
        otel_module._APP_CONFIG = None

    @patch("util.metrics.otel.trace")
    @patch("util.metrics.otel.BatchSpanProcessor")
    @patch("util.metrics.otel.OTLPSpanExporter")
    def test_preload_defers_initialization(self, mock_exporter, mock_processor, mock_trace):
        config = {"OTEL_CONFIG": {"service_name": "test-quay"}}
        init_exporter(config, is_gunicorn_preload=True)

        mock_processor.assert_not_called()
        mock_trace.set_tracer_provider.assert_not_called()
        assert otel_module._APP_CONFIG is config

    @patch("util.metrics.otel.trace")
    @patch("util.metrics.otel.BatchSpanProcessor")
    @patch("util.metrics.otel.OTLPSpanExporter")
    def test_post_fork_init_creates_provider(self, mock_exporter, mock_processor, mock_trace):
        config = {"OTEL_CONFIG": {"service_name": "test-quay"}}
        init_exporter(config, is_gunicorn_preload=True)

        mock_processor.assert_not_called()

        post_fork_init()

        mock_processor.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once()

    def test_post_fork_init_noop_without_config(self):
        otel_module._APP_CONFIG = None
        post_fork_init()


class TestSpanExportPipeline:
    @pytest.fixture(autouse=True)
    def reset(self, _reset_tracer_provider):
        pass

    def test_span_exported_successfully(self):
        in_memory = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(in_memory))
        trace.set_tracer_provider(provider)

        _patch_gevent_thread_cleanup()

        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test.key", "test-value")

        provider.force_flush()

        exported = in_memory.get_finished_spans()
        assert len(exported) == 1
        assert exported[0].name == "test-span"
        assert exported[0].attributes["test.key"] == "test-value"
