import time
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from app import app as quay_app
from endpoints.api.mirrorhealth import (
    RepositoryMirrorHealth,
    _get_last_sync_timestamps,
    _get_mirror_workers_active_value,
    _get_pending_tags_total,
    _mirror_status_counts,
    get_mirror_health_data,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


# =============================================================================
# Unit tests for Prometheus registry reader helpers
# =============================================================================


class TestGetLastSyncTimestamps:
    def test_returns_empty_when_metric_absent(self):
        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = []
            result = _get_last_sync_timestamps()
            assert result == {}

    def test_parses_samples_correctly(self):
        sample = mock.Mock()
        sample.name = "quay_repository_mirror_last_sync_timestamp"
        sample.labels = {"namespace": "ns1", "repository": "repo1"}
        sample.value = 1700000000.0

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_last_sync_timestamp"
        metric.samples = [sample]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            result = _get_last_sync_timestamps()
            assert result == {("ns1", "repo1"): 1700000000.0}

    def test_skips_samples_missing_labels(self):
        sample = mock.Mock()
        sample.name = "quay_repository_mirror_last_sync_timestamp"
        sample.labels = {"namespace": "ns1"}
        sample.value = 1700000000.0

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_last_sync_timestamp"
        metric.samples = [sample]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            result = _get_last_sync_timestamps()
            assert result == {}

    def test_handles_registry_exception(self):
        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.side_effect = RuntimeError("boom")
            result = _get_last_sync_timestamps()
            assert result == {}


class TestGetPendingTagsTotal:
    def test_returns_zero_when_metric_absent(self):
        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = []
            result = _get_pending_tags_total()
            assert result == 0

    def test_sums_across_namespaces(self):
        s1 = mock.Mock()
        s1.name = "quay_repository_mirror_pending_tags"
        s1.labels = {"namespace": "ns1", "repository": "r1"}
        s1.value = 5.0

        s2 = mock.Mock()
        s2.name = "quay_repository_mirror_pending_tags"
        s2.labels = {"namespace": "ns2", "repository": "r2"}
        s2.value = 3.0

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_pending_tags"
        metric.samples = [s1, s2]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            assert _get_pending_tags_total() == 8

    def test_filters_by_namespace(self):
        s1 = mock.Mock()
        s1.name = "quay_repository_mirror_pending_tags"
        s1.labels = {"namespace": "ns1", "repository": "r1"}
        s1.value = 5.0

        s2 = mock.Mock()
        s2.name = "quay_repository_mirror_pending_tags"
        s2.labels = {"namespace": "ns2", "repository": "r2"}
        s2.value = 3.0

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_pending_tags"
        metric.samples = [s1, s2]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            assert _get_pending_tags_total(namespace="ns1") == 5

    def test_returns_int_for_whole_numbers(self):
        s1 = mock.Mock()
        s1.name = "quay_repository_mirror_pending_tags"
        s1.labels = {"namespace": "ns1", "repository": "r1"}
        s1.value = 7.0

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_pending_tags"
        metric.samples = [s1]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            result = _get_pending_tags_total()
            assert result == 7
            assert isinstance(result, int)


class TestGetMirrorWorkersActiveValue:
    def test_returns_zero_when_metric_absent(self):
        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = []
            assert _get_mirror_workers_active_value() == 0

    def test_returns_sample_value(self):
        sample = mock.Mock()
        sample.name = "quay_repository_mirror_workers_active"
        sample.value = 1

        metric = mock.Mock()
        metric.name = "quay_repository_mirror_workers_active"
        metric.samples = [sample]

        with mock.patch("endpoints.api.mirrorhealth.REGISTRY") as mock_reg:
            mock_reg.collect.return_value = [metric]
            assert _get_mirror_workers_active_value() == 1


# =============================================================================
# Unit tests for get_mirror_health_data
# =============================================================================


class TestGetMirrorHealthData:
    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_healthy_with_no_mirrors(self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk):
        mock_counts.return_value = {
            "total": 0,
            "syncing": 0,
            "completed": 0,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert result["healthy"] is True
        assert result["repositories"]["total"] == 0
        assert result["tags_pending"] == 0
        assert result["issues"] == []

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_healthy_all_succeeded(self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk):
        mock_counts.return_value = {
            "total": 10,
            "syncing": 0,
            "completed": 10,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert result["healthy"] is True
        assert result["repositories"]["total"] == 10
        assert result["repositories"]["completed"] == 10

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_unhealthy_high_failure_rate(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 10,
            "syncing": 0,
            "completed": 5,
            "failed": 5,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert result["healthy"] is False
        assert result["workers"]["status"] == "degraded"
        critical_issues = [i for i in result["issues"] if i["severity"] == "critical"]
        assert len(critical_issues) == 1
        assert "50.0%" in critical_issues[0]["message"]

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_healthy_at_threshold_boundary(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 10,
            "syncing": 0,
            "completed": 8,
            "failed": 2,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert result["healthy"] is True

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_never_run_excluded_from_failure_rate(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 10,
            "syncing": 0,
            "completed": 4,
            "failed": 1,
            "never_run": 5,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert result["healthy"] is True

    @mock.patch("endpoints.api.mirrorhealth.app")
    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=1)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_unhealthy_worker_replica_mismatch(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk, mock_app
    ):
        mock_counts.return_value = {
            "total": 5,
            "syncing": 0,
            "completed": 5,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))
        mock_app.config.get.return_value = 3

        result = get_mirror_health_data()

        assert result["healthy"] is False
        warning_issues = [i for i in result["issues"] if i["severity"] == "warning"]
        worker_warnings = [w for w in warning_issues if "worker" in w["message"].lower()]
        assert len(worker_warnings) == 1
        assert "2 mirror worker" in worker_warnings[0]["message"]

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_stale_repos_generate_warnings(self, mock_counts, mock_rows, mock_pending, mock_wk):
        mock_counts.return_value = {
            "total": 2,
            "syncing": 0,
            "completed": 2,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).timestamp()
        with mock.patch(
            "endpoints.api.mirrorhealth._get_last_sync_timestamps",
            return_value={("ns1", "repo1"): stale_ts},
        ):
            result = get_mirror_health_data()

        stale_warnings = [
            i for i in result["issues"] if "hasn't synced" in i.get("message", "")
        ]
        assert len(stale_warnings) == 1
        assert "ns1/repo1" in stale_warnings[0]["message"]

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_stale_cap_limits_issue_samples(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 10,
            "syncing": 0,
            "completed": 10,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).timestamp()
        many_stale = {(f"ns{i}", f"repo{i}"): stale_ts for i in range(20)}
        with mock.patch(
            "endpoints.api.mirrorhealth._get_last_sync_timestamps",
            return_value=many_stale,
        ):
            result = get_mirror_health_data()

        stale_warnings = [
            i for i in result["issues"] if "hasn't synced" in i.get("message", "")
        ]
        assert len(stale_warnings) <= 5

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_response_structure(self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk):
        mock_counts.return_value = {
            "total": 3,
            "syncing": 1,
            "completed": 1,
            "failed": 1,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data()

        assert "healthy" in result
        assert "workers" in result
        assert "active" in result["workers"]
        assert "configured" in result["workers"]
        assert "status" in result["workers"]
        assert "repositories" in result
        assert "total" in result["repositories"]
        assert "syncing" in result["repositories"]
        assert "completed" in result["repositories"]
        assert "failed" in result["repositories"]
        assert "never_run" in result["repositories"]
        assert "tags_pending" in result
        assert "last_check" in result
        assert "issues" in result
        assert result["last_check"].endswith("Z")

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_detailed_includes_pagination(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 0,
            "syncing": 0,
            "completed": 0,
            "failed": 0,
            "never_run": 0,
        }
        page_query = mock.Mock()
        page_query.limit.return_value = mock.Mock(offset=mock.Mock(return_value=[]))
        rows_q = mock.Mock()
        rows_q.where.return_value = mock.Mock(limit=mock.Mock(return_value=[]))
        rows_q.limit.return_value = mock.Mock(offset=mock.Mock(return_value=[]))

        mock_rows.return_value = rows_q

        result = get_mirror_health_data(detailed=True)

        assert "details" in result["repositories"]
        assert "pagination" in result["repositories"]
        assert "limit" in result["repositories"]["pagination"]
        assert "offset" in result["repositories"]["pagination"]
        assert "has_more" in result["repositories"]["pagination"]

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_no_details_without_detailed_flag(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 0,
            "syncing": 0,
            "completed": 0,
            "failed": 0,
            "never_run": 0,
        }
        mock_rows.return_value = mock.Mock(where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))))

        result = get_mirror_health_data(detailed=False)

        assert "details" not in result["repositories"]
        assert "pagination" not in result["repositories"]

    @mock.patch("endpoints.api.mirrorhealth._get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._get_last_sync_timestamps", return_value={})
    @mock.patch("endpoints.api.mirrorhealth._get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.mirrorhealth._mirror_rows_query")
    @mock.patch("endpoints.api.mirrorhealth._mirror_status_counts")
    def test_detail_limit_clamped_to_max(
        self, mock_counts, mock_rows, mock_pending, mock_ts, mock_wk
    ):
        mock_counts.return_value = {
            "total": 0,
            "syncing": 0,
            "completed": 0,
            "failed": 0,
            "never_run": 0,
        }
        rows_q = mock.Mock()
        rows_q.where.return_value = mock.Mock(limit=mock.Mock(return_value=[]))
        rows_q.limit.return_value = mock.Mock(offset=mock.Mock(return_value=[]))
        mock_rows.return_value = rows_q

        result = get_mirror_health_data(detailed=True, detail_limit=5000)

        assert result["repositories"]["pagination"]["limit"] == 1000


# =============================================================================
# API endpoint integration tests
# =============================================================================


class TestMirrorHealthEndpoint:
    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_superuser_global_access(self, mock_health, app, initialized_db):
        mock_health.return_value = {
            "healthy": True,
            "workers": {"active": 0, "configured": 0, "status": "healthy"},
            "repositories": {
                "total": 0, "syncing": 0, "completed": 0, "failed": 0, "never_run": 0,
            },
            "tags_pending": 0,
            "last_check": "2024-01-01T00:00:00Z",
            "issues": [],
        }
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(cl, RepositoryMirrorHealth, "GET", None, None, 200)
            assert resp.json["healthy"] is True

    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_anonymous_returns_401(self, mock_health, app, initialized_db):
        with client_with_identity(None, app) as cl:
            conduct_api_call(cl, RepositoryMirrorHealth, "GET", None, None, 401)

    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_unhealthy_returns_503(self, mock_health, app, initialized_db):
        mock_health.return_value = {
            "healthy": False,
            "workers": {"active": 0, "configured": 0, "status": "degraded"},
            "repositories": {
                "total": 10, "syncing": 0, "completed": 5, "failed": 5, "never_run": 0,
            },
            "tags_pending": 0,
            "last_check": "2024-01-01T00:00:00Z",
            "issues": [{"severity": "critical", "message": "high failure rate", "timestamp": "2024-01-01T00:00:00Z"}],
        }
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(cl, RepositoryMirrorHealth, "GET", None, None, 503)
            assert resp.json["healthy"] is False

    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_cache_control_header(self, mock_health, app, initialized_db):
        mock_health.return_value = {
            "healthy": True,
            "workers": {"active": 0, "configured": 0, "status": "healthy"},
            "repositories": {
                "total": 0, "syncing": 0, "completed": 0, "failed": 0, "never_run": 0,
            },
            "tags_pending": 0,
            "last_check": "2024-01-01T00:00:00Z",
            "issues": [],
        }
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(cl, RepositoryMirrorHealth, "GET", None, None, 200)
            assert "no-cache" in resp.headers.get("Cache-Control", "")

    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_namespace_passed_to_health_data(self, mock_health, app, initialized_db):
        mock_health.return_value = {
            "healthy": True,
            "workers": {"active": 0, "configured": 0, "status": "healthy"},
            "repositories": {
                "total": 0, "syncing": 0, "completed": 0, "failed": 0, "never_run": 0,
            },
            "tags_pending": 0,
            "last_check": "2024-01-01T00:00:00Z",
            "issues": [],
        }
        with client_with_identity("devtable", app) as cl:
            conduct_api_call(
                cl,
                RepositoryMirrorHealth,
                "GET",
                {"namespace": "devtable"},
                None,
                200,
            )
            mock_health.assert_called_once()
            call_kwargs = mock_health.call_args
            assert call_kwargs[1].get("namespace") or call_kwargs[0][0] == "devtable"

    @mock.patch("endpoints.api.mirrorhealth.get_mirror_health_data")
    def test_global_readonly_superuser_access(self, mock_health, app, initialized_db):
        mock_health.return_value = {
            "healthy": True,
            "workers": {"active": 0, "configured": 0, "status": "healthy"},
            "repositories": {
                "total": 0, "syncing": 0, "completed": 0, "failed": 0, "never_run": 0,
            },
            "tags_pending": 0,
            "last_check": "2024-01-01T00:00:00Z",
            "issues": [],
        }
        with client_with_identity("globalreadonlysuperuser", app) as cl:
            conduct_api_call(cl, RepositoryMirrorHealth, "GET", None, None, 200)
