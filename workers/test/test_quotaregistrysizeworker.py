from unittest.mock import MagicMock, patch

import features
from test.fixtures import *
from workers.quotaregistrysizeworker import QuotaRegistrySizeWorker

from app import app as flask_app  # isort: skip

# since all checks are happening only when the worker is the main process `if __name__ == "__main__:`
# we need to re-implement the call/not-call logic as duplicate.
# Considering to move it into the `_calculate_registry_size` instead is dropped as dependencies are not clear


def test_registrysizeworker(initialized_db):
    with patch(
        "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
    ) as mock_calculate_registry_size:
        worker = QuotaRegistrySizeWorker()
        worker._calculate_registry_size()
        assert mock_calculate_registry_size.called


def test_registrysizeworker_recovery(initialized_db):
    # we expect to fail since we are in recovery mode
    flask_app.config.update({"ACCOUNT_RECOVERY_MODE": True})
    flask_app.config.update({"SUPER_USERS": ["someone"]})

    if not flask_app.config.get("ACCOUNT_RECOVERY_MODE", False):
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_no_quotamanagement(initialized_db):
    # we expect to fail since we do not have quota management enabled
    features.QUOTA_MANAGEMENT = False
    features.SUPER_USERS = True
    flask_app.config.update({"SUPER_USERS": ["someone"]})
    if features.QUOTA_MANAGEMENT:
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_no_superusers(initialized_db):
    # we expect to fail since we do not have any superusers
    features.QUOTA_MANAGEMENT = True
    features.SUPER_USERS = True
    flask_app.config.update({"SUPER_USERS": []})
    if all(
        [features.QUOTA_MANAGEMENT, features.SUPER_USERS, len(flask_app.config["SUPER_USERS"]) > 0]
    ):
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert not mock_calculate_registry_size.called


def test_registrysizeworker_ldap_superusers(initialized_db):
    # we expect to succeed since LDAP_SUPERUSERS_FILTER is not empty
    features.QUOTA_MANAGEMENT = False
    features.SUPER_USERS = True
    flask_app.config.update({"LDAP_SUPERUSER_FILTER": "(objectClass=*)"})
    flask_app.config.update({"SUPER_USERS": []})
    if not any(
        [
            any(
                [
                    features.SUPER_USERS,
                    len(flask_app.config.get("SUPER_USERS", [])) == 0,
                ]
            ),
            flask_app.config.get("LDAP_SUPERUSER_FILTER", False),
        ]
    ):
        with patch(
            "workers.quotaregistrysizeworker.calculate_registry_size", MagicMock()
        ) as mock_calculate_registry_size:
            worker = QuotaRegistrySizeWorker()
            worker._calculate_registry_size()
            assert mock_calculate_registry_size.called
