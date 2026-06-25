# -*- coding: utf-8 -*-

import pytest
from prometheus_client import REGISTRY

from workers.repomirrorworker import metrics as mirror_metrics


class TestMapFailureToReason:
    def test_auth_failed(self):
        assert mirror_metrics.map_failure_to_reason("unauthorized access") == "auth_failed"

    def test_network_timeout(self):
        assert mirror_metrics.map_failure_to_reason("connection timed out") == "network_timeout"

    def test_not_found(self):
        assert mirror_metrics.map_failure_to_reason("manifest not found 404") == "not_found"

    def test_unknown(self):
        assert mirror_metrics.map_failure_to_reason("something else") == "unknown"


class TestMapOrgDiscoveryFailureToReason:
    def test_rate_limited(self):
        assert mirror_metrics.map_org_discovery_failure_to_reason("429 Too Many Requests") == (
            "rate_limited"
        )

    def test_api_error(self):
        assert mirror_metrics.map_org_discovery_failure_to_reason("503 service unavailable") == (
            "api_error"
        )


class TestUpdateSyncFinished:
    def test_counter_omits_repository_label_when_requested(self):
        from workers.repomirrorworker.org_mirror_metrics import (
            org_mirror_last_sync_status,
            org_mirror_last_sync_timestamp,
            org_mirror_sync_complete,
            org_mirror_sync_failures_total,
            org_mirror_tags_pending,
        )

        before = {
            sample.labels.get("namespace"): sample.value
            for metric in REGISTRY.collect()
            if metric.name == "quay_org_mirror_sync_failures_total"
            for sample in metric.samples
            if sample.name == "quay_org_mirror_sync_failures_total"
            and sample.labels.get("namespace") == "cardinality-test"
        }

        mirror_metrics.update_sync_finished(
            org_mirror_tags_pending,
            org_mirror_last_sync_status,
            org_mirror_sync_complete,
            org_mirror_last_sync_timestamp,
            org_mirror_sync_failures_total,
            "cardinality-test",
            "repo-a",
            success=False,
            failure_reason="auth_failed",
            include_repository_label=False,
        )

        after_samples = [
            sample
            for metric in REGISTRY.collect()
            if metric.name == "quay_org_mirror_sync_failures_total"
            for sample in metric.samples
            if sample.name == "quay_org_mirror_sync_failures_total"
            and sample.labels.get("namespace") == "cardinality-test"
            and sample.labels.get("reason") == "auth_failed"
        ]
        assert after_samples
        assert "repository" not in after_samples[0].labels
