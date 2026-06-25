# -*- coding: utf-8 -*-
"""
Prometheus registry readers shared by mirror health endpoints.
"""

import logging

from prometheus_client import REGISTRY

logger = logging.getLogger(__name__)


def get_metric_timestamps(metric_name: str, namespace=None):
    """
    Retrieve per-repository timestamps from a gauge metric in this process's registry.

    Returns a dict keyed by (namespace, repository) with unix timestamps as values.
    """
    timestamps = {}
    try:
        for metric in REGISTRY.collect():
            if metric.name != metric_name:
                continue
            for sample in metric.samples:
                if sample.name != metric_name:
                    continue
                sample_namespace = sample.labels.get("namespace")
                repository = sample.labels.get("repository")
                if namespace is not None and sample_namespace != namespace:
                    continue
                if sample_namespace and repository:
                    timestamps[(sample_namespace, repository)] = sample.value
            break
    except Exception as ex:
        logger.debug("Unable to read %s timestamps from registry: %s", metric_name, ex)
    return timestamps


def get_pending_tags_total(metric_name: str, namespace=None):
    """
    Sum pending-tags gauge values from this process's registry.

    When namespace is set, only samples for that namespace are included.
    """
    total = 0.0
    try:
        for metric in REGISTRY.collect():
            if metric.name != metric_name:
                continue
            for sample in metric.samples:
                if sample.name != metric_name:
                    continue
                if namespace is not None and sample.labels.get("namespace") != namespace:
                    continue
                total += float(sample.value)
            break
    except Exception as ex:
        logger.debug("Unable to read %s pending tags from registry: %s", metric_name, ex)
    return int(total) if total == int(total) else total


def get_namespace_gauge_value(metric_name: str, namespace: str, label_name: str = "namespace"):
    """
    Read a single-sample gauge value for a namespace label from this process's registry.
    """
    try:
        for metric in REGISTRY.collect():
            if metric.name != metric_name:
                continue
            for sample in metric.samples:
                if sample.name != metric_name:
                    continue
                if sample.labels.get(label_name) == namespace:
                    return sample.value
            break
    except Exception as ex:
        logger.debug("Unable to read %s for %s from registry: %s", metric_name, namespace, ex)
    return None


def get_mirror_workers_active_value():
    """Read quay_repository_mirror_workers_active from this process's Prometheus registry."""
    try:
        for metric in REGISTRY.collect():
            if metric.name != "quay_repository_mirror_workers_active":
                continue
            for sample in metric.samples:
                if sample.name != "quay_repository_mirror_workers_active":
                    continue
                return int(sample.value)
            break
    except Exception as ex:
        logger.debug("Unable to read mirror workers active gauge from registry: %s", ex)
    return 0
