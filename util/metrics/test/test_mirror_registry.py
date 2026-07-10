# -*- coding: utf-8 -*-

import time
from unittest import mock

from flask import Flask

from util.metrics import mirror_registry


def _mock_urlopen(metrics_body):
    resp = mock.Mock(read=lambda: metrics_body.encode())
    context = mock.MagicMock()
    context.__enter__.return_value = resp
    context.__exit__.return_value = None
    return context


class TestIterMetricSamples:
    def test_pushgateway_path_yields_matching_samples(self):
        metrics_body = (
            "# TYPE quay_org_mirror_pending_tags gauge\n"
            'quay_org_mirror_pending_tags{namespace="coreos",repository="etcd"} 4\n'
            "# TYPE quay_repository_mirror_workers_active gauge\n"
            "quay_repository_mirror_workers_active 1\n"
        )
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
            ):
                with mock.patch("urllib.request.urlopen", return_value=_mock_urlopen(metrics_body)):
                    samples = list(
                        mirror_registry._iter_metric_samples("quay_org_mirror_pending_tags")
                    )
                    assert len(samples) == 1
                    assert samples[0].labels["repository"] == "etcd"
                    assert samples[0].value == 4.0

    def test_local_registry_fallback_when_pushgateway_disabled(self):
        metric = mock.Mock()
        metric.name = "quay_org_mirror_pending_tags"
        sample = mock.Mock()
        sample.name = "quay_org_mirror_pending_tags"
        sample.labels = {"namespace": "coreos", "repository": "etcd"}
        sample.value = 3.0
        metric.samples = [sample]

        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=False):
            with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                mock_registry.collect.return_value = [metric]
                samples = list(mirror_registry._iter_metric_samples("quay_org_mirror_pending_tags"))
                assert len(samples) == 1
                assert samples[0].value == 3.0


class TestGetMetricTimestamps:
    def test_namespace_filter_and_max_duplicate_series(self):
        metrics_body = (
            "# TYPE quay_org_mirror_last_sync_timestamp gauge\n"
            'quay_org_mirror_last_sync_timestamp{namespace="coreos",repository="etcd"} 100\n'
            'quay_org_mirror_last_sync_timestamp{namespace="coreos",repository="etcd"} 200\n'
            'quay_org_mirror_last_sync_timestamp{namespace="other",repository="app"} 50\n'
        )
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
            ):
                with mock.patch("urllib.request.urlopen", return_value=_mock_urlopen(metrics_body)):
                    result = mirror_registry.get_metric_timestamps(
                        "quay_org_mirror_last_sync_timestamp",
                        namespace="coreos",
                    )
                    assert result == {("coreos", "etcd"): 200}

    def test_skips_samples_missing_repository_label(self):
        metric = mock.Mock()
        metric.name = "quay_org_mirror_last_sync_timestamp"
        missing_repo = mock.Mock()
        missing_repo.name = "quay_org_mirror_last_sync_timestamp"
        missing_repo.labels = {"namespace": "coreos"}
        missing_repo.value = 100.0
        valid = mock.Mock()
        valid.name = "quay_org_mirror_last_sync_timestamp"
        valid.labels = {"namespace": "coreos", "repository": "etcd"}
        valid.value = 150.0
        metric.samples = [missing_repo, valid]

        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=False):
            with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                mock_registry.collect.return_value = [metric]
                result = mirror_registry.get_metric_timestamps(
                    "quay_org_mirror_last_sync_timestamp"
                )
                assert result == {("coreos", "etcd"): 150}


class TestGetPendingTagsTotal:
    def test_sums_with_namespace_filter(self):
        metrics_body = (
            "# TYPE quay_org_mirror_pending_tags gauge\n"
            'quay_org_mirror_pending_tags{namespace="coreos",repository="etcd"} 4\n'
            'quay_org_mirror_pending_tags{namespace="coreos",repository="flannel"} 2\n'
            'quay_org_mirror_pending_tags{namespace="other",repository="app"} 9\n'
        )
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
            ):
                with mock.patch("urllib.request.urlopen", return_value=_mock_urlopen(metrics_body)):
                    assert (
                        mirror_registry.get_pending_tags_total(
                            "quay_org_mirror_pending_tags",
                            namespace="coreos",
                        )
                        == 6
                    )
                    assert (
                        mirror_registry.get_pending_tags_total("quay_org_mirror_pending_tags") == 15
                    )

    def test_returns_int_for_whole_number_total(self):
        metric = mock.Mock()
        metric.name = "quay_org_mirror_pending_tags"
        sample = mock.Mock()
        sample.name = "quay_org_mirror_pending_tags"
        sample.labels = {"namespace": "coreos", "repository": "etcd"}
        sample.value = 5.0
        metric.samples = [sample]

        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=False):
            with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                mock_registry.collect.return_value = [metric]
                result = mirror_registry.get_pending_tags_total("quay_org_mirror_pending_tags")
                assert result == 5
                assert isinstance(result, int)

    def test_returns_float_for_fractional_total(self):
        metric = mock.Mock()
        metric.name = "quay_org_mirror_pending_tags"
        s1 = mock.Mock()
        s1.name = "quay_org_mirror_pending_tags"
        s1.labels = {"namespace": "coreos", "repository": "a"}
        s1.value = 1.5
        s2 = mock.Mock()
        s2.name = "quay_org_mirror_pending_tags"
        s2.labels = {"namespace": "coreos", "repository": "b"}
        s2.value = 1.0
        metric.samples = [s1, s2]

        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=False):
            with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                mock_registry.collect.return_value = [metric]
                result = mirror_registry.get_pending_tags_total("quay_org_mirror_pending_tags")
                assert result == 2.5
                assert isinstance(result, float)


