import base64
import os
import re
import traceback
import fnmatch
import logging.config

import requests

from contextlib import contextmanager
from prometheus_client import Gauge

import features

from app import app
from data import database
from data.encryption import DecryptionFailureException
from data.model.repo_mirror import claim_mirror, release_mirror
from data.model.user import retrieve_robot_token
from data.logs_model import logs_model
from data.registry_model import registry_model
from data.database import RepoMirrorStatus
from data.model.oci.tag import delete_tag, retarget_tag, lookup_alive_tags_shallow
from notifications import spawn_notification
from util.audit import wrap_repository

from workers.repomirrorworker.repo_mirror_model import repo_mirror_model as model
from workers.repomirrorworker.skopeo_calls import get_all_tags, RepoMirrorSkopeoException
from workers.repomirrorworker.rules.definitions import handler_for_mirroring_row


logger = logging.getLogger(__name__)


unmirrored_repositories = Gauge(
    "quay_repository_rows_unmirrored",
    "number of repositories in the database that have not yet been mirrored",
)


class PreemptedException(Exception):
    """
    Exception raised if another worker analyzed the image before this worker was able to do so.
    """


def process_mirrors(skopeo, token=None):
    """
    Performs mirroring of repositories whose last sync time is greater than sync interval.

    If a token is provided, scanning will begin where the token indicates it previously completed.
    """
    if not features.REPO_MIRROR:
        logger.debug("Repository mirror disabled; skipping RepoMirrorWorker process_mirrors")
        return None

    iterator, next_token = model.repositories_to_mirror(start_token=token)
    if iterator is None:
        logger.debug("Found no additional repositories to mirror")
        return next_token

    verbose_logs = os.getenv("DEBUGLOG", "false").lower() == "true"

    with database.UseThenDisconnect(app.config):
        for mirror, abt, num_remaining in iterator:
            try:
                _perform_mirror(skopeo, mirror, verbose_logs=verbose_logs)
            except PreemptedException:
                logger.info(
                    "Another repository mirror worker pre-empted us for repository: %s", mirror.id
                )
                abt.set()
            except Exception as e:
                logger.exception("Repository Mirror service unavailable")
                return None

            unmirrored_repositories.set(num_remaining)

    return next_token


class RunStatus(object):
    def __init__(self):
        self.success = False


@contextmanager
def _run_and_catch(mirror):
    """ Context manager which yields a RunStatus object and executes whatever code
        occurs underneath the context. If the code raises an exception of any kind,
        the mirroring operation is marked as failed.
    """
    status = RunStatus()

    try:
        yield status
        status.success = True
    except RepoMirrorSkopeoException as rmse:
        release_mirror(mirror, RepoMirrorStatus.FAIL)
        _emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "end",
            "%s: %s" % (_description(mirror), str(rmse)),
            stdout=rmse.stdout,
            stderr=rmse.stderr,
        )
    except Exception as e:
        if os.getenv("RAISE_MIRROR_EXCEPTIONS") == "true":
            raise

        release_mirror(mirror, RepoMirrorStatus.FAIL)
        _emit_log(
            mirror,
            "repo_mirror_sync_failed",
            "end",
            "%s: INTERNAL ERROR" % _description(mirror),
            stdout="Not applicable",
            stderr=traceback.format_exc(e),
        )


def _decrypt_credentials(mirror):
    """ Runs decryption of the mirroring credentials and returns them, if any. If none,
        returns (None, None). Raises an exception if decryption failed.
    """
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
    except DecryptionFailureException:
        logger.exception(
            "Failed to decrypt username or password for mirroring %s", mirror.repository
        )
        raise

    return username, password


def _perform_mirror(skopeo, mirror, verbose_logs=False):
    """
    Run mirror on all matching tags of remote repository.
    """
    mirror = claim_mirror(mirror)
    if mirror == None:
        raise PreemptedException

    # Emit that we've started the mirroring operation.
    _emit_log(
        mirror, "repo_mirror_sync_started", "start", _description(mirror),
    )

    # Validate credentials, if any.
    with _run_and_catch(mirror) as run_status:
        username, password = _decrypt_credentials(mirror)

    if not run_status.success:
        return RepoMirrorStatus.FAIL

    # Fetch the tags to mirror.
    with _run_and_catch(mirror) as run_status:
        tags = _tags_to_mirror(skopeo, mirror, verbose_logs=verbose_logs)

    if not run_status.success:
        return RepoMirrorStatus.FAIL

    # Delete any obsolete tags.
    with _run_and_catch(mirror) as run_status:
        _delete_obsolete_tags(mirror, tags)

    if not run_status.success:
        return RepoMirrorStatus.FAIL

    # Synchronize any new or updated tags.
    with _run_and_catch(mirror) as run_status:
        if not _synchronize_tags(
            mirror, skopeo, tags, username, password, verbose_logs=verbose_logs
        ):
            release_mirror(mirror, RepoMirrorStatus.FAIL)
            return RepoMirrorStatus.FAIL

    if not run_status.success:
        return RepoMirrorStatus.FAIL

    # Done!
    _emit_log(
        mirror, "repo_mirror_sync_success", "end", _description(mirror), tags=", ".join(tags),
    )
    release_mirror(mirror, RepoMirrorStatus.SUCCESS)

    return RepoMirrorStatus.SUCCESS


