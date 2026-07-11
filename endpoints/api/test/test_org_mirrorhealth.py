from datetime import datetime, timezone
from unittest import mock

import pytest

from app import app as quay_app
from endpoints.api.org_mirrorhealth import (
    OrganizationMirrorHealth,
    _aggregate_repo_counts,
    _config_status_indicators,
    get_org_mirror_health_data,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


def _mock_empty_org_mirror_repo_rows_query(mock_rows_query):
    mock_rows_query.return_value = mock.Mock(
        where=mock.Mock(return_value=mock.Mock(limit=mock.Mock(return_value=[]))),
        limit=mock.Mock(return_value=mock.Mock(offset=mock.Mock(return_value=[]))),
    )


class TestOrgMirrorHealthHelpers:
    def test_config_status_indicators_success(self):
        from data.database import OrgMirrorStatus

        result = _config_status_indicators(OrgMirrorStatus.SUCCESS)
        assert result == {
            "syncing": 0,
            "completed": 1,
            "failed": 0,
            "never_run": 0,
        }

    def test_aggregate_repo_counts_includes_sync_now_in_syncing(self):
        counts = {
            "SUCCESS": 2,
            "FAIL": 1,
            "NEVER_RUN": 1,
            "SKIP": 1,
            "SYNCING": 1,
            "SYNC_NOW": 2,
        }
        result = _aggregate_repo_counts(counts)
        assert result["total"] == 8
        assert result["syncing"] == 3
        assert result["skipped"] == 1


class TestGetOrgMirrorHealthData:
    @mock.patch("endpoints.api.org_mirrorhealth._org_mirror_repo_rows_query")
    @mock.patch("endpoints.api.org_mirrorhealth.get_mirror_workers_active_value", return_value=1)
    @mock.patch("endpoints.api.org_mirrorhealth.get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.org_mirrorhealth.get_metric_timestamps", return_value={})
    @mock.patch("endpoints.api.org_mirrorhealth.get_namespace_gauge_value", return_value=None)
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_repo_status_counts")
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_config")
    @mock.patch("endpoints.api.org_mirrorhealth.model.user.get_namespace_user")
    def test_healthy_with_no_repos(
        self,
        mock_get_user,
        mock_get_config,
        mock_counts,
        mock_gauge,
        mock_ts,
        mock_pending,
        mock_workers,
        mock_rows_query,
    ):
        from data.database import OrgMirrorRepoStatus, OrgMirrorStatus

        org = mock.Mock()
        org.organization = True
        mock_get_user.return_value = org

        config = mock.Mock()
        config.sync_status = OrgMirrorStatus.SUCCESS
        config.is_enabled = True
        config.sync_start_date = datetime.now(timezone.utc)
        mock_get_config.return_value = config
        mock_counts.return_value = {status.name: 0 for status in OrgMirrorRepoStatus}
        _mock_empty_org_mirror_repo_rows_query(mock_rows_query)

        result = get_org_mirror_health_data("coreos")
        assert result["healthy"] is True
        assert result["organization"]["completed"] == 1
        assert result["organization"]["repositories"]["total"] == 0

    @mock.patch("endpoints.api.org_mirrorhealth._org_mirror_repo_rows_query")
    @mock.patch("endpoints.api.org_mirrorhealth.get_mirror_workers_active_value", return_value=1)
    @mock.patch("endpoints.api.org_mirrorhealth.get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.org_mirrorhealth.get_metric_timestamps", return_value={})
    @mock.patch("endpoints.api.org_mirrorhealth.get_namespace_gauge_value", return_value=None)
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_repo_status_counts")
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_config")
    @mock.patch("endpoints.api.org_mirrorhealth.model.user.get_namespace_user")
    def test_unhealthy_high_failure_rate(
        self,
        mock_get_user,
        mock_get_config,
        mock_counts,
        mock_gauge,
        mock_ts,
        mock_pending,
        mock_workers,
        mock_rows_query,
    ):
        from data.database import OrgMirrorRepoStatus, OrgMirrorStatus

        org = mock.Mock()
        org.organization = True
        mock_get_user.return_value = org

        config = mock.Mock()
        config.sync_status = OrgMirrorStatus.SUCCESS
        config.is_enabled = True
        config.sync_start_date = datetime.now(timezone.utc)
        mock_get_config.return_value = config
        mock_counts.return_value = {status.name: 0 for status in OrgMirrorRepoStatus}
        mock_counts.return_value.update({"SUCCESS": 7, "FAIL": 3})
        _mock_empty_org_mirror_repo_rows_query(mock_rows_query)

        result = get_org_mirror_health_data("coreos")
        assert result["healthy"] is False
        assert result["issues"][0]["severity"] == "critical"

    @mock.patch("endpoints.api.org_mirrorhealth._org_mirror_repo_rows_query")
    @mock.patch("endpoints.api.org_mirrorhealth.app")
    @mock.patch("endpoints.api.org_mirrorhealth.get_mirror_workers_active_value", return_value=0)
    @mock.patch("endpoints.api.org_mirrorhealth.get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.org_mirrorhealth.get_metric_timestamps", return_value={})
    @mock.patch("endpoints.api.org_mirrorhealth.get_namespace_gauge_value", return_value=None)
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_repo_status_counts")
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_config")
    @mock.patch("endpoints.api.org_mirrorhealth.model.user.get_namespace_user")
    def test_skips_worker_replica_warning_when_local_gauge_zero(
        self,
        mock_get_user,
        mock_get_config,
        mock_counts,
        mock_gauge,
        mock_ts,
        mock_pending,
        mock_workers,
        mock_app,
        mock_rows_query,
    ):
        from data.database import OrgMirrorRepoStatus, OrgMirrorStatus

        org = mock.Mock()
        org.organization = True
        mock_get_user.return_value = org

        config = mock.Mock()
        config.sync_status = OrgMirrorStatus.SUCCESS
        config.is_enabled = True
        config.sync_start_date = datetime.now(timezone.utc)
        mock_get_config.return_value = config
        mock_counts.return_value = {status.name: 0 for status in OrgMirrorRepoStatus}
        mock_app.config.get.return_value = 3
        _mock_empty_org_mirror_repo_rows_query(mock_rows_query)

        result = get_org_mirror_health_data("coreos")
        assert result["healthy"] is True
        assert not any("worker" in i["message"].lower() for i in result["issues"])

    @mock.patch("endpoints.api.org_mirrorhealth._org_mirror_repo_rows_query")
    @mock.patch("endpoints.api.org_mirrorhealth.app")
    @mock.patch("endpoints.api.org_mirrorhealth.get_mirror_workers_active_value", return_value=1)
    @mock.patch("endpoints.api.org_mirrorhealth.get_pending_tags_total", return_value=0)
    @mock.patch("endpoints.api.org_mirrorhealth.get_metric_timestamps", return_value={})
    @mock.patch("endpoints.api.org_mirrorhealth.get_namespace_gauge_value", return_value=None)
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_repo_status_counts")
    @mock.patch("endpoints.api.org_mirrorhealth.model.org_mirror.get_org_mirror_config")
    @mock.patch("endpoints.api.org_mirrorhealth.model.user.get_namespace_user")
    def test_worker_replica_warning_when_local_worker_reports(
        self,
        mock_get_user,
        mock_get_config,
        mock_counts,
        mock_gauge,
        mock_ts,
        mock_pending,
        mock_workers,
        mock_app,
        mock_rows_query,
    ):
        from data.database import OrgMirrorRepoStatus, OrgMirrorStatus

        org = mock.Mock()
        org.organization = True
        mock_get_user.return_value = org

        config = mock.Mock()
        config.sync_status = OrgMirrorStatus.SUCCESS
        config.is_enabled = True
        config.sync_start_date = datetime.now(timezone.utc)
        mock_get_config.return_value = config
        mock_counts.return_value = {status.name: 0 for status in OrgMirrorRepoStatus}
        mock_app.config.get.return_value = 3
        _mock_empty_org_mirror_repo_rows_query(mock_rows_query)

        result = get_org_mirror_health_data("coreos")
        assert result["healthy"] is False
        worker_issues = [i for i in result["issues"] if "worker" in i["message"].lower()]
        assert len(worker_issues) == 1


class TestOrganizationMirrorHealthApi:
    @mock.patch("endpoints.api.org_mirrorhealth.get_org_mirror_health_data")
    def test_superuser_access(self, mock_health, app, initialized_db):
        mock_health.return_value = {"healthy": True, "issues": []}
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                OrganizationMirrorHealth,
                "GET",
                "/organization/coreos/mirror/health",
                params={},
            )
            assert resp.status_code == 200

    @mock.patch("endpoints.api.org_mirrorhealth.get_org_mirror_health_data")
    def test_unhealthy_returns_503(self, mock_health, app, initialized_db):
        mock_health.return_value = {"healthy": False, "issues": [{"severity": "critical"}]}
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                OrganizationMirrorHealth,
                "GET",
                "/organization/coreos/mirror/health",
                params={},
            )
            assert resp.status_code == 503

    @mock.patch("endpoints.api.org_mirrorhealth.get_org_mirror_health_data")
    def test_cache_control_header(self, mock_health, app, initialized_db):
        mock_health.return_value = {"healthy": True, "issues": []}
        with client_with_identity("devtable", app) as cl:
            resp = conduct_api_call(
                cl,
                OrganizationMirrorHealth,
                "GET",
                "/organization/coreos/mirror/health",
                params={},
            )
            assert resp.headers.get("Cache-Control") == "no-cache, no-store, must-revalidate"
