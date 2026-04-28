"""
Tests for util/metrics/otel.py.

Validates that _patch_gevent_thread_cleanup() prevents the KeyError crash
when a greenlet-backed thread terminates under gevent monkey-patching,
and that init_exporter() still sets up the OTel pipeline correctly.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from util.metrics.otel import _patch_gevent_thread_cleanup, init_exporter


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset OTel TracerProvider and threading.Thread._delete between tests."""
    original_delete = threading.Thread._delete
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    yield
    threading.Thread._delete = original_delete
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE._done = False


class TestPatchGeventThreadCleanup:
    def _enable_patch(self):
        """Mock gevent.monkey.is_module_patched to return True so the guard passes."""
        mock_monkey = MagicMock()
        mock_monkey.is_module_patched.return_value = True
        return patch.dict("sys.modules", {"gevent": MagicMock(monkey=mock_monkey)})

    def test_suppresses_key_error(self):
        """When original _delete raises KeyError, the wrapper suppresses it."""
        original = threading.Thread._delete

        def _raise_key_error(self):
            raise KeyError(threading.get_ident())

        threading.Thread._delete = _raise_key_error

        with self._enable_patch():
            _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t._delete()  # should not raise

    def test_propagates_other_exceptions(self):
        """Non-KeyError exceptions are not suppressed."""
        original = threading.Thread._delete

        def _raise_runtime(self):
            raise RuntimeError("unexpected")

        threading.Thread._delete = _raise_runtime

        with self._enable_patch():
            _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        with pytest.raises(RuntimeError, match="unexpected"):
            t._delete()

    def test_calls_through_when_no_error(self):
        """When the original _delete succeeds, the wrapper calls it normally."""
        calls = []

        def _tracking_delete(self):
            calls.append(self)

        threading.Thread._delete = _tracking_delete

        with self._enable_patch():
            _patch_gevent_thread_cleanup()

        t = threading.Thread(target=lambda: None)
        t._delete()
        assert calls == [t]

    def test_idempotent(self):
        """Calling _patch_gevent_thread_cleanup multiple times doesn't re-wrap."""
        with self._enable_patch():
            _patch_gevent_thread_cleanup()
            first_delete = threading.Thread._delete

            _patch_gevent_thread_cleanup()
            assert threading.Thread._delete is first_delete

    def test_skips_when_gevent_not_installed(self):
        """When gevent is not importable, _delete is not patched."""
        original = threading.Thread._delete
        with patch.dict("sys.modules", {"gevent": None}):
            _patch_gevent_thread_cleanup()
        assert threading.Thread._delete is original

    def test_skips_when_threading_not_patched(self):
        """When gevent hasn't monkey-patched threading, _delete is not patched."""
        original = threading.Thread._delete
        mock_monkey = MagicMock()
        mock_monkey.is_module_patched.return_value = False
        with patch.dict("sys.modules", {"gevent": MagicMock(monkey=mock_monkey)}):
            _patch_gevent_thread_cleanup()
        assert threading.Thread._delete is original


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

        tracer = trace.get_tracer("test-tracer")
        with tracer.start_as_current_span("test-span") as span:
            span.set_attribute("test.key", "test-value")

        provider.force_flush()

        exported = in_memory.get_finished_spans()
        assert len(exported) == 1
        assert exported[0].name == "test-span"
        assert exported[0].attributes["test.key"] == "test-value"
