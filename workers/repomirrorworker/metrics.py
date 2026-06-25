# -*- coding: utf-8 -*-
"""
Shared mirror metric helpers for repository and organization mirroring.

This module is intentionally independent of workers/repomirrorworker/__init__.py so
org-mirror metrics work can land without refactoring repo-mirror code in that file.
"""

import time
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram


def map_failure_to_reason(error_message: str) -> str:
    """
    Map skopeo / sync error messages to standardized failure reasons for metrics.
    """
    error_lower = str(error_message).lower()

    if "auth" in error_lower or "unauthorized" in error_lower or "forbidden" in error_lower:
        return "auth_failed"
    if "timeout" in error_lower or "timed out" in error_lower:
        return "network_timeout"
    if "not found" in error_lower or "404" in error_lower:
        return "not_found"
    if "500" in error_lower or "503" in error_lower or "registry" in error_lower:
        return "registry_error"
    if "manifest" in error_lower or "digest" in error_lower or "layer" in error_lower:
        return "image_error"
    if "permission" in error_lower or "denied" in error_lower:
        return "permission_denied"
    if "tls" in error_lower or "certificate" in error_lower or "ssl" in error_lower:
        return "config_error"
    if "decrypt" in error_lower or "proxy" in error_lower:
        return "config_error"
    return "unknown"


def map_org_discovery_failure_to_reason(error_or_response) -> str:
    """
    Map registry API discovery errors to standardized failure reasons for metrics.
    """
    error_lower = str(error_or_response).lower()

    if "auth" in error_lower or "unauthorized" in error_lower or "401" in error_lower:
        return "auth_failed"
    if "forbidden" in error_lower or "403" in error_lower:
        return "permission_denied"
    if "timeout" in error_lower or "timed out" in error_lower:
        return "network_timeout"
    if "429" in error_lower or "rate limit" in error_lower or "too many requests" in error_lower:
        return "rate_limited"
    if "not found" in error_lower or "404" in error_lower:
        return "not_found"
    if "500" in error_lower or "502" in error_lower or "503" in error_lower:
        return "api_error"
    if "pagination" in error_lower or "next page" in error_lower or "page token" in error_lower:
        return "pagination_error"
    if "json" in error_lower or "malformed" in error_lower:
        return "api_error"
    if "url" in error_lower or "reference" in error_lower or "config" in error_lower:
        return "config_error"
    return "unknown"


def update_sync_started(
    pending_gauge: Gauge,
    status_gauge: Gauge,
    timestamp_gauge: Gauge,
    namespace: str,
    repository: str,
    tag_count: int,
    start_time: Optional[float] = None,
):
    """Record sync start: in-progress status, timestamp, and initial pending tag count."""
    when = start_time if start_time is not None else time.time()
    status_gauge.labels(
        namespace=namespace,
        repository=repository,
        last_error_reason="",
    ).set(2)
    timestamp_gauge.labels(namespace=namespace, repository=repository).set(when)
    pending_gauge.labels(namespace=namespace, repository=repository).set(tag_count)


def update_sync_tag_processed(
    pending_gauge: Gauge,
    namespace: str,
    repository: str,
    remaining: int,
):
    """Update pending tag count after processing a tag."""
    pending_gauge.labels(namespace=namespace, repository=repository).set(remaining)


def update_sync_finished(
    pending_gauge: Gauge,
    status_gauge: Gauge,
    complete_gauge: Gauge,
    timestamp_gauge: Gauge,
    failures_counter: Counter,
    namespace: str,
    repository: str,
    success: bool,
    failure_reason: Optional[str] = None,
    include_repository_label: bool = True,
):
    """
    Record final sync outcome for gauges and optionally increment the failure counter.

    Counter increments use namespace-only labels when include_repository_label is False.
    """
    pending_gauge.labels(namespace=namespace, repository=repository).set(0)
    status_value = 1 if success else 0
    error_reason = "" if success else (failure_reason or "unknown")

    status_gauge.labels(
        namespace=namespace,
        repository=repository,
        last_error_reason="",
    ).set(status_value)
    if error_reason:
        status_gauge.labels(
            namespace=namespace,
            repository=repository,
            last_error_reason=error_reason,
        ).set(status_value)

    complete_gauge.labels(namespace=namespace, repository=repository).set(1 if success else 0)

    if not success:
        counter_labels = {"namespace": namespace, "reason": error_reason}
        if include_repository_label:
            counter_labels["repository"] = repository
        failures_counter.labels(**counter_labels).inc()


def update_sync_failed(
    pending_gauge: Gauge,
    status_gauge: Gauge,
    complete_gauge: Gauge,
    timestamp_gauge: Gauge,
    failures_counter: Counter,
    namespace: str,
    repository: str,
    failure_reason: Optional[str],
    include_repository_label: bool = False,
):
    """Record an early sync failure before tag processing completes."""
    update_sync_finished(
        pending_gauge,
        status_gauge,
        complete_gauge,
        timestamp_gauge,
        failures_counter,
        namespace,
        repository,
        success=False,
        failure_reason=failure_reason,
        include_repository_label=include_repository_label,
    )


def update_discovery_started(
    status_gauge: Gauge,
    timestamp_gauge: Gauge,
    namespace: str,
    start_time: Optional[float] = None,
):
    """Record discovery start: in-progress status and timestamp."""
    when = start_time if start_time is not None else time.time()
    status_gauge.labels(namespace=namespace).set(2)
    timestamp_gauge.labels(namespace=namespace).set(when)


def update_discovery_finished(
    status_gauge: Gauge,
    timestamp_gauge: Gauge,
    namespace: str,
    success: bool,
    start_time: Optional[float] = None,
):
    """Record discovery completion status and refresh timestamp."""
    when = start_time if start_time is not None else time.time()
    status_gauge.labels(namespace=namespace).set(1 if success else 0)
    timestamp_gauge.labels(namespace=namespace).set(when)
