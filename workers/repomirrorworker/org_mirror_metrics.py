# -*- coding: utf-8 -*-
"""
Organization mirror Prometheus metrics and worker instrumentation hooks.

Metric definitions and updates live here so workers/repomirrorworker/__init__.py
does not need to be refactored for org-mirror observability work.
"""

import logging

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

org_mirror_tags_pending = Gauge(
    "quay_org_mirror_pending_tags",
    "Total number of tags pending synchronization for each org-mirrored repository",
    labelnames=["namespace", "repository"],
)

org_mirror_last_sync_status = Gauge(
    "quay_org_mirror_last_sync_status",
    "Status of the last org mirror sync attempt (0=failed, 1=success, 2=in_progress)",
    labelnames=["namespace", "repository", "last_error_reason"],
)

org_mirror_sync_complete = Gauge(
    "quay_org_mirror_sync_complete",
    "Indicates if all tags have been successfully synchronized for an org-mirrored repo",
    labelnames=["namespace", "repository"],
)

org_mirror_sync_failures_total = Counter(
    "quay_org_mirror_sync_failures_total",
    "Total number of org mirror synchronization failures aggregated by namespace",
    labelnames=["namespace", "reason"],
)

org_mirror_last_sync_timestamp = Gauge(
    "quay_org_mirror_last_sync_timestamp",
    "Unix timestamp of the last org mirror synchronization attempt",
    labelnames=["namespace", "repository"],
)

org_mirror_last_discovery_status = Gauge(
    "quay_org_mirror_last_discovery_status",
    "Status of the last org mirror discovery attempt (0=failed, 1=success, 2=in_progress)",
    labelnames=["namespace"],
)

org_mirror_last_discovery_timestamp = Gauge(
    "quay_org_mirror_last_discovery_timestamp",
    "Unix timestamp of the last org mirror discovery attempt",
    labelnames=["namespace"],
)

_HOOKS_INSTALLED = False


def install_hooks():
    """
    Replace org mirror worker entry points with instrumented versions.

    Called from workers/repomirrorworker/repomirrorworker.py at worker startup so
    workers/repomirrorworker/__init__.py remains unchanged.
    """
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    import workers.repomirrorworker as rmw
    from workers.repomirrorworker import org_mirror_instrumentation

    rmw.perform_org_mirror_repo = org_mirror_instrumentation.perform_org_mirror_repo_with_metrics
    rmw.perform_org_mirror_discovery = (
        org_mirror_instrumentation.perform_org_mirror_discovery_with_metrics
    )
    _HOOKS_INSTALLED = True
    logger.debug("Installed org mirror metric instrumentation hooks")
