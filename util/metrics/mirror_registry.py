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
import time
import urllib.error
import urllib.request
from typing import Dict, Tuple

from prometheus_client import REGISTRY
from prometheus_client.parser import (
    text_string_to_metric_families,  # type: ignore[import]
)

logger = logging.getLogger(__name__)

_PUSHGATEWAY_FETCH_TIMEOUT_SECONDS = 2
# Ignore PushGateway groupings not refreshed within this window (3x default 30s push interval).
_WORKERS_ACTIVE_MAX_AGE_SECONDS = 90
_PUSHGATEWAY_FAMILIES_CACHE_ATTR = "_mirror_registry_pushgateway_families"


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


def _request_cache():
    try:
        from flask import g, has_request_context

        if has_request_context():
            return g
    except Exception:
        pass
    return None


def _fetch_pushgateway_metric_families():
    cache = _request_cache()
    if cache is not None:
        cached = getattr(cache, _PUSHGATEWAY_FAMILIES_CACHE_ATTR, None)
        if cached is not None:
            return cached

    url = _get_pushgateway_url()
    if not url:
        families = []
    else:
        metrics_url = f"{url.rstrip('/')}/metrics"
        try:
            with urllib.request.urlopen(
                metrics_url, timeout=_PUSHGATEWAY_FETCH_TIMEOUT_SECONDS
            ) as resp:
                body = resp.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ValueError) as ex:
            logger.debug("Unable to fetch metrics from PushGateway at %s: %s", metrics_url, ex)
            families = []
        else:
            try:
                families = list(text_string_to_metric_families(body))
            except Exception as ex:
                logger.debug("Unable to parse PushGateway metrics from %s: %s", metrics_url, ex)
                families = []

    if cache is not None:
        setattr(cache, _PUSHGATEWAY_FAMILIES_CACHE_ATTR, families)
    return families


def _grouping_labels_key(labels):
    return frozenset(labels.items())


def _pushgateway_push_times(metric_families):
    push_times = {}
    for family in metric_families:
        if family.name != "push_time_seconds":
            continue
        for sample in family.samples:
            if sample.name == "push_time_seconds":
                push_times[_grouping_labels_key(sample.labels)] = float(sample.value)
    return push_times


def _is_fresh_pushgateway_grouping(labels, push_times, now):
    pushed_at = push_times.get(_grouping_labels_key(labels))
    if pushed_at is None:
        return False
    return (now - pushed_at) <= _WORKERS_ACTIVE_MAX_AGE_SECONDS


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
    timestamps: Dict[Tuple[str, str], float] = {}
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

    Sums fresh PushGateway groupings so API pods see cluster worker count without
    counting stale series left after worker shutdown.
    """
    if _should_read_pushgateway():
        families = _fetch_pushgateway_metric_families()
        if families:
            now = time.time()
            push_times = _pushgateway_push_times(families)
            total = 0
            for family in families:
                if family.name != "quay_repository_mirror_workers_active":
                    continue
                for sample in family.samples:
                    if sample.name != "quay_repository_mirror_workers_active":
                        continue
                    if _is_fresh_pushgateway_grouping(sample.labels, push_times, now):
                        total += int(sample.value)
            return total

    total = 0
    try:
        for sample in _iter_metric_samples("quay_repository_mirror_workers_active"):
            total += int(sample.value)
    except Exception as ex:
        logger.debug("Unable to read mirror workers active gauge: %s", ex)
    return total
