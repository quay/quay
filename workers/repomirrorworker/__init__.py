import fnmatch
import logging
import logging.config
import os
import re
import time
import traceback
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

import features
from app import app
from data import database
from data.database import RepoMirrorConfig, RepoMirrorStatus
from data.encryption import DecryptionFailureException
from data.logs_model import logs_model
from data.model.oci.tag import delete_tag, lookup_alive_tags_shallow, retarget_tag
from data.model.repo_mirror import (
    change_retries_remaining,
    change_sync_status,
    check_repo_mirror_sync_status,
    claim_mirror,
    release_mirror,
)
from data.model.user import retrieve_robot_token
from data.registry_model import registry_model
from notifications import spawn_notification
from util.audit import wrap_repository
from util.repomirror.skopeomirror import SkopeoMirror, SkopeoResults
from workers.repomirrorworker.repo_mirror_model import repo_mirror_model as model

logger = logging.getLogger(__name__)


unmirrored_repositories = Gauge(
    "quay_repository_rows_unmirrored",
    "number of repositories in the database that have not yet been mirrored",
)

# Repository mirroring metrics
repo_mirror_tags_pending = Gauge(
    "quay_repository_mirror_tags_pending",
    "Total number of tags pending synchronization for each mirrored repository",
    labelnames=["namespace", "repository"],
)

repo_mirror_last_sync_status = Gauge(
    "quay_repository_mirror_last_sync_status",
    "Status of the last synchronization attempt (0=failed, 1=success, 2=in_progress)",
    labelnames=["namespace", "repository", "last_error_reason"],
)

repo_mirror_sync_complete = Gauge(
    "quay_repository_mirror_sync_complete",
    "Indicates if all tags have been successfully synchronized (0=incomplete, 1=complete)",
    labelnames=["namespace", "repository"],
)

repo_mirror_sync_failures_total = Counter(
    "quay_repository_mirror_sync_failures_total",
    "Total number of synchronization failures per repository",
    labelnames=["namespace", "repository", "reason"],
)

# Additional supporting metrics
repo_mirror_workers_active = Gauge(
    "quay_repository_mirror_workers_active",
    "Number of currently active mirror workers",
)

repo_mirror_last_sync_timestamp = Gauge(
    "quay_repository_mirror_last_sync_timestamp",
    "Unix timestamp of the last synchronization attempt",
    labelnames=["namespace", "repository"],
)

repo_mirror_sync_duration_seconds = Histogram(
    "quay_repository_mirror_sync_duration_seconds",
    "Duration of the last synchronization operation",
    labelnames=["namespace", "repository"],
    buckets=(30, 60, 120, 300, 600, 1200, 1800, 3600, 7200, float("inf")),
)

# Used only for testing - should not be set in production
TAG_ROLLBACK_PAGE_SIZE = app.config.get("REPO_MIRROR_TAG_ROLLBACK_PAGE_SIZE", 100)


def _map_failure_to_reason(error_message):
    """
    Map error messages to standardized failure reasons for metrics.
    This helps categorize failures for better alerting and troubleshooting.
    """
    error_lower = str(error_message).lower()
    
    if "auth" in error_lower or "unauthorized" in error_lower or "forbidden" in error_lower:
        return "auth_failed"
    elif "timeout" in error_lower or "timed out" in error_lower:
        return "network_timeout"
    elif "connection" in error_lower or "network" in error_lower:
        return "connection_error"
    elif "not found" in error_lower or "404" in error_lower:
        return "not_found"
    elif "tls" in error_lower or "certificate" in error_lower or "ssl" in error_lower:
        return "tls_error"
    elif "decrypt" in error_lower:
        return "decryption_failed"
    else:
        return "unknown_error"


class PreemptedException(Exception):
    """
    Exception raised if another worker analyzed the image before this worker was able to do so.
    """


class RepoMirrorSkopeoException(Exception):
    """
    Exception from skopeo.
    """

    def __init__(self, message, stdout, stderr):
        self.message = message
        self.stdout = stdout
        self.stderr = stderr


