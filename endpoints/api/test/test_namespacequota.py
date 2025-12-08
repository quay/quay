"""
Tests for namespace quota API endpoints, specifically audit logging.

This tests the fix for PROJQUAY-9859: No audit log for Quota configuration.
"""

from unittest.mock import patch

import pytest

from data import model
from endpoints.api.namespacequota import (
    OrganizationQuota,
    OrganizationQuotaLimit,
    OrganizationQuotaLimitList,
    OrganizationQuotaList,
)
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from test.fixtures import *


class TestQuotaAuditLogging:
    """
    Tests that quota operations create appropriate audit log entries.

    This addresses PROJQUAY-9859: After configuring Quota for Organization/User,
    there is no audit log in Usage Logs.
    """

    @pytest.fixture(autouse=True)
    def setup(self, app):
        """Enable required features and create test organization."""
        import features

        features.import_features(
            {
                "FEATURE_SUPER_USERS": True,
                "FEATURE_SUPERUSERS_FULL_ACCESS": True,
                "FEATURE_QUOTA_MANAGEMENT": True,
                "FEATURE_EDIT_QUOTA": True,
            }
        )

        # Create a test organization if it doesn't exist
        randomuser = model.user.get_user("randomuser")
        try:
            model.organization.get_organization("quotatestorg")
        except model.InvalidOrganizationException:
            model.organization.create_organization(
                "quotatestorg", "quotatestorg@test.com", randomuser
            )

        yield

        # Clean up any quotas created during tests
        try:
            quotas = model.namespacequota.get_namespace_quota_list("quotatestorg")
            for quota in quotas:
                model.namespacequota.delete_namespace_quota(quota)
        except Exception:
            pass

    def test_create_quota_logs_action(self, app):
        """
        Test that creating a quota logs the org_create_quota action.
        """
        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {"orgname": "quotatestorg"}
                body = {"limit_bytes": 1073741824}  # 1 GiB
                conduct_api_call(cl, OrganizationQuotaList, "POST", params, body, 201)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_create_quota"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["limit_bytes"] == 1073741824
                assert "limit" in metadata  # Human-readable format

    def test_update_quota_logs_action(self, app):
        """
        Test that updating a quota logs the org_change_quota action with previous values.
        """
        # Create a quota first
        org = model.organization.get_organization("quotatestorg")
        quota = model.namespacequota.create_namespace_quota(org, 1073741824)  # 1 GiB

        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {"orgname": "quotatestorg", "quota_id": quota.id}
                body = {"limit_bytes": 5368709120}  # 5 GiB
                conduct_api_call(cl, OrganizationQuota, "PUT", params, body, 200)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_change_quota"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["limit_bytes"] == 5368709120
                assert metadata["previous_limit_bytes"] == 1073741824

    def test_delete_quota_logs_action(self, app):
        """
        Test that deleting a quota logs the org_delete_quota action.
        """
        # Create a quota first
        org = model.organization.get_organization("quotatestorg")
        quota = model.namespacequota.create_namespace_quota(org, 1073741824)  # 1 GiB
        quota_id = quota.id

        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {"orgname": "quotatestorg", "quota_id": quota_id}
                conduct_api_call(cl, OrganizationQuota, "DELETE", params, None, 204)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_delete_quota"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["quota_id"] == quota_id
                assert metadata["limit_bytes"] == 1073741824

    def test_create_quota_limit_logs_action(self, app):
        """
        Test that creating a quota limit logs the org_create_quota_limit action.
        """
        # Create a quota first
        org = model.organization.get_organization("quotatestorg")
        quota = model.namespacequota.create_namespace_quota(org, 1073741824)  # 1 GiB

        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {"orgname": "quotatestorg", "quota_id": quota.id}
                body = {"type": "Warning", "threshold_percent": 80}
                conduct_api_call(cl, OrganizationQuotaLimitList, "POST", params, body, 201)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_create_quota_limit"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["type"] == "Warning"
                assert metadata["threshold_percent"] == 80

    def test_update_quota_limit_logs_action(self, app):
        """
        Test that updating a quota limit logs the org_change_quota_limit action.
        """
        # Create a quota and limit first
        org = model.organization.get_organization("quotatestorg")
        quota = model.namespacequota.create_namespace_quota(org, 1073741824)  # 1 GiB
        limit = model.namespacequota.create_namespace_quota_limit(quota, "Warning", 80)

        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {
                    "orgname": "quotatestorg",
                    "quota_id": quota.id,
                    "limit_id": limit.id,
                }
                body = {"threshold_percent": 90}
                conduct_api_call(cl, OrganizationQuotaLimit, "PUT", params, body, 200)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_change_quota_limit"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["threshold_percent"] == 90
                assert metadata["previous_threshold_percent"] == 80

    def test_delete_quota_limit_logs_action(self, app):
        """
        Test that deleting a quota limit logs the org_delete_quota_limit action.
        """
        # Create a quota and limit first
        org = model.organization.get_organization("quotatestorg")
        quota = model.namespacequota.create_namespace_quota(org, 1073741824)  # 1 GiB
        limit = model.namespacequota.create_namespace_quota_limit(quota, "Reject", 100)
        limit_id = limit.id

        with client_with_identity("devtable", app) as cl:
            with patch("endpoints.api.namespacequota.log_action") as mock_log:
                params = {
                    "orgname": "quotatestorg",
                    "quota_id": quota.id,
                    "limit_id": limit_id,
                }
                conduct_api_call(cl, OrganizationQuotaLimit, "DELETE", params, None, 204)

                mock_log.assert_called_once()
                call_args = mock_log.call_args
                assert call_args[0][0] == "org_delete_quota_limit"
                assert call_args[0][1] == "quotatestorg"
                metadata = call_args[0][2]
                assert metadata["namespace"] == "quotatestorg"
                assert metadata["limit_id"] == limit_id
                assert metadata["type"] == "Reject"
                assert metadata["threshold_percent"] == 100
