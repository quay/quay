import time
from unittest import mock

import pytest
from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram

from test.fixtures import *
from workers.repomirrorworker import (
    _map_failure_to_reason,
    _update_mirror_metrics_on_failure,
)

# =============================================================================
# Tests for _map_failure_to_reason
# =============================================================================


class TestMapFailureToReason:
    @pytest.mark.parametrize(
        "error_message, expected_reason",
        [
            ("unauthorized access denied", "auth_failed"),
            ("HTTP 401 Unauthorized", "auth_failed"),
            ("403 Forbidden", "auth_failed"),
            ("authentication required", "auth_failed"),
            ("connection timed out after 30s", "network_timeout"),
            ("request timeout exceeded", "network_timeout"),
            ("connection refused by remote host", "connection_error"),
            ("network unreachable", "connection_error"),
            ("repository not found", "not_found"),
            ("HTTP 404 error", "not_found"),
            ("TLS handshake failure", "tls_error"),
            ("certificate has expired", "tls_error"),
            ("SSL verification failed", "tls_error"),
            ("unable to decrypt credentials", "decryption_failed"),
            ("something completely unexpected happened", "unknown_error"),
            ("", "unknown_error"),
        ],
    )
    def test_error_categorization(self, error_message, expected_reason):
        assert _map_failure_to_reason(error_message) == expected_reason

    def test_case_insensitive(self):
        assert _map_failure_to_reason("UNAUTHORIZED") == "auth_failed"
        assert _map_failure_to_reason("CONNECTION REFUSED") == "connection_error"
        assert _map_failure_to_reason("TLS Error") == "tls_error"

    def test_non_string_input(self):
        assert _map_failure_to_reason(None) == "unknown_error"
        assert _map_failure_to_reason(42) == "unknown_error"
        assert _map_failure_to_reason(Exception("timeout")) == "network_timeout"


# =============================================================================
# Tests for _update_mirror_metrics_on_failure
# =============================================================================


