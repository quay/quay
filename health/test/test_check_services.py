"""Unit tests for health.services._check_services timeout and exception handling."""

import logging
from unittest.mock import MagicMock

import gevent
import pytest

from health.services import _SERVICE_CHECK_TIMEOUT, _check_services


@pytest.fixture
def mock_app():
    return MagicMock()


class TestCheckServicesTimeout:
    def test_service_exceeding_timeout_returns_failure(self, mock_app):
        def slow_service(a):
            gevent.sleep(_SERVICE_CHECK_TIMEOUT + 1)
            return (True, None)

        services = {"slow_svc": slow_service}
        result = _check_services(mock_app, skip=[], services=services)

        assert result["slow_svc"][0] is False
        assert "Health check failed" in result["slow_svc"][1]

    def test_service_exceeding_timeout_logs_error(self, mock_app, caplog):
        def slow_service(a):
            gevent.sleep(_SERVICE_CHECK_TIMEOUT + 1)
            return (True, None)

        services = {"slow_svc": slow_service}
        with caplog.at_level(logging.ERROR, logger="health.services"):
            _check_services(mock_app, skip=[], services=services)

        assert any("slow_svc" in rec.message for rec in caplog.records)


class TestCheckServicesException:
    def test_raising_service_returns_failure(self, mock_app):
        def bad_service(a):
            raise RuntimeError("connection refused")

        services = {"bad_svc": bad_service}
        result = _check_services(mock_app, skip=[], services=services)

        assert result["bad_svc"][0] is False
        assert "connection refused" in result["bad_svc"][1]

    def test_raising_service_logs_error(self, mock_app, caplog):
        def bad_service(a):
            raise RuntimeError("connection refused")

        services = {"bad_svc": bad_service}
        with caplog.at_level(logging.ERROR, logger="health.services"):
            _check_services(mock_app, skip=[], services=services)

        assert any("bad_svc" in rec.message for rec in caplog.records)


class TestCheckServicesSuccess:
    def test_healthy_service_returns_original_result(self, mock_app):
        def good_service(a):
            return (True, "all good")

        services = {"good_svc": good_service}
        result = _check_services(mock_app, skip=[], services=services)

        assert result["good_svc"] == (True, "all good")

    def test_healthy_service_does_not_log_error(self, mock_app, caplog):
        def good_service(a):
            return (True, None)

        services = {"good_svc": good_service}
        with caplog.at_level(logging.ERROR, logger="health.services"):
            _check_services(mock_app, skip=[], services=services)

        assert not any("good_svc" in rec.message for rec in caplog.records)


class TestCheckServicesSkip:
    def test_skipped_services_are_excluded(self, mock_app):
        def svc(a):
            return (True, None)

        services = {"svc_a": svc, "svc_b": svc}
        result = _check_services(mock_app, skip=["svc_a"], services=services)

        assert "svc_a" not in result
        assert "svc_b" in result


class TestCheckServicesMultiple:
    def test_one_failure_does_not_affect_others(self, mock_app):
        def good_service(a):
            return (True, None)

        def bad_service(a):
            raise RuntimeError("boom")

        services = {"good": good_service, "bad": bad_service}
        result = _check_services(mock_app, skip=[], services=services)

        assert result["good"] == (True, None)
        assert result["bad"][0] is False
