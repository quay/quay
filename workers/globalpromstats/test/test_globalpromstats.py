import unittest
from collections import namedtuple
from unittest.mock import patch

from prometheus_client import REGISTRY

from workers.globalpromstats.globalpromstats import GlobalPrometheusStatsWorker

MockRegistrySize = namedtuple("MockRegistrySize", ["id", "queued", "running", "size_bytes"])


class TestGlobalPrometheusStatsWorker(unittest.TestCase):
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count", return_value=20
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.organization.get_active_org_count",
        return_value=5,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_estimated_robot_count",
        return_value=2,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_registry_size",
        return_value=MockRegistrySize("1", False, False, 100000),
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
        return_value=[
            {"id": "1", "username": "test_org1", "organization": False, "size_bytes": 1000},
            {"id": "2", "username": "test_org2", "organization": True, "size_bytes": 2000},
            {"id": "3", "username": "test_org3", "organization": True, "size_bytes": 3000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[
            {"id": "4", "name": "repo1", "namespace": "test_org1", "size_bytes": 4000},
            {"id": "5", "name": "repo2", "namespace": "test_org2", "size_bytes": 5000},
            {"id": "6", "name": "repo3", "namespace": "test_org3", "size_bytes": 6000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[
            {"id": "1", "username": "test_org1", "limit_bytes": 10000},
            {"id": "3", "username": "test_org3", "limit_bytes": 20000},
        ],
    )
    def test_report_stats(
        self,
        mock_get_registry_size,
        mock_get_all_repository_sizes,
        mock_get_namespaces_with_quotas,
        mock_get_all_namespace_sizes,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
    ):
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(REGISTRY.get_sample_value("quay_repository_rows"), 10)
            self.assertEqual(REGISTRY.get_sample_value("quay_user_rows"), 20)
            self.assertEqual(REGISTRY.get_sample_value("quay_org_rows"), 5)
            self.assertEqual(REGISTRY.get_sample_value("quay_robot_rows"), 2)
            self.assertEqual(REGISTRY.get_sample_value("registry_total_used_bytes"), 100000)

            # used org bytes calculation
            org1_used_bytes = REGISTRY.get_sample_value(
                "namespace_stats_used_bytes", {"namespace": "test_org1", "entity_type": "user"}
            )
            self.assertEqual(org1_used_bytes, 1000)

            org2_used_bytes = REGISTRY.get_sample_value(
                "namespace_stats_used_bytes",
                {"namespace": "test_org2", "entity_type": "organization"},
            )
            self.assertEqual(org2_used_bytes, 2000)

            org3_used_bytes = REGISTRY.get_sample_value(
                "namespace_stats_used_bytes",
                {"namespace": "test_org2", "entity_type": "organization"},
            )
            self.assertEqual(org3_used_bytes, 2000)

            # used repo bytes calculation
            repo1_used_bytes = REGISTRY.get_sample_value(
                "repository_stats_used_bytes",
                {"repository": "repo1", "namespace": "test_org1"},
            )
            self.assertEqual(repo1_used_bytes, 4000)

            repo2_used_bytes = REGISTRY.get_sample_value(
                "repository_stats_used_bytes",
                {"repository": "repo2", "namespace": "test_org2"},
            )
            self.assertEqual(repo2_used_bytes, 5000)

            repo3_used_bytes = REGISTRY.get_sample_value(
                "repository_stats_used_bytes",
                {"repository": "repo3", "namespace": "test_org3"},
            )
            self.assertEqual(repo3_used_bytes, 6000)

            # quota stats
            org1_capacity_bytes = REGISTRY.get_sample_value(
                "namespace_quota_stats_capacity_bytes",
                {"namespace": "test_org1", "entity_type": "user"},
            )
            self.assertEqual(org1_capacity_bytes, 10000)

            org3_capacity_bytes = REGISTRY.get_sample_value(
                "namespace_quota_stats_capacity_bytes",
                {"namespace": "test_org3", "entity_type": "organization"},
            )
            self.assertEqual(org3_capacity_bytes, 20000)

            org1_available_bytes = REGISTRY.get_sample_value(
                "namespace_quota_stats_available_bytes",
                {"namespace": "test_org1", "entity_type": "user"},
            )
            self.assertEqual(org1_available_bytes, 10000 - 1000)

            org3_available_bytes = REGISTRY.get_sample_value(
                "namespace_quota_stats_available_bytes",
                {"namespace": "test_org3", "entity_type": "organization"},
            )
            self.assertEqual(org3_available_bytes, 20000 - 3000)
