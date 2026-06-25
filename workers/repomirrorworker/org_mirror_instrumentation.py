# -*- coding: utf-8 -*-
"""
Instrumented org mirror worker functions with Prometheus metric updates.

These replace perform_org_mirror_repo and perform_org_mirror_discovery at runtime
via org_mirror_metrics.install_hooks() without modifying __init__.py.
"""

import logging
import os
import time
import traceback

from app import app
from data import database
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
)
from data.encryption import DecryptionFailureException
from data.model.org_mirror import (
    check_org_mirror_repo_sync_status,
    claim_org_mirror_config,
    claim_org_mirror_repo,
    deactivate_excluded_repos,
    matches_repository_filter,
    propagate_status_to_repos,
    release_org_mirror_config,
    release_org_mirror_repo,
    schedule_org_mirror_repos_for_sync,
    sync_discovered_repos,
)
from data.model.user import retrieve_robot_token
from util.orgmirror import get_registry_adapter
from util.repomirror.skopeomirror import SkopeoMirror
from workers.repomirrorworker import (
    PreemptedException,
    RepoMirrorSkopeoException,
    _build_external_reference,
    _emit_org_config_log,
    _ensure_local_repository,
    _get_all_tags_for_org_mirror,
    _truncate,
    emit_org_mirror_log,
)
from workers.repomirrorworker import metrics as mirror_metrics
from workers.repomirrorworker import (
    org_mirror_discovery_duration_seconds,
    org_mirror_discovery_total,
    org_mirror_repo_sync_duration_seconds,
    org_mirror_repo_sync_total,
    org_mirror_repos_created_total,
    org_mirror_repos_discovered,
)
from workers.repomirrorworker.org_mirror_metrics import (
    org_mirror_last_discovery_status,
    org_mirror_last_discovery_timestamp,
    org_mirror_last_sync_status,
    org_mirror_last_sync_timestamp,
    org_mirror_sync_complete,
    org_mirror_sync_failures_total,
    org_mirror_tags_pending,
)

logger = logging.getLogger(__name__)


def _record_repo_sync_failure_metrics(
    namespace: str,
    repository: str,
    failure_reason: str,
    sync_start_time: float,
):
    mirror_metrics.update_sync_failed(
        org_mirror_tags_pending,
        org_mirror_last_sync_status,
        org_mirror_sync_complete,
        org_mirror_last_sync_timestamp,
        org_mirror_sync_failures_total,
        namespace,
        repository,
        failure_reason,
        include_repository_label=False,
    )
    org_mirror_last_sync_timestamp.labels(namespace=namespace, repository=repository).set(
        sync_start_time
    )


def _record_repo_sync_success_metrics(namespace: str, repository: str, sync_start_time: float):
    mirror_metrics.update_sync_finished(
        org_mirror_tags_pending,
        org_mirror_last_sync_status,
        org_mirror_sync_complete,
        org_mirror_last_sync_timestamp,
        org_mirror_sync_failures_total,
        namespace,
        repository,
        success=True,
        include_repository_label=False,
    )
    org_mirror_last_sync_timestamp.labels(namespace=namespace, repository=repository).set(
        sync_start_time
    )


def _record_repo_sync_outcome_metrics(
    namespace: str,
    repository: str,
    overall_status: OrgMirrorRepoStatus,
    failure_reason: str | None,
    sync_start_time: float,
):
    if overall_status == OrgMirrorRepoStatus.SUCCESS:
        _record_repo_sync_success_metrics(namespace, repository, sync_start_time)
        return

    reason = failure_reason or "unknown"
    if overall_status == OrgMirrorRepoStatus.CANCEL:
        reason = "cancelled"
    mirror_metrics.update_sync_finished(
        org_mirror_tags_pending,
        org_mirror_last_sync_status,
        org_mirror_sync_complete,
        org_mirror_last_sync_timestamp,
        org_mirror_sync_failures_total,
        namespace,
        repository,
        success=False,
        failure_reason=reason,
        include_repository_label=False,
    )
    org_mirror_last_sync_timestamp.labels(namespace=namespace, repository=repository).set(
        sync_start_time
    )


