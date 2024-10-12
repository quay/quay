from test.fixtures import *
from unittest.mock import MagicMock, patch
import app
import features

from workers.quotaregistrysizeworker import QuotaRegistrySizeWorker


def test_registrysizeworker(initialized_db):
    with patch(
        "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
    ) as mock_calculate_registry_size:
        worker = QuotaRegistrySizeWorker()
        worker._calculate_registry_size()
        assert mock_calculate_registry_size.called


def test_registrysizeworker_recovery(initialized_db):
    # we expect to fail since we are in recovery mode
    app.config.update({"ACCOUNT_RECOVERY_MODE": True})
    app.config.update({"SUPER_USERS": ["someone"]})

    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_no_quotamanagement(initialized_db):
    # we expect to fail since we do not have quota management enabled
    features.QUOTA_MANAGEMENT = False
    app.config.update({"SUPER_USERS": ["someone"]})
    if not features.QUOTA_MANAGEMENT:
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_no_superusers(initialized_db):
    # we expect to fail since we do not have any superusers
    app.config.update({"SUPER_USERS": [""]})
    if not features.QUOTA_MANAGEMENT:
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_ldap_superusers(initialized_db):
    # we expect to succeed since LDAP_SUPERUSERS_FILTER is not empty
    app.config.update({"LDAP_SUPERUSER_FILTER": "(objectClass=*)"})
    app.config.update({"SUPER_USERS": []})
    if not all(
        [
            any(
                [
                    features.SUPER_USERS,
                    len(app.config.get("SUPER_USERS", [])) == 0,
                ]
            ),
            app.config.get("LDAP_SUPERUSER_FILTER", False),
        ]
    ):
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert mock_calculate_registry_size.called