class TestUpdateMirrorMetricsOnFailure:
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_duration_seconds")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_failures_total")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_complete")
    @mock.patch("workers.repomirrorworker.repo_mirror_last_sync_status")
    @mock.patch("workers.repomirrorworker.repo_mirror_tags_pending")
    def test_sets_all_failure_metrics(
        self, mock_pending, mock_status, mock_complete, mock_failures, mock_duration
    ):
        mock_pending_labeled = mock.Mock()
        mock_pending.labels.return_value = mock_pending_labeled

        mock_status_labeled = mock.Mock()
        mock_status.labels.return_value = mock_status_labeled

        mock_complete_labeled = mock.Mock()
        mock_complete.labels.return_value = mock_complete_labeled

        mock_failures_labeled = mock.Mock()
        mock_failures.labels.return_value = mock_failures_labeled

        _update_mirror_metrics_on_failure("myns", "myrepo", "auth_failed", time.time() - 10)

        mock_pending.labels.assert_called_with(namespace="myns", repository="myrepo")
        mock_pending_labeled.set.assert_called_with(0)

        mock_complete.labels.assert_called_with(namespace="myns", repository="myrepo")
        mock_complete_labeled.set.assert_called_with(0)

        mock_failures.labels.assert_called_with(namespace="myns", reason="auth_failed")
        mock_failures_labeled.inc.assert_called_once()

    @mock.patch("workers.repomirrorworker.repo_mirror_sync_duration_seconds")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_failures_total")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_complete")
    @mock.patch("workers.repomirrorworker.repo_mirror_last_sync_status")
    @mock.patch("workers.repomirrorworker.repo_mirror_tags_pending")
    def test_records_duration_when_start_time_provided(
        self, mock_pending, mock_status, mock_complete, mock_failures, mock_duration
    ):
        mock_pending.labels.return_value = mock.Mock()
        mock_status.labels.return_value = mock.Mock()
        mock_complete.labels.return_value = mock.Mock()
        mock_failures.labels.return_value = mock.Mock()

        mock_duration_labeled = mock.Mock()
        mock_duration.labels.return_value = mock_duration_labeled

        start = time.time() - 60
        _update_mirror_metrics_on_failure("myns", "myrepo", "timeout", start)

        mock_duration.labels.assert_called_with(namespace="myns")
        mock_duration_labeled.observe.assert_called_once()
        observed = mock_duration_labeled.observe.call_args[0][0]
        assert 59 < observed < 62

    @mock.patch("workers.repomirrorworker.repo_mirror_sync_duration_seconds")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_failures_total")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_complete")
    @mock.patch("workers.repomirrorworker.repo_mirror_last_sync_status")
    @mock.patch("workers.repomirrorworker.repo_mirror_tags_pending")
    def test_skips_duration_when_no_start_time(
        self, mock_pending, mock_status, mock_complete, mock_failures, mock_duration
    ):
        mock_pending.labels.return_value = mock.Mock()
        mock_status.labels.return_value = mock.Mock()
        mock_complete.labels.return_value = mock.Mock()
        mock_failures.labels.return_value = mock.Mock()

        _update_mirror_metrics_on_failure("myns", "myrepo", "auth_failed", None)

        mock_duration.labels.assert_not_called()

    @mock.patch("workers.repomirrorworker.repo_mirror_sync_duration_seconds")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_failures_total")
    @mock.patch("workers.repomirrorworker.repo_mirror_sync_complete")
    @mock.patch("workers.repomirrorworker.repo_mirror_last_sync_status")
    @mock.patch("workers.repomirrorworker.repo_mirror_tags_pending")
    def test_defaults_to_unknown_error_reason(
        self, mock_pending, mock_status, mock_complete, mock_failures, mock_duration
    ):
        mock_pending.labels.return_value = mock.Mock()
        mock_status.labels.return_value = mock.Mock()
        mock_complete.labels.return_value = mock.Mock()
        mock_failures.labels.return_value = mock.Mock()

        _update_mirror_metrics_on_failure("myns", "myrepo", None, None)

        mock_failures.labels.assert_called_with(namespace="myns", reason="unknown_error")


# =============================================================================
# Tests for metric cardinality: Counter and Histogram use namespace-only labels
# =============================================================================


class TestMetricCardinality:
    def test_sync_failures_counter_has_namespace_and_reason_labels(self):
        from workers.repomirrorworker import repo_mirror_sync_failures_total

        assert repo_mirror_sync_failures_total._labelnames == ("namespace", "reason")

    def test_sync_duration_histogram_has_namespace_only_label(self):
        from workers.repomirrorworker import repo_mirror_sync_duration_seconds

        assert repo_mirror_sync_duration_seconds._labelnames == ("namespace",)

    def test_sync_duration_histogram_has_trimmed_buckets(self):
        from workers.repomirrorworker import repo_mirror_sync_duration_seconds

        expected = [60.0, 300.0, 900.0, 3600.0, float("inf")]
        assert list(repo_mirror_sync_duration_seconds._upper_bounds) == expected

    def test_tags_pending_gauge_has_per_repo_labels(self):
        from workers.repomirrorworker import repo_mirror_tags_pending

        assert repo_mirror_tags_pending._labelnames == ("namespace", "repository")

    def test_last_sync_status_gauge_has_per_repo_labels(self):
        from workers.repomirrorworker import repo_mirror_last_sync_status

        assert repo_mirror_last_sync_status._labelnames == (
            "namespace",
            "repository",
            "last_error_reason",
        )

    def test_sync_complete_gauge_has_per_repo_labels(self):
        from workers.repomirrorworker import repo_mirror_sync_complete

        assert repo_mirror_sync_complete._labelnames == ("namespace", "repository")

    def test_last_sync_timestamp_gauge_has_per_repo_labels(self):
        from workers.repomirrorworker import repo_mirror_last_sync_timestamp

        assert repo_mirror_last_sync_timestamp._labelnames == ("namespace", "repository")
