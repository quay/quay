"""
Tests for util/metrics/otel.py.

Validates that _patch_gevent_thread_cleanup() prevents the KeyError crash
when a greenlet-backed thread terminates under gevent monkey-patching,
and that init_exporter() still sets up the OTel pipeline correctly.
"""

import threading
from unittest.mock import patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from util.metrics.otel import _patch_gevent_thread_cleanup, init_exporter


@pytest.fixture(autouse=True)
def _reset_tracer_provider():
    """Reset the global OTel TracerProvider before each test."""
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

        # Simulate the gevent bug: calling _delete() when the thread ID
        # is not in threading._active should not raise.
        threading._active.pop(t.ident, None)
        t._delete()  # would raise KeyError without the patch

    def test_thread_delete_still_works_normally(self):
        _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t.start()
        t.join()

        # Normal _delete() on a thread that IS in _active should work fine.
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
        t._delete()  # should still not raise


class TestInitExporter:
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


class TestSpanExportPipeline:
    """Verify spans flow through the pipeline end-to-end."""

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
