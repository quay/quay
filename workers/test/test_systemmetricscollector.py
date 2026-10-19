import os
import tempfile
import time
from unittest.mock import patch

import pytest

from workers.systemmetricscollector import (
    _build_registry,
    _push,
    _read_proc_net_unix,
    _sample,
)

PROC_HEADER = "Num       RefCount Protocol Flags    Type St Inode Path\n"

PROC_WITH_PENDING = PROC_HEADER + (
    "0000000092d0f433: 00000002 00000000 00010000 0001 01 1158022 /tmp/gunicorn_registry.sock\n"
    "00000000cd32b376: 00000002 00000000 00000000 0001 02      0 /tmp/gunicorn_registry.sock\n"
    "00000000a224bb9e: 00000002 00000000 00000000 0001 02      0 /tmp/gunicorn_registry.sock\n"
    "00000000f7fdc027: 00000002 00000000 00000000 0001 02      0 /tmp/gunicorn_registry.sock\n"
    "0000000056665bdb: 00000002 00000000 00000000 0001 03 1167596 /tmp/gunicorn_registry.sock\n"
    "00000000c06b969c: 00000002 00000000 00010000 0001 01 1139957 /tmp/gunicorn_web.sock\n"
    "00000000cd32b376: 00000002 00000000 00000000 0001 02      0 /tmp/gunicorn_web.sock\n"
)

PROC_EMPTY = PROC_HEADER + (
    "0000000092d0f433: 00000002 00000000 00010000 0001 01 1158022 /tmp/gunicorn_registry.sock\n"
    "00000000c06b969c: 00000002 00000000 00010000 0001 01 1139957 /tmp/gunicorn_web.sock\n"
    "0000000066df8c2b: 00000002 00000000 00010000 0001 01 1137220 /tmp/gunicorn_secscan.sock\n"
)

PROC_NO_GUNICORN = PROC_HEADER + (
    "00000000a1b2c3d4: 00000002 00000000 00010000 0001 01 999999 /tmp/other.sock\n"
)


def _write_tmp_proc(content):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    f.write(content)
    f.close()
    return f.name


class TestReadProcNetUnix:
    def test_counts_pending_connections(self):
        path = _write_tmp_proc(PROC_WITH_PENDING)
        try:
            result = _read_proc_net_unix(path)
            assert result["/tmp/gunicorn_registry.sock"]["pending"] == 3
            assert result["/tmp/gunicorn_web.sock"]["pending"] == 1
        finally:
            os.unlink(path)

    def test_counts_active_connections(self):
        path = _write_tmp_proc(PROC_WITH_PENDING)
        try:
            result = _read_proc_net_unix(path)
            assert result["/tmp/gunicorn_registry.sock"]["active"] == 1
            assert result["/tmp/gunicorn_web.sock"]["active"] == 0
        finally:
            os.unlink(path)

    def test_no_pending_connections(self):
        path = _write_tmp_proc(PROC_EMPTY)
        try:
            result = _read_proc_net_unix(path)
            assert result.get("/tmp/gunicorn_registry.sock", {}).get("pending", 0) == 0
            assert result.get("/tmp/gunicorn_web.sock", {}).get("pending", 0) == 0
        finally:
            os.unlink(path)

    def test_no_gunicorn_sockets(self):
        path = _write_tmp_proc(PROC_NO_GUNICORN)
        try:
            result = _read_proc_net_unix(path)
            assert "/tmp/gunicorn_registry.sock" not in result
        finally:
            os.unlink(path)

    def test_unreadable_file_raises(self):
        with pytest.raises(OSError):
            _read_proc_net_unix("/nonexistent/proc/net/unix")

    def test_header_only_returns_empty(self):
        path = _write_tmp_proc(PROC_HEADER)
        try:
            result = _read_proc_net_unix(path)
            assert result == {}
        finally:
            os.unlink(path)


class TestBuildRegistry:
    def test_creates_all_metrics(self):
        registry, metrics, hostname = _build_registry()
        expected = [
            "queue_depth",
            "queue_depth_hist",
            "active_connections",
            "socket_present",
            "collector_errors",
            "last_sample_timestamp",
        ]
        for name in expected:
            assert name in metrics

    def test_hostname_is_set(self):
        _, _, hostname = _build_registry()
        assert hostname and len(hostname) > 0


