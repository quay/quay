# -*- coding: utf-8 -*-
"""
Prometheus registry readers shared by mirror health endpoints.

Mirror worker metrics are pushed to PushGateway from separate processes. Health
APIs run in the Quay app process, so these helpers prefer scraping
PROMETHEUS_PUSHGATEWAY_URL and fall back to the in-process REGISTRY when the
gateway is unavailable (tests, misconfiguration).
"""

import logging
import os
import urllib.error
import urllib.request

from prometheus_client import REGISTRY
from prometheus_client.parser import text_string_to_metric_families

logger = logging.getLogger(__name__)

_PUSHGATEWAY_FETCH_TIMEOUT_SECONDS = 2


def _get_pushgateway_url():
    try:
        from app import app

        return app.config.get("PROMETHEUS_PUSHGATEWAY_URL")
    except Exception:
        return None


def _should_read_pushgateway():
    if os.getenv("TEST", "false").lower() == "true":
        return False
    return bool(_get_pushgateway_url())


def _fetch_pushgateway_metric_families():
    url = _get_pushgateway_url()
    if not url:
        return []

    metrics_url = f"{url.rstrip('/')}/metrics"
    try:
        with urllib.request.urlopen(
            metrics_url, timeout=_PUSHGATEWAY_FETCH_TIMEOUT_SECONDS
        ) as resp:
            body = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, ValueError) as ex:
        logger.debug("Unable to fetch metrics from PushGateway at %s: %s", metrics_url, ex)
        return []

    try:
        return list(text_string_to_metric_families(body))
    except Exception as ex:
        logger.debug("Unable to parse PushGateway metrics from %s: %s", metrics_url, ex)
        return []


def _iter_metric_samples(metric_name):
    """
    Yield metric samples for metric_name from PushGateway when configured, else REGISTRY.
    """
    if _should_read_pushgateway():
        families = _fetch_pushgateway_metric_families()
        if families:
            for family in families:
                if family.name != metric_name:
                    continue
                for sample in family.samples:
                    if sample.name == metric_name:
                        yield sample
            return

    try:
        for metric in REGISTRY.collect():
            if metric.name != metric_name:
                continue
            for sample in metric.samples:
                if sample.name == metric_name:
                    yield sample
            break
    except Exception as ex:
        logger.debug("Unable to read %s from local registry: %s", metric_name, ex)


def get_metric_timestamps(metric_name: str, namespace=None):
    """
    Retrieve per-repository timestamps from mirror metrics.

    Returns a dict keyed by (namespace, repository) with unix timestamps as values.
    """
    timestamps = {}
    try:
        for sample in _iter_metric_samples(metric_name):
            sample_namespace = sample.labels.get("namespace")
            repository = sample.labels.get("repository")
            if namespace is not None and sample_namespace != namespace:
                continue
            if sample_namespace and repository:
                key = (sample_namespace, repository)
                value = sample.value
                if key in timestamps:
                    timestamps[key] = max(timestamps[key], value)
                else:
                    timestamps[key] = value
    except Exception as ex:
        logger.debug("Unable to read %s timestamps: %s", metric_name, ex)
    return timestamps


def get_pending_tags_total(metric_name: str, namespace=None):
    """
    Sum pending-tags gauge values from mirror metrics.

    When namespace is set, only samples for that namespace are included.
    """
    total = 0.0
    try:
        for sample in _iter_metric_samples(metric_name):
            if namespace is not None and sample.labels.get("namespace") != namespace:
                continue
            total += float(sample.value)
    except Exception as ex:
        logger.debug("Unable to read %s pending tags: %s", metric_name, ex)
    return int(total) if total == int(total) else total


def get_namespace_gauge_value(metric_name: str, namespace: str, label_name: str = "namespace"):
    """
    Read a gauge value for a namespace label from mirror metrics.

    When multiple worker processes report the same series, returns the maximum value.
    """
    values = []
    try:
        for sample in _iter_metric_samples(metric_name):
            if sample.labels.get(label_name) == namespace:
                values.append(sample.value)
    except Exception as ex:
        logger.debug("Unable to read %s for %s: %s", metric_name, namespace, ex)
    if not values:
        return None
    return max(values)


def get_mirror_workers_active_value():
    """
    Read quay_repository_mirror_workers_active from mirror metrics.

    Sums samples across PushGateway targets so API pods see cluster worker count.
    """
    total = 0
    try:
        for sample in _iter_metric_samples("quay_repository_mirror_workers_active"):
            total += int(sample.value)
    except Exception as ex:
        logger.debug("Unable to read mirror workers active gauge: %s", ex)
    return total