class TestGetNamespaceGaugeValue:
    def test_returns_none_when_no_matching_samples(self):
        with mock.patch.object(mirror_registry, "_iter_metric_samples", return_value=iter([])):
            assert (
                mirror_registry.get_namespace_gauge_value(
                    "quay_org_mirror_last_discovery_status",
                    "coreos",
                )
                is None
            )

    def test_returns_max_for_duplicate_namespace_series(self):
        s1 = mock.Mock(labels={"namespace": "coreos"}, value=0.0)
        s2 = mock.Mock(labels={"namespace": "coreos"}, value=2.0)
        s3 = mock.Mock(labels={"namespace": "other"}, value=1.0)
        with mock.patch.object(
            mirror_registry,
            "_iter_metric_samples",
            return_value=iter([s1, s2, s3]),
        ):
            assert (
                mirror_registry.get_namespace_gauge_value(
                    "quay_org_mirror_last_discovery_status",
                    "coreos",
                )
                == 2.0
            )


class TestGetMirrorWorkersActiveValue:
    def test_sums_fresh_pushgateway_samples(self):
        now = time.time()
        metrics_body = (
            "# TYPE push_time_seconds gauge\n"
            f'push_time_seconds{{pid="1"}} {now}\n'
            f'push_time_seconds{{pid="2"}} {now}\n'
            "# TYPE quay_repository_mirror_workers_active gauge\n"
            'quay_repository_mirror_workers_active{pid="1"} 1\n'
            'quay_repository_mirror_workers_active{pid="2"} 1\n'
        )
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
            ):
                with mock.patch("urllib.request.urlopen", return_value=_mock_urlopen(metrics_body)):
                    assert mirror_registry.get_mirror_workers_active_value() == 2

    def test_ignores_stale_pushgateway_samples(self):
        now = time.time()
        stale = now - 200
        metrics_body = (
            "# TYPE push_time_seconds gauge\n"
            f'push_time_seconds{{pid="1"}} {stale}\n'
            f'push_time_seconds{{pid="2"}} {now}\n'
            "# TYPE quay_repository_mirror_workers_active gauge\n"
            'quay_repository_mirror_workers_active{pid="1"} 1\n'
            'quay_repository_mirror_workers_active{pid="2"} 1\n'
        )
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
            ):
                with mock.patch("urllib.request.urlopen", return_value=_mock_urlopen(metrics_body)):
                    assert mirror_registry.get_mirror_workers_active_value() == 1

    def test_local_registry_fallback(self):
        sample = mock.Mock()
        sample.name = "quay_repository_mirror_workers_active"
        sample.labels = {}
        sample.value = 1
        metric = mock.Mock()
        metric.name = "quay_repository_mirror_workers_active"
        metric.samples = [sample]

        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=False):
            with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                mock_registry.collect.return_value = [metric]
                assert mirror_registry.get_mirror_workers_active_value() == 1


class TestPushgatewayRequestCache:
    def test_fetch_pushgateway_metric_families_cached_within_request(self):
        metrics_body = (
            "# TYPE quay_org_mirror_pending_tags gauge\n"
            'quay_org_mirror_pending_tags{namespace="coreos",repository="etcd"} 1\n'
            "# TYPE quay_org_mirror_last_sync_timestamp gauge\n"
            'quay_org_mirror_last_sync_timestamp{namespace="coreos",repository="etcd"} 10\n'
        )
        with Flask(__name__).test_request_context():
            with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
                with mock.patch.object(
                    mirror_registry, "_get_pushgateway_url", return_value="http://pg:9091"
                ):
                    with mock.patch(
                        "urllib.request.urlopen",
                        return_value=_mock_urlopen(metrics_body),
                    ) as urlopen:
                        mirror_registry.get_pending_tags_total("quay_org_mirror_pending_tags")
                        mirror_registry.get_metric_timestamps("quay_org_mirror_last_sync_timestamp")
                        mirror_registry.get_mirror_workers_active_value()
                        assert urlopen.call_count == 1

    def test_pushgateway_empty_falls_back_to_local_registry(self):
        with mock.patch.object(mirror_registry, "_should_read_pushgateway", return_value=True):
            with mock.patch.object(
                mirror_registry, "_fetch_pushgateway_metric_families", return_value=[]
            ):
                with mock.patch.object(mirror_registry, "REGISTRY") as mock_registry:
                    metric = mock.Mock()
                    metric.name = "quay_org_mirror_pending_tags"
                    sample = mock.Mock()
                    sample.name = "quay_org_mirror_pending_tags"
                    sample.labels = {"namespace": "coreos", "repository": "etcd"}
                    sample.value = 3.0
                    metric.samples = [sample]
                    mock_registry.collect.return_value = [metric]

                    assert (
                        mirror_registry.get_pending_tags_total(
                            "quay_org_mirror_pending_tags",
                            namespace="coreos",
                        )
                        == 3
                    )