def process_mirrors(skopeo, token=None):
    """
    Performs mirroring of repositories whose last sync time is greater than sync interval.

    If a token is provided, scanning will begin where the token indicates it previously completed.
    """

    if not features.REPO_MIRROR:
        logger.debug("Repository mirror disabled; skipping RepoMirrorWorker process_mirrors")
        return None

    iterator, next_token = model.repositories_to_mirror(start_token=token)
    if not iterator:
        logger.debug("Found no additional repositories to mirror")
        return next_token

    with database.UseThenDisconnect(app.config):
        for mirror, abt, num_remaining in iterator:
            try:
                perform_mirror(skopeo, mirror)
            except PreemptedException:
                logger.info(
                    "Another repository mirror worker pre-empted us for repository: %s", mirror.id
                )
                abt.set()
            except Exception as e:  # TODO: define exceptions
                logger.exception("Repository Mirror service unavailable: %s" % e)
                return None

            unmirrored_repositories.set(num_remaining)

    return next_token


def perform_mirror(skopeo: SkopeoMirror, mirror: RepoMirrorConfig):
    """
    Run mirror on all matching tags of remote repository.
    """

    if os.getenv("DEBUGLOG", "false").lower() == "true":
        verbose_logs = True
    else:
        verbose_logs = False

    mirror = claim_mirror(mirror)  # type: ignore
    if not mirror:
        raise PreemptedException

    # Track start time for duration metric
    sync_start_time = time.time()
    namespace = mirror.repository.namespace_user.username
    repository_name = mirror.repository.name
    
    # Set sync status to in_progress (2)
    repo_mirror_last_sync_status.labels(
        namespace=namespace,
        repository=repository_name,
        last_error_reason="",
    ).set(2)
    
    # Update timestamp
    repo_mirror_last_sync_timestamp.labels(
        namespace=namespace,
        repository=repository_name,
    ).set(sync_start_time)

    emit_log(
        mirror,
        "repo_mirror_sync_started",
        "start",
        "'%s' with tag pattern '%s'"
        % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
    )

    # Fetch the tags to mirror, being careful to handle exceptions. The 'Exception' is safety net only, allowing
    # easy communication by user through bug report.
    tags = []
    failure_reason = None
    
    try:
        tags = tags_to_mirror(skopeo, mirror)
    except RepoMirrorSkopeoException as e:
        failure_reason = _map_failure_to_reason(str(e))
        emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "end",
            "'%s' with tag pattern '%s': %s"
            % (mirror.external_reference, ",".join(mirror.root_rule.rule_value), str(e)),
            tags=", ".join(tags),
            stdout=e.stdout,
            stderr=e.stderr,
        )
        # Update metrics for early failure
        _update_mirror_metrics_on_failure(namespace, repository_name, failure_reason, sync_start_time)
        release_mirror(mirror, RepoMirrorStatus.FAIL)
        return
    except Exception as e:
        failure_reason = _map_failure_to_reason(str(e))
        emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "end",
            "'%s' with tag pattern '%s': INTERNAL ERROR"
            % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
            tags=", ".join(tags),
            stdout="Not applicable",
            stderr=traceback.format_exc(),
        )
        # Update metrics for early failure
        _update_mirror_metrics_on_failure(namespace, repository_name, failure_reason, sync_start_time)
        release_mirror(mirror, RepoMirrorStatus.FAIL)
        return
    if tags == []:
        emit_log(
            mirror,
            "repo_mirror_sync_success",
            "end",
            "'%s' with tag pattern '%s'"
            % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
            tags="No tags matched",
        )
        # Set metrics for empty tag list - this is a success
        sync_duration = time.time() - sync_start_time
        repo_mirror_tags_pending.labels(
            namespace=namespace,
            repository=repository_name,
        ).set(0)
        repo_mirror_last_sync_status.labels(
            namespace=namespace,
            repository=repository_name,
            last_error_reason="",
        ).set(1)
        repo_mirror_sync_complete.labels(
            namespace=namespace,
            repository=repository_name,
        ).set(1)
        repo_mirror_sync_duration_seconds.labels(
            namespace=namespace,
            repository=repository_name,
        ).observe(sync_duration)
        release_mirror(mirror, RepoMirrorStatus.SUCCESS)
        return

    # Sync tags
    now_ms = database.get_epoch_timestamp_ms()
    overall_status = RepoMirrorStatus.SUCCESS
    failed_tags = []
    
    # Set initial pending tags metric
    repo_mirror_tags_pending.labels(
        namespace=namespace,
        repository=repository_name,
    ).set(len(tags))
    try:
        try:
            username = (
                mirror.external_registry_username.decrypt()
                if mirror.external_registry_username
                else None
            )
            password = (
                mirror.external_registry_password.decrypt()
                if mirror.external_registry_password
                else None
            )
        except DecryptionFailureException as e:
            logger.exception(
                "Failed to decrypt username or password for mirroring %s", mirror.repository
            )
            failure_reason = _map_failure_to_reason(str(e))
            _update_mirror_metrics_on_failure(namespace, repository_name, failure_reason, sync_start_time)
            raise

        dest_server = (
            app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
        )

        skopeo_timeout = mirror.skopeo_timeout

        for tag_index, tag in enumerate(tags):
            src_image = "docker://%s:%s" % (mirror.external_reference, tag)
            dest_image = "docker://%s/%s/%s:%s" % (
                dest_server,
                mirror.repository.namespace_user.username,
                mirror.repository.name,
                tag,
            )
            with database.CloseForLongOperation(app.config):
                result = skopeo.copy(
                    src_image,
                    dest_image,
                    timeout=skopeo_timeout,
                    src_tls_verify=mirror.external_registry_config.get("verify_tls", True),
                    dest_tls_verify=app.config.get(
                        "REPO_MIRROR_TLS_VERIFY", True
                    ),  # TODO: is this a config choice or something else?
                    src_username=username,
                    src_password=password,
                    dest_username=mirror.internal_robot.username,
                    dest_password=retrieve_robot_token(mirror.internal_robot),
                    proxy=mirror.external_registry_config.get("proxy", {}),
                    verbose_logs=verbose_logs,
                    unsigned_images=mirror.external_registry_config.get("unsigned_images", False),
                )

            # Update pending tags metric after processing each tag
            remaining_tags = len(tags) - (tag_index + 1)
            repo_mirror_tags_pending.labels(
                namespace=namespace,
                repository=repository_name,
            ).set(remaining_tags)

            if check_repo_mirror_sync_status(mirror) == RepoMirrorStatus.CANCEL:
                logger.info(
                    "Sync cancelled on repo %s/%s.",
                    mirror.repository.namespace_user.username,
                    mirror.repository.name,
                )
                overall_status = RepoMirrorStatus.CANCEL
                break

            if not result.success:
                overall_status = RepoMirrorStatus.FAIL
                failed_tags.append(tag)
                # Track the first failure reason for metrics
                if failure_reason is None:
                    failure_reason = _map_failure_to_reason(result.stderr or result.stdout or "unknown")
                emit_log(
                    mirror,
                    "repo_mirror_sync_tag_failed",
                    "finish",
                    "Source '%s' failed to sync" % src_image,
                    tag=tag,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                logger.info("Source '%s' failed to sync." % src_image)
            else:
                emit_log(
                    mirror,
                    "repo_mirror_sync_tag_success",
                    "finish",
                    "Source '%s' successful sync" % src_image,
                    tag=tag,
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
                logger.info("Source '%s' successful sync." % src_image)

        delete_obsolete_tags(mirror, tags)

    except PreemptedException as e:
        overall_status = RepoMirrorStatus.FAIL
        failure_reason = "preempted"
        emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "lost",
            "'%s' job lost" % (mirror.external_reference),
            tags="",
            stdout="Not applicable",
            stderr="Not applicable",
        )
        release_mirror(mirror, overall_status)
        return

    except Exception as e:
        overall_status = RepoMirrorStatus.FAIL
        if failure_reason is None:
            failure_reason = _map_failure_to_reason(str(e))
        emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "end",
            "'%s' with tag pattern '%s': INTERNAL ERROR"
            % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
            tags=", ".join(tags),
            stdout="Not applicable",
            stderr=traceback.format_exc(),
        )
        release_mirror(mirror, overall_status)
        return
    finally:
        sync_duration = time.time() - sync_start_time
        
        if overall_status == RepoMirrorStatus.FAIL:
            log_tags = []
            log_message = "'%s' with tag pattern '%s'"

            # Handle the case where not all tags were synced and state will not be rolled back
            if (
                len(failed_tags) != len(tags)
                and len(failed_tags) > 0
                and not app.config.get("REPO_MIRROR_ROLLBACK", False)
            ):
                log_message = "'%s' with tag pattern '%s': PARTIAL SYNC"
                for tag in tags:
                    if tag in failed_tags:
                        tag = tag + "(FAILED)"
                    log_tags.append(tag)

            emit_log(
                mirror,
                "repo_mirror_sync_failed",
                "lost",
                log_message % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
                tags=", ".join(log_tags),
                stdout="Not applicable",
                stderr="Not applicable",
            )

            # Rollback the state of repo if feature is enabled,
            # otherwise only rollback those that failed
            if app.config.get("REPO_MIRROR_ROLLBACK", False):
                rollback(mirror, now_ms)
            else:
                rollback(mirror, now_ms, failed_tags)
        if overall_status == RepoMirrorStatus.CANCEL:
            log_message = "'%s' with tag pattern '%s'"
            emit_log(
                mirror,
                "repo_mirror_sync_failed",
                "Cancelled",
                log_message % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
                stdout="Not applicable",
                stderr="Not applicable",
            )
        else:
            emit_log(
                mirror,
                "repo_mirror_sync_success",
                "end",
                "'%s' with tag pattern '%s'"
                % (mirror.external_reference, ",".join(mirror.root_rule.rule_value)),
                tags=", ".join(tags),
            )
        
        # Update mirroring metrics
        # Set complete sync metric (1 if all tags synced successfully, 0 otherwise)
        is_complete = 1 if (overall_status == RepoMirrorStatus.SUCCESS and len(failed_tags) == 0) else 0
        repo_mirror_sync_complete.labels(
            namespace=namespace,
            repository=repository_name,
        ).set(is_complete)
        
        # Set last sync status metric based on final status
        if overall_status == RepoMirrorStatus.SUCCESS:
            status_value = 1
            error_reason = ""
        elif overall_status == RepoMirrorStatus.SYNCING:
            status_value = 2
            error_reason = ""
        else:  # FAIL or CANCEL
            status_value = 0
            error_reason = failure_reason or "unknown_error"
        
        repo_mirror_last_sync_status.labels(
            namespace=namespace,
            repository=repository_name,
            last_error_reason=error_reason,
        ).set(status_value)
        
        # Record sync duration
        repo_mirror_sync_duration_seconds.labels(
            namespace=namespace,
            repository=repository_name,
        ).observe(sync_duration)
        
        # Increment failure counter on failures with reason
        if overall_status == RepoMirrorStatus.FAIL:
            repo_mirror_sync_failures_total.labels(
                namespace=namespace,
                repository=repository_name,
                reason=failure_reason or "unknown_error",
            ).inc()
        
        release_mirror(mirror, overall_status)

    return overall_status