def _description(mirror):
    """ Returns a human-readable description of the mirroring configuration. """
    handler = handler_for_mirroring_row(mirror.root_rule)
    return "'%s' with rule '%s'" % (
        mirror.external_reference,
        handler.describe(mirror.root_rule.rule_value),
    )


def _synchronize_tags(mirror, skopeo, tags, username, password, verbose_logs=False):
    """ Synchronizes tags as part of the mirroring operation. """
    dest_server = (
        app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
    )

    had_failure = False
    for tag in tags:
        # Re-claim the mirror between each operation, to ensure no other worker
        # preempts use
        mirror = claim_mirror(mirror)
        if mirror is None:
            _emit_log(
                mirror, "repo_mirror_sync_failed", "lost", _description(mirror),
            )
            return False

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
            )

        if result.success:
            _emit_log(
                mirror,
                "repo_mirror_sync_tag_success",
                "finish",
                "Source '%s' successful sync" % src_image,
                tag=tag,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            logger.debug("Source '%s' successful sync." % src_image)
        else:
            had_failure = True
            _emit_log(
                mirror,
                "repo_mirror_sync_tag_failed",
                "finish",
                "Source '%s' failed to sync" % src_image,
                tag=tag,
                stdout=result.stdout,
                stderr=result.stderr,
            )
            logger.warning("Source '%s' failed to sync." % src_image)

    return not had_failure


def _tags_to_mirror(skopeo, mirror, verbose_logs=False):
    """ Returns the list of tags to mirror. """
    # Build a list of expected tags to give to skopeo. Skopeo cannot perform
    # a tags call without at least one valid tag (no idea why), so we loop
    # through the list of rules and find any defined tag names to use as a list.
    # If none are found, `latest` will be provided in the tags call.
    handler = handler_for_mirroring_row(mirror.root_rule)
    expected_tags = list(handler.list_direct_tag_references(mirror.root_rule.rule_value))
    expected_tags = expected_tags or ["latest"]

    all_tags = get_all_tags(skopeo, mirror, expected_tags, verbose_logs=verbose_logs)
    if not all_tags:
        return []

    handler = handler_for_mirroring_row(mirror.root_rule)
    matching_tags = set(
        filter_tags(skopeo, mirror, mirror.root_rule.rule_value, all_tags, verbose_logs)
    )
    matching_tags = list(matching_tags)
    matching_tags.sort()
    return matching_tags


def _rollback(mirror, since_ms):
    """
      :param mirror: Mirror to perform rollback on
      :param start_time: Time mirror was started; all changes after will be undone
      :return:
    """

    repository_ref = registry_model.lookup_repository(
        mirror.repository.namespace_user.username, mirror.repository.name
    )
    tags, has_more = registry_model.list_repository_tag_history(
        repository_ref, 1, 100, since_time_ms=since_ms
    )
    for tag in tags:
        logger.debug("Repo mirroring rollback tag '%s'" % tag)

        # If the tag has an end time, it was either deleted or moved.
        if tag.lifetime_end_ms:
            #  If a future entry exists with a start time equal to the end time for this tag,
            # then the action was a move, rather than a delete and a create.
            newer_tag = list(
                filter(
                    lambda t: tag != t
                    and tag.name == t.name
                    and tag.lifetime_end_ms
                    and t.lifetime_start_ms == tag.lifetime_end_ms,
                    tags,
                )
            )[0]
            if newer_tag:
                logger.debug("Repo mirroring rollback revert tag '%s'" % tag)
                retarget_tag(tag.name, tag.manifest._db_id, is_reversion=True)
            else:
                logger.debug("Repo mirroring recreate tag '%s'" % tag)
                retarget_tag(tag.name, tag.manifest._db_id, is_reversion=True)

        #  If the tag has a start time, it was created.
        elif tag.lifetime_start_ms:
            logger.debug("Repo mirroring rollback delete tag '%s'" % tag)
            delete_tag(mirror.repository, tag.name)


def _delete_obsolete_tags(mirror, tags):
    """ Deletes any tags no longer found in the mirrored repository. """
    existing_tags = lookup_alive_tags_shallow(mirror.repository.id)
    obsolete_tags = list([tag for tag in existing_tags if tag.name not in tags])

    for tag in obsolete_tags:
        delete_tag(mirror.repository, tag.name)

    return obsolete_tags


def _emit_log(mirror, log_kind, verb, message, tag=None, tags=None, stdout=None, stderr=None):
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
