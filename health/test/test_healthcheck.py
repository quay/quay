import logging
from typing import Dict, List

import pytest

import health.healthcheck
import health.services
from app import app
from health.healthcheck import LDAPHealthCheck

INSTANCE_SERVICES = {
    "registry_gunicorn": (True, ""),
    "web_gunicorn": (True, ""),
    "service_key": (True, ""),
    "disk_space": (True, ""),
}

GLOBAL_SERVICES = {
    "database": (True, ""),
    "redis": (True, ""),
    "storage": (True, ""),
    "auth": (True, ""),
}

WARNING_SERVICES = {
    "disk_space_warning": (True, ""),
}

app.config.update({"TESTING": True})


class ConfigProvider(object):
    provider_id = "provider_id"


class InstanceKeys(object):
    local_key_id = "local_key_id"


class SuperUserPermission(object):
    def can(self):
        return True


def _check_all_services() -> Dict:
    services = dict(INSTANCE_SERVICES)
    services.update(GLOBAL_SERVICES)
    return services


def _check_warning_services() -> Dict:
    return WARNING_SERVICES


health.services.check_all_services = _check_all_services  # type: ignore
health.services.check_warning_services = _check_warning_services  # type: ignore
health.healthcheck.SuperUserPermission = SuperUserPermission  # type: ignore


def test_healthcheck_allgood():
    with app.app_context():
        hc = LDAPHealthCheck(app, ConfigProvider(), InstanceKeys())
        assert hc.check_names() == ["LDAPHealthCheck"]
        assert hc.instance_skips == ["redis", "storage"]
        states, code = hc.calculate_overall_health(_check_all_services())
        assert code == 200
        assert set(states["services"].values()) == set([True])


def test_healtcheck_failauth():
    with app.app_context():
        hc = LDAPHealthCheck(app, ConfigProvider(), InstanceKeys())
        assert hc.check_names() == ["LDAPHealthCheck"]
        assert hc.instance_skips == ["redis", "storage"]
        GLOBAL_SERVICES["auth"] = (False, "failing")
        states, code = hc.calculate_overall_health(_check_all_services())
        assert code == 200
        assert set(states["services"].values()) == set([True, False])


def test_healtcheck_failnonauth():
    with app.app_context():
        hc = LDAPHealthCheck(app, ConfigProvider(), InstanceKeys())
        assert hc.check_names() == ["LDAPHealthCheck"]
        assert hc.instance_skips == ["redis", "storage"]
        GLOBAL_SERVICES["database"] = (False, "failing")
        states, code = hc.calculate_overall_health(_check_all_services())
        assert code == 503
        assert set(states["services"].values()) == set([True, False])


def test_healtcheck_failnonauthandauth():
    with app.app_context():
        hc = LDAPHealthCheck(app, ConfigProvider(), InstanceKeys())
        assert hc.check_names() == ["LDAPHealthCheck"]
        assert hc.instance_skips == ["redis", "storage"]
        GLOBAL_SERVICES["database"] = (False, "failing")
        GLOBAL_SERVICES["auth"] = (False, "failing")
        states, code = hc.calculate_overall_health(_check_all_services())
        assert code == 503
        assert set(states["services"].values()) == set([True, False])