def tags_to_mirror(skopeo: SkopeoMirror, mirror: RepoMirrorConfig) -> list[str]:
    all_tags = get_all_tags(skopeo, mirror)
    if all_tags == []:
        return []

    matching_tags: list[str] = []
    for pattern in mirror.root_rule.rule_value:
        matching_tags = matching_tags + [tag for tag in all_tags if fnmatch.fnmatch(tag, pattern)]
    matching_tags = list(set(matching_tags))
    matching_tags.sort()
    return matching_tags


def get_all_tags(skopeo: SkopeoMirror, mirror: RepoMirrorConfig) -> list[str]:
    verbose_logs = os.getenv("DEBUGLOG", "false").lower() == "true"

    username = (
        mirror.external_registry_username.decrypt() if mirror.external_registry_username else None
    )
    password = (
        mirror.external_registry_password.decrypt() if mirror.external_registry_password else None
    )

    skopeo_timeout = mirror.skopeo_timeout

    with database.CloseForLongOperation(app.config):
        result = skopeo.tags(
            "docker://%s" % (mirror.external_reference),
            timeout=skopeo_timeout,
            username=username,
            password=password,
            verbose_logs=verbose_logs,
            verify_tls=mirror.external_registry_config.get("verify_tls", True),
            proxy=mirror.external_registry_config.get("proxy", {}),
        )

    if not result.success:
        raise RepoMirrorSkopeoException(
            "skopeo list-tags failed: %s" % _skopeo_inspect_failure(result),
            result.stdout,
            result.stderr,
        )

    return result.tags