class TestSample:
    @patch("workers.systemmetricscollector._read_proc_net_unix")
    @patch("workers.systemmetricscollector.os.path.exists")
    def test_sets_queue_depth(self, mock_exists, mock_read):
        mock_exists.return_value = True
        mock_read.return_value = {
            "/tmp/gunicorn_registry.sock": {"pending": 5, "active": 2},
            "/tmp/gunicorn_web.sock": {"pending": 0, "active": 1},
        }
        _, metrics, hostname = _build_registry()

        _sample(metrics, hostname)

        assert metrics["queue_depth"].labels(host=hostname, socket="registry")._value.get() == 5.0
        assert metrics["queue_depth"].labels(host=hostname, socket="web")._value.get() == 0.0

    @patch("workers.systemmetricscollector._read_proc_net_unix")
    @patch("workers.systemmetricscollector.os.path.exists")
    def test_records_histogram_observation(self, mock_exists, mock_read):
        mock_exists.return_value = True
        mock_read.return_value = {
            "/tmp/gunicorn_registry.sock": {"pending": 75, "active": 0},
        }
        _, metrics, hostname = _build_registry()

        _sample(metrics, hostname)
        _sample(metrics, hostname)

        hist = metrics["queue_depth_hist"].labels(host=hostname, socket="registry")
        assert hist._sum.get() == 150.0  # 75 + 75

    @patch("workers.systemmetricscollector._read_proc_net_unix")
    @patch("workers.systemmetricscollector.os.path.exists")
    def test_sets_active_connections(self, mock_exists, mock_read):
        mock_exists.return_value = True
        mock_read.return_value = {
            "/tmp/gunicorn_registry.sock": {"pending": 0, "active": 10},
        }
        _, metrics, hostname = _build_registry()

        _sample(metrics, hostname)

        assert (
            metrics["active_connections"].labels(host=hostname, socket="registry")._value.get()
            == 10.0
        )

    @patch("workers.systemmetricscollector._read_proc_net_unix")
    @patch("workers.systemmetricscollector.os.path.exists")
    def test_socket_not_present(self, mock_exists, mock_read):
        mock_exists.return_value = False
        mock_read.return_value = {}
        _, metrics, hostname = _build_registry()

        _sample(metrics, hostname)

        assert metrics["socket_present"].labels(host=hostname, socket="registry")._value.get() == 0
        assert metrics["queue_depth"].labels(host=hostname, socket="registry")._value.get() == 0

    @patch("workers.systemmetricscollector._read_proc_net_unix")
    @patch("workers.systemmetricscollector.os.path.exists")
    def test_updates_timestamp(self, mock_exists, mock_read):
        mock_exists.return_value = True
        mock_read.return_value = {}
        _, metrics, hostname = _build_registry()

        before = time.time()
        _sample(metrics, hostname)
        after = time.time()

        ts = metrics["last_sample_timestamp"].labels(host=hostname)._value.get()
        assert before <= ts <= after

    @patch("workers.systemmetricscollector._read_proc_net_unix")
    def test_procfs_failure_increments_errors_and_skips_timestamp(self, mock_read):
        mock_read.side_effect = OSError("permission denied")
        _, metrics, hostname = _build_registry()

        _sample(metrics, hostname)

        assert metrics["collector_errors"].labels(host=hostname)._value.get() == 1.0
        assert metrics["last_sample_timestamp"].labels(host=hostname)._value.get() == 0.0


class TestPush:
    @patch("workers.systemmetricscollector.push_to_gateway")
    def test_successful_push(self, mock_push):
        _, metrics, hostname = _build_registry()

        _push(None, metrics, hostname)

        mock_push.assert_called_once()

    @patch("workers.systemmetricscollector.push_to_gateway")
    def test_pushgateway_failure_increments_errors(self, mock_push):
        mock_push.side_effect = Exception("connection refused")
        registry, metrics, hostname = _build_registry()

        _push(registry, metrics, hostname)

        assert metrics["collector_errors"].labels(host=hostname)._value.get() == 1.0