def perform_org_mirror_discovery_with_metrics(org_mirror_config: OrgMirrorConfig):
    """Instrumented org mirror discovery with config-level Prometheus metrics."""
    discovery_start_time = time.monotonic()
    discovery_start_ts = time.time()
    original_status = org_mirror_config.sync_status

    claimed_config = claim_org_mirror_config(org_mirror_config)
    if not claimed_config:
        raise PreemptedException

    org_name = claimed_config.organization.username
    mirror_metrics.update_discovery_started(
        org_mirror_last_discovery_status,
        org_mirror_last_discovery_timestamp,
        org_name,
        start_time=discovery_start_ts,
    )

    if original_status == OrgMirrorStatus.CANCEL:
        logger.info(
            "Processing cancel for org mirror: %s (config_id=%s)",
            org_name,
            claimed_config.id,
        )
        cancelled_count = propagate_status_to_repos(claimed_config, OrgMirrorRepoStatus.CANCEL)
        logger.info(
            "Cancelled %d repositories for org mirror %s",
            cancelled_count,
            org_name,
        )
        _emit_org_config_log(
            claimed_config,
            "org_mirror_sync_failed",
            "cancelled",
            f"Sync cancelled: {cancelled_count} repos set to cancelled",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.CANCEL)
        org_mirror_discovery_total.labels(status="cancel").inc()
        org_mirror_discovery_duration_seconds.observe(time.monotonic() - discovery_start_time)
        mirror_metrics.update_discovery_finished(
            org_mirror_last_discovery_status,
            org_mirror_last_discovery_timestamp,
            org_name,
            success=False,
            start_time=time.time(),
        )
        return

    logger.info(
        "Starting repository discovery for org mirror: %s (config_id=%s)",
        org_name,
        claimed_config.id,
    )
    _emit_org_config_log(
        claimed_config,
        "org_mirror_sync_started",
        "start",
        f"Starting repository discovery for organization '{org_name}'",
    )

    username = None
    password = None
    try:
        if claimed_config.external_registry_username:
            username = claimed_config.external_registry_username.decrypt()
        if claimed_config.external_registry_password:
            password = claimed_config.external_registry_password.decrypt()
    except DecryptionFailureException as e:
        logger.error(
            "Failed to decrypt credentials for org mirror config %s: %s",
            claimed_config.id,
            e,
        )
        reason = mirror_metrics.map_org_discovery_failure_to_reason(str(e))
        _emit_org_config_log(
            claimed_config,
            "org_mirror_sync_failed",
            "end",
            f"Failed to decrypt source registry credentials: {_truncate(str(e))}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        org_mirror_discovery_total.labels(status="fail").inc()
        org_mirror_discovery_duration_seconds.observe(time.monotonic() - discovery_start_time)
        mirror_metrics.update_discovery_finished(
            org_mirror_last_discovery_status,
            org_mirror_last_discovery_timestamp,
            org_name,
            success=False,
            start_time=time.time(),
        )
        logger.debug("Org mirror discovery failed for %s: %s", org_name, reason)
        return

    try:
        adapter = get_registry_adapter(
            registry_type=claimed_config.external_registry_type,
            url=claimed_config.external_registry_url,
            namespace=claimed_config.external_namespace,
            username=username,
            password=password,
            config=claimed_config.external_registry_config,
            allowed_hosts=app.config.get("SSRF_ALLOWED_HOSTS", []),
        )
    except ValueError as e:
        logger.error(
            "Failed to create registry adapter for org mirror config %s: %s",
            claimed_config.id,
            e,
        )
        _emit_org_config_log(
            claimed_config,
            "org_mirror_sync_failed",
            "end",
            f"Failed to create registry adapter: {_truncate(str(e))}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        org_mirror_discovery_total.labels(status="fail").inc()
        org_mirror_discovery_duration_seconds.observe(time.monotonic() - discovery_start_time)
        mirror_metrics.update_discovery_finished(
            org_mirror_last_discovery_status,
            org_mirror_last_discovery_timestamp,
            org_name,
            success=False,
            start_time=time.time(),
        )
        return

    try:
        all_repos = adapter.list_repositories()
    except Exception as e:
        logger.error(
            "Failed to list repositories from source registry for org mirror config %s: %s",
            claimed_config.id,
            e,
        )
        _emit_org_config_log(
            claimed_config,
            "org_mirror_sync_failed",
            "end",
            f"Failed to fetch repositories from source: {_truncate(str(e))}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        org_mirror_discovery_total.labels(status="fail").inc()
        org_mirror_discovery_duration_seconds.observe(time.monotonic() - discovery_start_time)
        mirror_metrics.update_discovery_finished(
            org_mirror_last_discovery_status,
            org_mirror_last_discovery_timestamp,
            org_name,
            success=False,
            start_time=time.time(),
        )
        return

    filters = claimed_config.repository_filters
    if filters:
        filtered_repos = [r for r in all_repos if matches_repository_filter(r, filters)]
        logger.info(
            "Filtered %d repositories to %d for org mirror config %s",
            len(all_repos),
            len(filtered_repos),
            claimed_config.id,
        )
    else:
        filtered_repos = all_repos

    total_count, newly_created = sync_discovered_repos(claimed_config, filtered_repos)

    deactivated_count = 0
    if all_repos:
        deactivated_count = deactivate_excluded_repos(
            claimed_config, filtered_repos, source_repo_names=all_repos
        )
    if deactivated_count > 0:
        logger.info(
            "Deactivated %d repositories for org mirror %s (no longer in source or filtered out)",
            deactivated_count,
            org_name,
        )

    logger.info(
        "Discovery complete for org mirror %s: %d repos discovered, %d newly created",
        org_name,
        total_count,
        newly_created,
    )

    if original_status == OrgMirrorStatus.SYNC_NOW:
        propagated_count = propagate_status_to_repos(claimed_config, OrgMirrorRepoStatus.SYNC_NOW)
        logger.info(
            "Propagated SYNC_NOW to %d repositories for org mirror %s",
            propagated_count,
            org_name,
        )
    else:
        scheduled_count = schedule_org_mirror_repos_for_sync(claimed_config)
        logger.info(
            "Scheduled %d repositories for sync for org mirror %s",
            scheduled_count,
            org_name,
        )

    _emit_org_config_log(
        claimed_config,
        "org_mirror_sync_success",
        "end",
        f"Discovery completed: {total_count} repos discovered, {newly_created} new",
    )

    release_org_mirror_config(
        claimed_config,
        OrgMirrorStatus.SUCCESS,
        _repos_discovered=total_count,
        _repos_created=newly_created,
    )

    org_mirror_discovery_total.labels(status="success").inc()
    org_mirror_discovery_duration_seconds.observe(time.monotonic() - discovery_start_time)
    org_mirror_repos_discovered.set(total_count)
    if newly_created > 0:
        org_mirror_repos_created_total.inc(newly_created)
    mirror_metrics.update_discovery_finished(
        org_mirror_last_discovery_status,
        org_mirror_last_discovery_timestamp,
        org_name,
        success=True,
        start_time=time.time(),
    )


def perform_org_mirror_repo_with_metrics(
    skopeo: SkopeoMirror, org_mirror_repo: OrgMirrorRepository
) -> OrgMirrorRepoStatus:
    """Instrumented org mirror repository sync with per-repository Prometheus metrics."""
    verbose_logs = os.getenv("DEBUGLOG", "false").lower() == "true"
    repo_sync_start_time = time.monotonic()
    sync_start_ts = time.time()

    claimed_repo = claim_org_mirror_repo(org_mirror_repo)
    if not claimed_repo:
        raise PreemptedException

    config = claimed_repo.org_mirror_config
    org = config.organization
    namespace = org.username
    repository_name = claimed_repo.repository_name
    external_reference = _build_external_reference(config, repository_name)

    mirror_metrics.update_sync_started(
        org_mirror_tags_pending,
        org_mirror_last_sync_status,
        org_mirror_last_sync_timestamp,
        namespace,
        repository_name,
        tag_count=0,
        start_time=sync_start_ts,
    )

    emit_org_mirror_log(
        config,
        claimed_repo,
        "org_mirror_sync_started",
        "start",
        f"Starting sync for '{external_reference}'",
    )

    local_repo = _ensure_local_repository(config, claimed_repo)
    if not local_repo:
        msg = f"Failed to create local repository for '{claimed_repo.repository_name}'"
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            msg,
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL, status_message=msg)
        _record_repo_sync_failure_metrics(
            namespace, repository_name, "permission_denied", sync_start_ts
        )
        org_mirror_repo_sync_total.labels(status="fail").inc()
        org_mirror_repo_sync_duration_seconds.observe(time.monotonic() - repo_sync_start_time)
        return OrgMirrorRepoStatus.FAIL

    tags = []
    try:
        tags = _get_all_tags_for_org_mirror(skopeo, config, external_reference)
    except RepoMirrorSkopeoException as e:
        msg = f"Failed to list tags for '{external_reference}': {e.message}"
        failure_reason = mirror_metrics.map_failure_to_reason(e.stderr or e.message)
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            msg,
            stdout=e.stdout,
            stderr=e.stderr,
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL, status_message=msg)
        _record_repo_sync_failure_metrics(namespace, repository_name, failure_reason, sync_start_ts)
        org_mirror_repo_sync_total.labels(status="fail").inc()
        org_mirror_repo_sync_duration_seconds.observe(time.monotonic() - repo_sync_start_time)
        return OrgMirrorRepoStatus.FAIL
    except Exception as e:
        msg = f"Internal error listing tags for '{external_reference}'"
        failure_reason = mirror_metrics.map_failure_to_reason(str(e))
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            msg,
            stderr=traceback.format_exc(),
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL, status_message=msg)
        _record_repo_sync_failure_metrics(namespace, repository_name, failure_reason, sync_start_ts)
        org_mirror_repo_sync_total.labels(status="fail").inc()
        org_mirror_repo_sync_duration_seconds.observe(time.monotonic() - repo_sync_start_time)
        return OrgMirrorRepoStatus.FAIL

    if not tags:
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_success",
            "end",
            f"No tags found for '{external_reference}'",
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.SUCCESS)
        _record_repo_sync_success_metrics(namespace, repository_name, sync_start_ts)
        org_mirror_repo_sync_total.labels(status="success").inc()
        org_mirror_repo_sync_duration_seconds.observe(time.monotonic() - repo_sync_start_time)
        return OrgMirrorRepoStatus.SUCCESS

    overall_status = OrgMirrorRepoStatus.SUCCESS
    failed_tags = []
    tag_errors = {}
    status_message = None
    released = False
    failure_reason = None

    try:
        try:
            username = (
                config.external_registry_username.decrypt()
                if config.external_registry_username
                else None
            )
            password = (
                config.external_registry_password.decrypt()
                if config.external_registry_password
                else None
            )
        except DecryptionFailureException:
            logger.exception(
                "Failed to decrypt credentials for org mirror %s/%s",
                org.username,
                claimed_repo.repository_name,
            )
            overall_status = OrgMirrorRepoStatus.FAIL
            status_message = "Failed to decrypt credentials"
            failure_reason = "config_error"
            release_org_mirror_repo(claimed_repo, overall_status, status_message=status_message)
            released = True
            return OrgMirrorRepoStatus.FAIL

        dest_server = (
            app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
        )
        skopeo_timeout = config.skopeo_timeout

        mirror_metrics.update_sync_started(
            org_mirror_tags_pending,
            org_mirror_last_sync_status,
            org_mirror_last_sync_timestamp,
            namespace,
            repository_name,
            tag_count=len(tags),
            start_time=sync_start_ts,
        )

        for tag_index, tag in enumerate(tags):
            src_image = f"docker://{external_reference}:{tag}"
            dest_image = (
                f"docker://{dest_server}/{org.username}/{claimed_repo.repository_name}:{tag}"
            )

            with database.CloseForLongOperation(app.config):
                result = skopeo.copy(
                    src_image,
                    dest_image,
                    timeout=skopeo_timeout,
                    src_tls_verify=config.external_registry_config.get("verify_tls", True),
                    dest_tls_verify=app.config.get("REPO_MIRROR_TLS_VERIFY", True),
                    src_username=username,
                    src_password=password,
                    dest_username=config.internal_robot.username,
                    dest_password=retrieve_robot_token(config.internal_robot),
                    proxy=config.external_registry_config.get("proxy", {}),
                    verbose_logs=verbose_logs,
                    unsigned_images=config.external_registry_config.get("unsigned_images", False),
                )

            remaining_tags = len(tags) - (tag_index + 1)
            mirror_metrics.update_sync_tag_processed(
                org_mirror_tags_pending,
                namespace,
                repository_name,
                remaining_tags,
            )

            if check_org_mirror_repo_sync_status(claimed_repo) == OrgMirrorRepoStatus.CANCEL:
                logger.info(
                    "Org mirror sync cancelled on repo %s/%s.",
                    org.username,
                    claimed_repo.repository_name,
                )
                overall_status = OrgMirrorRepoStatus.CANCEL
                break

            if not result.success:
                overall_status = OrgMirrorRepoStatus.FAIL
                failed_tags.append(tag)
                tag_errors[tag] = result.stderr or ""
                if failure_reason is None:
                    failure_reason = mirror_metrics.map_failure_to_reason(
                        result.stderr or result.stdout or "unknown"
                    )
                logger.info("Org mirror: Source '%s' failed to sync.", src_image)
            else:
                logger.info("Org mirror: Source '%s' successful sync.", src_image)

        if overall_status == OrgMirrorRepoStatus.FAIL:
            combined_stderr = "; ".join(f"[{t}]: {err}" for t, err in tag_errors.items() if err)
            if len(combined_stderr) > 4096:
                combined_stderr = combined_stderr[:4093] + "..."
            status_message = f"Sync failed: {len(failed_tags)}/{len(tags)} tags failed"
            emit_org_mirror_log(
                config,
                claimed_repo,
                "org_mirror_sync_failed",
                "end",
                f"Sync failed for '{external_reference}': "
                f"{len(failed_tags)}/{len(tags)} tags failed",
                tags=", ".join(failed_tags),
                stderr=combined_stderr,
            )
        elif overall_status == OrgMirrorRepoStatus.CANCEL:
            emit_org_mirror_log(
                config,
                claimed_repo,
                "org_mirror_sync_cancelled",
                "end",
                f"Sync cancelled for '{external_reference}'",
            )
        else:
            emit_org_mirror_log(
                config,
                claimed_repo,
                "org_mirror_sync_success",
                "end",
                f"Successfully synced '{external_reference}': {len(tags)} tags",
                tags=", ".join(tags),
            )

        release_org_mirror_repo(claimed_repo, overall_status, status_message=status_message)
        released = True

    except Exception as e:
        logger.exception(
            "Unexpected error during tag sync for org mirror %s/%s",
            org.username,
            claimed_repo.repository_name,
        )
        overall_status = OrgMirrorRepoStatus.FAIL
        status_message = "Unexpected error during sync"
        failure_reason = mirror_metrics.map_failure_to_reason(str(e))
        if not released:
            release_org_mirror_repo(
                claimed_repo,
                overall_status,
                status_message=status_message,
            )
            released = True
    finally:
        if not released:
            release_org_mirror_repo(
                claimed_repo,
                OrgMirrorRepoStatus.FAIL,
                status_message=f"Unexpected error during sync of '{external_reference}'",
            )
            overall_status = OrgMirrorRepoStatus.FAIL
            failure_reason = failure_reason or "unknown"

        _record_repo_sync_outcome_metrics(
            namespace,
            repository_name,
            overall_status,
            failure_reason,
            sync_start_ts,
        )

        status_label = overall_status.name.lower()
        org_mirror_repo_sync_total.labels(status=status_label).inc()
        org_mirror_repo_sync_duration_seconds.observe(time.monotonic() - repo_sync_start_time)

    return overall_status