def _skopeo_inspect_failure(result: SkopeoResults) -> str:
    """
    Custom processing of skopeo error messages for user friendly description.

    :param result: SkopeoResults object
    :return: Message to display
    """

    return "See output"


def rollback(
    mirror: RepoMirrorConfig, since_ms: int, tag_names: Optional[list[str]] = None
) -> None:
    """
    :param mirror: Mirror to perform rollback on
    :param start_time: Time mirror was started; all changes after will be undone
    :return:
    """

    repository_ref = registry_model.lookup_repository(
        mirror.repository.namespace_user.username, mirror.repository.name
    )

    tags = []
    index = 1
    has_more = True
    while has_more:
        tags_page, has_more = registry_model.list_repository_tag_history(
            repository_ref, index, TAG_ROLLBACK_PAGE_SIZE, since_time_ms=since_ms
        )
        tags.extend(tags_page)
        index = index + 1

    if tag_names is not None:
        tags = [tag for tag in tags if tag.name in tag_names]

    for tag in tags:
        logger.debug("Repo mirroring rollback tag '%s'" % tag)

        # If the tag has an end time, it was either deleted or moved.
        if tag.lifetime_end_ms:
            #  If a future entry exists with a start time equal to the end time for this tag,
            # then the action was a move, rather than a delete and a create.
            tag_list = list(
                filter(
                    lambda t: tag != t
                    and tag.name == t.name
                    and tag.lifetime_end_ms
                    and t.lifetime_start_ms == tag.lifetime_end_ms,
                    tags,
                )
            )
            if len(tag_list) > 0:
                logger.debug("Repo mirroring rollback revert tag '%s'" % tag)
                retarget_tag(tag.name, tag.manifest._db_id, is_reversion=True)
            else:
                logger.debug("Repo mirroring recreate tag '%s'" % tag)
                retarget_tag(tag.name, tag.manifest._db_id, is_reversion=True)

        #  If the tag has a start time, it was created.
        elif tag.lifetime_start_ms:
            logger.debug("Repo mirroring rollback delete tag '%s'" % tag)
            delete_tag(mirror.repository, tag.name)


