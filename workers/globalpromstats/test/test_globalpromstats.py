import unittest
from collections import namedtuple
from unittest.mock import patch

from prometheus_client import REGISTRY

from test.fixtures import *
from workers.globalpromstats.globalpromstats import GlobalPrometheusStatsWorker

MockRegistrySize = namedtuple("MockRegistrySize", ["id", "queued", "running", "size_bytes"])


def test_globalpromstats(initialized_db):
    worker = GlobalPrometheusStatsWorker()
    worker._report_stats()


class TestGlobalPrometheusStatsWorkerQuotaMetrics(unittest.TestCase):
    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
            {
                "id": 1,
                "username": "test_org1",
                "organization": False,
                "size_bytes": 1000,
            },
            {
                "id": 2,
                "username": "test_org2",
                "organization": True,
                "size_bytes": 2000,
            },
            {
                "id": 3,
                "username": "test_org3",
                "organization": True,
                "size_bytes": 3000,
            },
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[
            {"id": 4, "name": "repo1", "namespace": "test_org1", "size_bytes": 4000},
            {"id": 5, "name": "repo2", "namespace": "test_org2", "size_bytes": 5000},
            {"id": 6, "name": "repo3", "namespace": "test_org3", "size_bytes": 6000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[
            {"id": 1, "username": "test_org1", "organization": False, "limit_bytes": 10000},
            {"id": 3, "username": "test_org3", "organization": True, "limit_bytes": 20000},
        ],
    )
    def test_report_stats_with_quota_metrics(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(REGISTRY.get_sample_value("quay_repository_rows"), 10)
            self.assertEqual(REGISTRY.get_sample_value("quay_user_rows"), 20)
            self.assertEqual(REGISTRY.get_sample_value("quay_org_rows"), 5)
            self.assertEqual(REGISTRY.get_sample_value("quay_robot_rows"), 2)
            self.assertEqual(REGISTRY.get_sample_value("quay_registry_total_used_bytes"), 100000)

            # namespace used bytes
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "test_org1", "entity_type": "user"},
                ),
                1000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "test_org2", "entity_type": "organization"},
                ),
                2000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "test_org3", "entity_type": "organization"},
                ),
                3000,
            )

            # repository used bytes
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo1", "namespace": "test_org1"},
                ),
                4000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo2", "namespace": "test_org2"},
                ),
                5000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo3", "namespace": "test_org3"},
                ),
                6000,
            )

            # namespace quota capacity (only namespaces with quotas)
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_capacity_bytes",
                    {"namespace": "test_org1", "entity_type": "user"},
                ),
                10000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_capacity_bytes",
                    {"namespace": "test_org3", "entity_type": "organization"},
                ),
                20000,
            )

            # namespace quota available bytes
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_available_bytes",
                    {"namespace": "test_org1", "entity_type": "user"},
                ),
                10000 - 1000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_available_bytes",
                    {"namespace": "test_org3", "entity_type": "organization"},
                ),
                20000 - 3000,
            )

            # org2 should NOT have quota metrics (no quota defined)
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_capacity_bytes",
                    {"namespace": "test_org2", "entity_type": "organization"},
                )
            )
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_available_bytes",
                    {"namespace": "test_org2", "entity_type": "organization"},
                )
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.organization.get_active_org_count",
        return_value=5,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_estimated_robot_count",
        return_value=2,
    )
    def test_report_stats_without_quota_metrics(
        self,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", False):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(REGISTRY.get_sample_value("quay_repository_rows"), 10)
            self.assertEqual(REGISTRY.get_sample_value("quay_user_rows"), 20)
            self.assertEqual(REGISTRY.get_sample_value("quay_org_rows"), 5)
            self.assertEqual(REGISTRY.get_sample_value("quay_robot_rows"), 2)

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        return_value=None,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[],
    )
    def test_report_stats_quota_metrics_empty_data(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(REGISTRY.get_sample_value("quay_repository_rows"), 10)
            # When registry size is None, the gauge should be set to 0
            self.assertEqual(REGISTRY.get_sample_value("quay_registry_total_used_bytes"), 0)

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        return_value=MockRegistrySize("1", False, False, 50000),
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
        return_value=[
            {
                "id": 1,
                "username": "overquota_org",
                "organization": True,
                "size_bytes": 15000,
            },
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[
            {"id": 1, "username": "overquota_org", "organization": True, "limit_bytes": 10000},
        ],
    )
    def test_report_stats_quota_exceeded(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "overquota_org", "entity_type": "organization"},
                ),
                15000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_capacity_bytes",
                    {"namespace": "overquota_org", "entity_type": "organization"},
                ),
                10000,
            )
            # Available should be 0 when usage exceeds capacity
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_available_bytes",
                    {"namespace": "overquota_org", "entity_type": "organization"},
                ),
                0,
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        side_effect=Exception("DB error"),
    )
    def test_report_stats_error_isolation(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Failure in one populate function should not block others."""
        with (
            patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True),
            patch(
                "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
                return_value=[],
            ),
            patch(
                "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
                return_value=[
                    {"id": 4, "name": "repo1", "namespace": "test_org1", "size_bytes": 4000},
                ],
            ),
        ):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            # populate_namespace_quota_stats raises but repo and registry should still work
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo1", "namespace": "test_org1"},
                ),
                4000,
            )
            self.assertEqual(REGISTRY.get_sample_value("quay_registry_total_used_bytes"), 100000)

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
            {"id": 1, "username": "org1", "organization": True, "size_bytes": 5000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[
            {"id": 4, "name": "repo1", "namespace": "org1", "size_bytes": 4000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[
            {"id": 1, "username": "org1", "organization": True, "limit_bytes": 10000},
        ],
    )
    def test_stale_metrics_cleared(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Metrics from deleted namespaces/repos should be cleared on next cycle."""
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            # First run: org1 and repo1 should have metrics
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "org1", "entity_type": "organization"},
                ),
                5000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo1", "namespace": "org1"},
                ),
                4000,
            )

        # Second run with empty data: stale metrics should be cleared
        with (
            patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True),
            patch(
                "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
                return_value=[],
            ),
            patch(
                "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
                return_value=[],
            ),
            patch(
                "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
                return_value=[],
            ),
            patch(
                "workers.globalpromstats.globalpromstats.model.quota.get_registry_size",
                return_value=MockRegistrySize("1", False, False, 100000),
            ),
        ):
            worker._report_stats()

            # After clearing, the old labels should no longer exist
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "org1", "entity_type": "organization"},
                )
            )
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo1", "namespace": "org1"},
                )
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        side_effect=Exception("Repo DB error"),
    )
    def test_report_stats_repo_error_isolation(
        self,
        mock_get_all_repository_sizes,
        mock_get_namespaces_with_quotas,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Failure in populate_repo_quota_stats should not block registry stats."""
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(REGISTRY.get_sample_value("quay_registry_total_used_bytes"), 100000)

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        side_effect=Exception("Registry DB error"),
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_namespace_sizes",
        return_value=[
            {"id": 1, "username": "org1", "organization": True, "size_bytes": 5000},
        ],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[
            {"id": 4, "name": "repo1", "namespace": "org1", "size_bytes": 4000},
        ],
    )
    def test_report_stats_registry_error_isolation(
        self,
        mock_get_all_repository_sizes,
        mock_get_namespaces_with_quotas,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Failure in populate_registry_size_stats should not block other quota stats."""
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "org1", "entity_type": "organization"},
                ),
                5000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo1", "namespace": "org1"},
                ),
                4000,
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[
            {"id": 10, "username": "new_org", "organization": True, "limit_bytes": 50000},
        ],
    )
    def test_quota_without_size_row(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Quota metrics should be emitted even without a QuotaNamespaceSize row."""
        with patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            # No namespace size row means no used_bytes metric
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "new_org", "entity_type": "organization"},
                )
            )
            # But capacity and available should still be emitted (available = limit)
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_capacity_bytes",
                    {"namespace": "new_org", "entity_type": "organization"},
                ),
                50000,
            )
            self.assertEqual(
                REGISTRY.get_sample_value(
                    "quay_namespace_quota_stats_available_bytes",
                    {"namespace": "new_org", "entity_type": "organization"},
                ),
                50000,
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
        return_value=[],
    )
    def test_repo_metrics_limit(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Repository metrics should be bounded at the generator level."""
        all_repos = [
            {"id": i, "name": f"repo{i}", "namespace": "org1", "size_bytes": 100 * i}
            for i in range(1, 6)
        ]
        mock_get_all_repository_sizes.side_effect = lambda batch_size=500, max_rows=0: iter(
            all_repos[:max_rows] if max_rows > 0 else all_repos
        )

        with (
            patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True),
            patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS_REPOS_LIMIT", 3),
        ):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            # Verify max_rows was passed to the generator
            mock_get_all_repository_sizes.assert_called_with(max_rows=3)

            # First 3 repos should have metrics
            for i in range(1, 4):
                self.assertEqual(
                    REGISTRY.get_sample_value(
                        "quay_repository_stats_used_bytes",
                        {"repository": f"repo{i}", "namespace": "org1"},
                    ),
                    100 * i,
                )
            # Repos beyond the limit should not have metrics
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo4", "namespace": "org1"},
                )
            )
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_repository_stats_used_bytes",
                    {"repository": "repo5", "namespace": "org1"},
                )
            )

    @patch(
        "workers.globalpromstats.globalpromstats.get_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.get_enabled_org_mirror_config_count",
        return_value=0,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.repository.get_estimated_repository_count",
        return_value=10,
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.user.get_active_user_count",
        return_value=20,
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
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.quota.get_all_repository_sizes",
        return_value=[],
    )
    @patch(
        "workers.globalpromstats.globalpromstats.model.namespacequota.get_namespaces_with_quotas",
    )
    def test_namespace_metrics_limit(
        self,
        mock_get_namespaces_with_quotas,
        mock_get_all_repository_sizes,
        mock_get_all_namespace_sizes,
        mock_get_registry_size,
        mock_get_estimated_robot_count,
        mock_get_active_org_count,
        mock_get_active_user_count,
        mock_get_estimated_repository_count,
        mock_get_enabled_org_mirror_config_count,
        mock_get_org_mirror_config_count,
    ):
        """Namespace metrics should be bounded at the generator level."""
        all_ns_sizes = [
            {
                "id": i,
                "username": f"ns{i}",
                "organization": True,
                "size_bytes": 1000 * i,
            }
            for i in range(1, 6)
        ]
        all_ns_quotas = [
            {
                "id": i,
                "username": f"ns{i}",
                "organization": True,
                "limit_bytes": 50000,
            }
            for i in range(1, 6)
        ]
        mock_get_all_namespace_sizes.side_effect = lambda batch_size=500, max_rows=0: iter(
            all_ns_sizes[:max_rows] if max_rows > 0 else all_ns_sizes
        )
        mock_get_namespaces_with_quotas.side_effect = lambda batch_size=500, max_rows=0: iter(
            all_ns_quotas[:max_rows] if max_rows > 0 else all_ns_quotas
        )

        with (
            patch("workers.globalpromstats.globalpromstats.QUOTA_METRICS", True),
            patch(
                "workers.globalpromstats.globalpromstats.QUOTA_METRICS_NAMESPACES_LIMIT",
                3,
            ),
        ):
            worker = GlobalPrometheusStatsWorker()
            worker._report_stats()

            # Verify max_rows was passed to both generators
            mock_get_all_namespace_sizes.assert_called_with(max_rows=3)
            mock_get_namespaces_with_quotas.assert_called_with(max_rows=3)

            # First 3 namespaces should have metrics
            for i in range(1, 4):
                self.assertEqual(
                    REGISTRY.get_sample_value(
                        "quay_namespace_stats_used_bytes",
                        {"namespace": f"ns{i}", "entity_type": "organization"},
                    ),
                    1000 * i,
                )
            # Namespaces beyond the limit should not have metrics
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "ns4", "entity_type": "organization"},
                )
            )
            self.assertIsNone(
                REGISTRY.get_sample_value(
                    "quay_namespace_stats_used_bytes",
                    {"namespace": "ns5", "entity_type": "organization"},
                )
            )