def delete_obsolete_tags(mirror, tags):
    existing_tags, _ = lookup_alive_tags_shallow(mirror.repository.id)
    obsolete_tags = list([tag for tag in existing_tags if tag.name not in tags])

    for tag in obsolete_tags:
        logger.debug("Repo mirroring delete obsolete tag '%s'" % tag.name)
        delete_tag(mirror.repository, tag.name)

    return obsolete_tags


# TODO: better to call 'track_and_log()' https://jira.coreos.com/browse/QUAY-1821
def emit_log(mirror, log_kind, verb, message, tag=None, tags=None, stdout=None, stderr=None):
    logs_model.log_action(
        log_kind,
        namespace_name=mirror.repository.namespace_user.username,
        repository_name=mirror.repository.name,
        metadata={
            "verb": verb,
            "namespace": mirror.repository.namespace_user.username,
            "repo": mirror.repository.name,
            "message": message,
            "tag": tag,
            "tags": tags,
            "stdout": stdout,
            "stderr": stderr,
        },
    )

    if log_kind in (
        "repo_mirror_sync_started",
        "repo_mirror_sync_failed",
        "repo_mirror_sync_success",
    ):
        spawn_notification(wrap_repository(mirror.repository), log_kind, {"message": message})


def _update_mirror_metrics_on_failure(namespace, repository_name, failure_reason, sync_start_time):
    """
    Helper function to update metrics when a mirror sync fails.
    """
    repo_mirror_tags_pending.labels(
        namespace=namespace,
        repository=repository_name,
    ).set(0)
    
    repo_mirror_last_sync_status.labels(
        namespace=namespace,
        repository=repository_name,
        last_error_reason=failure_reason or "unknown_error",
    ).set(0)
    
    repo_mirror_sync_complete.labels(
        namespace=namespace,
        repository=repository_name,
    ).set(0)
    
    repo_mirror_sync_failures_total.labels(
        namespace=namespace,
        repository=repository_name,
        reason=failure_reason or "unknown_error",
    ).inc()
    
    # Record duration if available
    if sync_start_time:
        sync_duration = time.time() - sync_start_time
        repo_mirror_sync_duration_seconds.labels(
            namespace=namespace,
            repository=repository_name,
        ).observe(sync_duration)


def cleanup_mirror_metrics(namespace, repository_name):
    """
    Remove metrics for a repository that is being deleted or disabled.
    This helps prevent stale metrics from accumulating.
    """
    try:
        repo_mirror_tags_pending.remove(namespace, repository_name)
        repo_mirror_sync_complete.remove(namespace, repository_name)
        repo_mirror_last_sync_timestamp.remove(namespace, repository_name)
        
        # Note: Last sync status has an additional 'last_error_reason' label, 
        # so we need to remove all possible combinations
        # Since we can't enumerate all possible error reasons, we'll try common ones
        for error_reason in ["", "auth_failed", "network_timeout", "connection_error", 
                             "not_found", "tls_error", "decryption_failed", "unknown_error", "preempted"]:
            try:
                repo_mirror_last_sync_status.remove(namespace, repository_name, error_reason)
            except (KeyError, ValueError):
                pass
        
        # Note: Counter and Histogram metrics cannot be easily removed in prometheus_client,
        # they will naturally expire when not updated
    except (KeyError, AttributeError):
        # Metrics may not exist or removal not supported
        logger.debug(
            "Could not remove metrics for %s/%s - may not exist",
            namespace,
            repository_name,
        )
