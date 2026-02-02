import fnmatch
import json
import logging
import os
import re
import traceback
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from prometheus_client import Gauge

import features
from app import app
from data import database
from data.database import (
    OrgMirrorConfig,
    OrgMirrorRepository,
    OrgMirrorRepoStatus,
    OrgMirrorStatus,
    RepoMirrorConfig,
    RepoMirrorStatus,
    Repository,
    RepositoryState,
)
from data.encryption import DecryptionFailureException
from data.logs_model import logs_model
from data.model import repository as repository_model
from data.model.oci.tag import delete_tag, lookup_alive_tags_shallow, retarget_tag
from data.model.org_mirror import (
    claim_org_mirror_config,
    claim_org_mirror_repo,
    matches_repository_filter,
    propagate_status_to_repos,
    release_org_mirror_config,
    release_org_mirror_repo,
    schedule_org_mirror_repos_for_sync,
    sync_discovered_repos,
)
from data.model.repo_mirror import (
    check_repo_mirror_sync_status,
    claim_mirror,
    release_mirror,
)
from data.model.user import retrieve_robot_token
from data.registry_model import registry_model
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE
from notifications import spawn_notification
from util.audit import wrap_repository
from util.orgmirror import get_registry_adapter
from util.repomirror.skopeomirror import SkopeoMirror, SkopeoResults
from workers.repomirrorworker.manifest_utils import (
    filter_manifests_by_architecture,
    get_available_architectures,
    get_manifest_media_type,
    is_manifest_list,
)
from workers.repomirrorworker.org_mirror_model import org_mirror_model
from workers.repomirrorworker.repo_mirror_model import repo_mirror_model as model

logger = logging.getLogger(__name__)


unmirrored_repositories = Gauge(
    "quay_repository_rows_unmirrored",
    "number of repositories in the database that have not yet been mirrored",
)

unmirrored_org_repositories = Gauge(
    "quay_org_mirror_repositories_unmirrored",
    "number of org-level mirror repositories in the database that have not yet been mirrored",
)

pending_org_mirror_discovery = Gauge(
    "quay_org_mirror_configs_pending_discovery",
    "number of org-level mirror configs pending repository discovery",
)

# Used only for testing - should not be set in production
TAG_ROLLBACK_PAGE_SIZE = app.config.get("REPO_MIRROR_TAG_ROLLBACK_PAGE_SIZE", 100)


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

    mirror = claim_mirror(mirror)
    if not mirror:
        raise PreemptedException

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
    try:
        tags = tags_to_mirror(skopeo, mirror)
    except RepoMirrorSkopeoException as e:
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
        release_mirror(mirror, RepoMirrorStatus.FAIL)
        return
    except Exception as e:
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
        release_mirror(mirror, RepoMirrorStatus.SUCCESS)
        return

    # Sync tags
    now_ms = database.get_epoch_timestamp_ms()
    overall_status = RepoMirrorStatus.SUCCESS
    failed_tags = []
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
        except DecryptionFailureException:
            logger.exception(
                "Failed to decrypt username or password for mirroring %s", mirror.repository
            )
            raise

        dest_server = (
            app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
        )

        skopeo_timeout = mirror.skopeo_timeout

        # Check for architecture filter
        architecture_filter = mirror.architecture_filter or []
        use_arch_filter = bool(architecture_filter)
        if use_arch_filter:
            logger.info(
                "Architecture filter for %s/%s: %s",
                mirror.repository.namespace_user.username,
                mirror.repository.name,
                architecture_filter,
            )

        for tag in tags:
            src_image = "docker://%s:%s" % (mirror.external_reference, tag)
            dest_image = "docker://%s/%s/%s:%s" % (
                dest_server,
                mirror.repository.namespace_user.username,
                mirror.repository.name,
                tag,
            )

            if use_arch_filter:
                # Use architecture-filtered copy
                result = copy_filtered_architectures(
                    skopeo, mirror, tag, architecture_filter, verbose_logs=verbose_logs
                )
            else:
                # Use existing --all copy
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
                        unsigned_images=mirror.external_registry_config.get(
                            "unsigned_images", False
                        ),
                    )

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


def _get_v2_bearer_token(server, scheme, namespace, repo_name, username, password, verify_tls):
    """
    Get a bearer token for v2 registry authentication.

    Performs the OAuth2 token exchange required by v2 registries.
    """

    # First, make a request to get the WWW-Authenticate challenge
    v2_url = f"{scheme}://{server}/v2/"
    try:
        resp = requests.get(v2_url, verify=verify_tls, timeout=30)
        if resp.status_code == 200:
            # No auth required or already authenticated
            return None

        www_auth = resp.headers.get("WWW-Authenticate", "")
        if not www_auth:
            logger.warning("No WWW-Authenticate header found")
            return None

        # Parse the WWW-Authenticate header
        # Format: Bearer realm="...",service="...",scope="..."
        realm_match = re.search(r'realm="([^"]+)"', www_auth)
        service_match = re.search(r'service="([^"]+)"', www_auth)

        if not realm_match:
            logger.warning("Could not parse realm from WWW-Authenticate: %s", www_auth)
            return None

        realm = realm_match.group(1)
        service = service_match.group(1) if service_match else None
        scope = f"repository:{namespace}/{repo_name}:push,pull"

        # Build token URL using urllib.parse to handle existing query params in realm
        parsed_realm = urlparse(realm)
        existing_params = parse_qs(parsed_realm.query)

        # Add service and scope params (only add service if present)
        new_params = {}
        if service:
            new_params["service"] = service
        new_params["scope"] = scope

        # Merge existing params with new params (new params take precedence)
        for key, value in existing_params.items():
            if key not in new_params:
                new_params[key] = value[0] if len(value) == 1 else value

        # Reconstruct the URL with merged query parameters
        token_url = urlunparse(
            (
                parsed_realm.scheme,
                parsed_realm.netloc,
                parsed_realm.path,
                parsed_realm.params,
                urlencode(new_params),
                parsed_realm.fragment,
            )
        )

        token_resp = requests.get(
            token_url, auth=(username, password), verify=verify_tls, timeout=30
        )
        if token_resp.status_code != 200:
            logger.error(
                "Failed to get bearer token: %s %s", token_resp.status_code, token_resp.text
            )
            return None

        try:
            token_data = token_resp.json()
        except json.JSONDecodeError:
            logger.error("Token endpoint returned non-JSON response: %s", token_resp.text[:200])
            return None

        return token_data.get("token") or token_data.get("access_token")

    except requests.RequestException:
        logger.exception("Error getting bearer token")
        return None


def push_sparse_manifest_list(mirror, tag, manifest_bytes, media_type):
    """
    Push original manifest list bytes directly to preserve digest.

    Returns True on success, False on failure.
    """
    dest_server = (
        app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
    )
    namespace = mirror.repository.namespace_user.username
    repo_name = mirror.repository.name
    scheme = app.config.get("PREFERRED_URL_SCHEME", "https")
    url = f"{scheme}://{dest_server}/v2/{namespace}/{repo_name}/manifests/{tag}"

    robot_username = mirror.internal_robot.username
    robot_token = retrieve_robot_token(mirror.internal_robot)
    dest_tls_verify = app.config.get("REPO_MIRROR_TLS_VERIFY", True)

    try:
        # Get bearer token using v2 OAuth flow
        bearer_token = _get_v2_bearer_token(
            dest_server,
            scheme,
            namespace,
            repo_name,
            robot_username,
            robot_token,
            dest_tls_verify,
        )

        headers = {"Content-Type": media_type or OCI_IMAGE_INDEX_CONTENT_TYPE}
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
            auth = None
        else:
            # Fall back to basic auth if token exchange fails
            auth = (robot_username, robot_token)

        response = requests.put(
            url,
            data=(
                manifest_bytes.encode("utf-8")
                if isinstance(manifest_bytes, str)
                else manifest_bytes
            ),
            headers=headers,
            auth=auth,
            verify=dest_tls_verify,
            timeout=60,
        )
        if response.status_code in (200, 201):
            logger.info("Pushed sparse manifest list for %s/%s:%s", namespace, repo_name, tag)
            return True
        logger.error("Failed to push manifest list: %s %s", response.status_code, response.text)
        return False
    except requests.RequestException as e:
        logger.exception("Request failed pushing manifest list: %s", e)
        return False


def copy_filtered_architectures(skopeo, mirror, tag, architecture_filter, verbose_logs=False):
    """
    Copy only specified architectures from a multi-arch image.

    Returns tuple of (success, stdout, stderr).
    """
    from util.repomirror.skopeomirror import SkopeoResults

    # Get credentials
    username = (
        mirror.external_registry_username.decrypt() if mirror.external_registry_username else None
    )
    password = (
        mirror.external_registry_password.decrypt() if mirror.external_registry_password else None
    )

    dest_server = (
        app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
    )
    src_image_base = f"docker://{mirror.external_reference}"
    src_image_tag = f"{src_image_base}:{tag}"
    dest_image_base = (
        f"docker://{dest_server}/{mirror.repository.namespace_user.username}/"
        f"{mirror.repository.name}"
    )

    proxy = mirror.external_registry_config.get("proxy", {})
    src_tls_verify = mirror.external_registry_config.get("verify_tls", True)
    dest_tls_verify = app.config.get("REPO_MIRROR_TLS_VERIFY", True)
    unsigned_images = mirror.external_registry_config.get("unsigned_images", False)

    # Step 1: Inspect manifest
    with database.CloseForLongOperation(app.config):
        result = skopeo.inspect_raw(
            src_image_tag,
            mirror.skopeo_timeout,
            username=username,
            password=password,
            verify_tls=src_tls_verify,
            proxy=proxy,
            verbose_logs=verbose_logs,
        )

    if not result.success:
        logger.error("Failed to inspect manifest for %s: %s", src_image_tag, result.stderr)
        return SkopeoResults(False, [], result.stdout, result.stderr)

    manifest_bytes = result.stdout

    # Step 2: Check if manifest list
    if not is_manifest_list(manifest_bytes):
        logger.info("Image %s is not a manifest list, using standard copy", src_image_tag)
        with database.CloseForLongOperation(app.config):
            result = skopeo.copy(
                src_image_tag,
                f"{dest_image_base}:{tag}",
                timeout=mirror.skopeo_timeout,
                src_tls_verify=src_tls_verify,
                dest_tls_verify=dest_tls_verify,
                src_username=username,
                src_password=password,
                dest_username=mirror.internal_robot.username,
                dest_password=retrieve_robot_token(mirror.internal_robot),
                proxy=proxy,
                verbose_logs=verbose_logs,
                unsigned_images=unsigned_images,
            )
        return result

    # Step 3: Filter and validate architectures
    available = get_available_architectures(manifest_bytes)
    matching = [a for a in architecture_filter if a in available]
    missing = [a for a in architecture_filter if a not in available]

    if missing:
        logger.warning("Architectures not in source %s: %s", src_image_tag, missing)
    if not matching:
        return SkopeoResults(
            False,
            [],
            "",
            f"No matching architectures. Requested: {architecture_filter}, Available: {available}",
        )

    filtered = filter_manifests_by_architecture(manifest_bytes, matching)
    logger.info("Mirroring %d architectures for %s: %s", len(filtered), src_image_tag, matching)

    # Step 4: Copy each architecture by digest
    all_stdout, all_stderr = [], []
    for entry in filtered:
        digest = entry.get("digest")
        arch = entry.get("platform", {}).get("architecture", "unknown")
        logger.info("Copying architecture %s (%s)", arch, digest)

        with database.CloseForLongOperation(app.config):
            result = skopeo.copy_by_digest(
                f"{src_image_base}@{digest}",
                f"{dest_image_base}@{digest}",
                timeout=mirror.skopeo_timeout,
                src_tls_verify=src_tls_verify,
                dest_tls_verify=dest_tls_verify,
                src_username=username,
                src_password=password,
                dest_username=mirror.internal_robot.username,
                dest_password=retrieve_robot_token(mirror.internal_robot),
                proxy=proxy,
                verbose_logs=verbose_logs,
                unsigned_images=unsigned_images,
            )
        all_stdout.append(f"[{arch}] {result.stdout}")
        all_stderr.append(f"[{arch}] {result.stderr}")
        if not result.success:
            logger.error("Failed to copy arch %s: %s", arch, result.stderr)
            return SkopeoResults(False, [], "\n".join(all_stdout), "\n".join(all_stderr))

    # Step 5: Push original manifest list
    media_type = get_manifest_media_type(manifest_bytes)
    if not push_sparse_manifest_list(mirror, tag, manifest_bytes, media_type):
        return SkopeoResults(
            False, [], "\n".join(all_stdout), "Failed to push sparse manifest list"
        )

    return SkopeoResults(True, [], "\n".join(all_stdout), "\n".join(all_stderr))


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


# ==============================================================================
# Organization-level Mirror Functions
# ==============================================================================


def process_org_mirror_discovery(token=None):
    """
    Performs repository discovery for org-level mirrors whose sync time is due.

    This is Phase 1 of org-level mirroring:
    1. Find eligible OrgMirrorConfig entries
    2. For each config, fetch repository list from source registry
    3. Apply glob filters and populate OrgMirrorRepository table
    4. Schedule discovered repos for sync

    Args:
        token: Optional OrgMirrorConfigToken to resume from previous run

    Returns:
        Next OrgMirrorConfigToken or None if done
    """
    if not features.ORG_MIRROR:
        logger.debug("Organization mirror disabled; skipping process_org_mirror_discovery")
        return None

    iterator, next_token = org_mirror_model.configs_to_discover(start_token=token)
    if not iterator:
        logger.debug("Found no additional organization mirror configs for discovery")
        return next_token

    with database.UseThenDisconnect(app.config):
        for org_mirror_config, abt, num_remaining in iterator:
            try:
                perform_org_mirror_discovery(org_mirror_config)
            except PreemptedException:
                logger.info(
                    "Another worker pre-empted us for org mirror config: %s",
                    org_mirror_config.id,
                )
                abt.set()
            except Exception as e:
                logger.exception("Organization Mirror discovery failed: %s" % e)
                # Continue to next config instead of returning
                continue

            pending_org_mirror_discovery.set(num_remaining)

    return next_token


def perform_org_mirror_discovery(org_mirror_config: OrgMirrorConfig):
    """
    Perform repository discovery for a single org-level mirror config.

    Fetches repository list from source registry, applies filters,
    and populates OrgMirrorRepository table.

    Handles special statuses:
    - CANCEL: Skips discovery, propagates CANCEL to all repos
    - SYNC_NOW: Runs discovery, propagates SYNC_NOW to all repos

    Args:
        org_mirror_config: The OrgMirrorConfig to discover repos for

    Raises:
        PreemptedException: If another worker claimed this config first
    """
    # Remember the original status before claiming (claim changes it to SYNCING)
    original_status = org_mirror_config.sync_status

    # Claim the config for this worker
    claimed_config = claim_org_mirror_config(org_mirror_config)
    if not claimed_config:
        raise PreemptedException

    org_name = claimed_config.organization.username

    # Handle CANCEL: skip discovery, propagate CANCEL to repos
    if original_status == OrgMirrorStatus.CANCEL:
        logger.info(
            "Processing cancel for org mirror: %s (config_id=%s)",
            org_name,
            claimed_config.id,
        )

        # Propagate CANCEL to all repos
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

        # Release with CANCEL status
        release_org_mirror_config(claimed_config, OrgMirrorStatus.CANCEL)
        return

    logger.info(
        "Starting repository discovery for org mirror: %s (config_id=%s)",
        org_name,
        claimed_config.id,
    )

    # Emit log for discovery start
    _emit_org_config_log(
        claimed_config,
        "org_mirror_sync_started",
        "start",
        f"Starting repository discovery for organization '{org_name}'",
    )

    # Get credentials for source registry
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
        _emit_org_config_log(
            claimed_config,
            "org_mirror_sync_failed",
            "end",
            f"Failed to decrypt source registry credentials: {e}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        return

    # Create registry adapter
    try:
        adapter = get_registry_adapter(
            registry_type=claimed_config.external_registry_type,
            url=claimed_config.external_registry_url,
            namespace=claimed_config.external_namespace,
            username=username,
            password=password,
            config=claimed_config.external_registry_config,
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
            f"Failed to create registry adapter: {e}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        return

    # Fetch repositories from source
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
            f"Failed to fetch repositories from source: {e}",
        )
        release_org_mirror_config(claimed_config, OrgMirrorStatus.FAIL)
        return

    # Apply glob filters
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

    # Sync to database
    total_count, newly_created = sync_discovered_repos(claimed_config, filtered_repos)

    logger.info(
        "Discovery complete for org mirror %s: %d repos discovered, %d newly created",
        org_name,
        total_count,
        newly_created,
    )

    # Propagate status to repos based on original config status
    if original_status == OrgMirrorStatus.SYNC_NOW:
        # SYNC_NOW: propagate to all repos for immediate sync
        propagated_count = propagate_status_to_repos(claimed_config, OrgMirrorRepoStatus.SYNC_NOW)
        logger.info(
            "Propagated SYNC_NOW to %d repositories for org mirror %s",
            propagated_count,
            org_name,
        )
    else:
        # Normal scheduled sync: only schedule NEVER_RUN repos
        scheduled_count = schedule_org_mirror_repos_for_sync(claimed_config)
        logger.info(
            "Scheduled %d repositories for sync for org mirror %s",
            scheduled_count,
            org_name,
        )

    # Emit success log
    _emit_org_config_log(
        claimed_config,
        "org_mirror_sync_success",
        "end",
        f"Discovery completed: {total_count} repos discovered, {newly_created} new",
    )

    # Release the config
    release_org_mirror_config(
        claimed_config,
        OrgMirrorStatus.SUCCESS,
        _repos_discovered=total_count,
        _repos_created=newly_created,
    )


def _emit_org_config_log(
    config: OrgMirrorConfig,
    log_kind: str,
    verb: str,
    message: str,
):
    """
    Emit an audit log for an org mirror config operation.

    Args:
        config: The OrgMirrorConfig
        log_kind: The log kind (e.g., 'org_mirror_sync_started')
        verb: The verb for the action
        message: Human-readable message
    """
    org = config.organization
    logs_model.log_action(
        log_kind,
        namespace_name=org.username,
        performer=config.internal_robot,
        ip=None,
        metadata={
            "message": message,
            "org_mirror_config_id": config.id,
            "external_registry_url": config.external_registry_url,
            "external_namespace": config.external_namespace,
        },
    )


def process_org_mirrors(skopeo, token=None):
    """
    Performs mirroring of org-level mirror repositories whose last sync time is greater than
    sync interval.

    If a token is provided, scanning will begin where the token indicates it previously completed.

    Args:
        skopeo: SkopeoMirror instance for image operations
        token: Optional OrgMirrorToken to resume from previous run

    Returns:
        Next OrgMirrorToken or None if done
    """
    if not features.ORG_MIRROR:
        logger.debug("Organization mirror disabled; skipping process_org_mirrors")
        return None

    iterator, next_token = org_mirror_model.repositories_to_mirror(start_token=token)
    if not iterator:
        logger.debug("Found no additional organization mirror repositories to sync")
        return next_token

    with database.UseThenDisconnect(app.config):
        for org_mirror_repo, abt, num_remaining in iterator:
            try:
                perform_org_mirror_repo(skopeo, org_mirror_repo)
            except PreemptedException:
                logger.info(
                    "Another org mirror worker pre-empted us for repository: %s",
                    org_mirror_repo.id,
                )
                abt.set()
            except Exception as e:
                logger.exception("Organization Mirror service unavailable: %s" % e)
                return None

            unmirrored_org_repositories.set(num_remaining)

    return next_token


def perform_org_mirror_repo(skopeo: SkopeoMirror, org_mirror_repo: OrgMirrorRepository):
    """
    Perform mirror sync for a single org-level mirror repository.

    Syncs all tags from the external repository to the internal Quay repository.

    Args:
        skopeo: SkopeoMirror instance for image operations
        org_mirror_repo: The OrgMirrorRepository to sync

    Returns:
        OrgMirrorRepoStatus indicating the result
    """
    verbose_logs = os.getenv("DEBUGLOG", "false").lower() == "true"

    # Claim the repo for this worker
    claimed_repo = claim_org_mirror_repo(org_mirror_repo)
    if not claimed_repo:
        raise PreemptedException

    # Get parent config for credentials and settings
    config = claimed_repo.org_mirror_config
    org = config.organization

    # Build external reference
    external_reference = _build_external_reference(config, claimed_repo.repository_name)

    emit_org_mirror_log(
        config,
        claimed_repo,
        "org_mirror_sync_started",
        "start",
        f"Starting sync for '{external_reference}'",
    )

    # Ensure the local repository exists
    local_repo = _ensure_local_repository(config, claimed_repo)
    if not local_repo:
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            f"Failed to create local repository for '{claimed_repo.repository_name}'",
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL)
        return OrgMirrorRepoStatus.FAIL

    # Fetch all tags from remote
    tags = []
    try:
        tags = _get_all_tags_for_org_mirror(skopeo, config, external_reference)
    except RepoMirrorSkopeoException as e:
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            f"Failed to list tags for '{external_reference}': {e.message}",
            stdout=e.stdout,
            stderr=e.stderr,
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL)
        return OrgMirrorRepoStatus.FAIL
    except Exception:
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            f"Internal error listing tags for '{external_reference}'",
            stderr=traceback.format_exc(),
        )
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL)
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
        return OrgMirrorRepoStatus.SUCCESS

    # Sync each tag
    overall_status = OrgMirrorRepoStatus.SUCCESS
    failed_tags = []

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
        release_org_mirror_repo(claimed_repo, OrgMirrorRepoStatus.FAIL)
        return OrgMirrorRepoStatus.FAIL

    dest_server = (
        app.config.get("REPO_MIRROR_SERVER_HOSTNAME", None) or app.config["SERVER_HOSTNAME"]
    )
    skopeo_timeout = config.skopeo_timeout

    for tag in tags:
        src_image = f"docker://{external_reference}:{tag}"
        dest_image = f"docker://{dest_server}/{org.username}/{claimed_repo.repository_name}:{tag}"

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

        if not result.success:
            overall_status = OrgMirrorRepoStatus.FAIL
            failed_tags.append(tag)
            logger.info("Org mirror: Source '%s' failed to sync.", src_image)
        else:
            logger.info("Org mirror: Source '%s' successful sync.", src_image)

    if overall_status == OrgMirrorRepoStatus.FAIL:
        emit_org_mirror_log(
            config,
            claimed_repo,
            "org_mirror_sync_failed",
            "end",
            f"Sync failed for '{external_reference}': {len(failed_tags)}/{len(tags)} tags failed",
            tags=", ".join(failed_tags),
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

    release_org_mirror_repo(claimed_repo, overall_status)
    return overall_status


def _build_external_reference(config: OrgMirrorConfig, repository_name: str) -> str:
    """
    Build the external registry reference for an org mirror repository.

    Args:
        config: The OrgMirrorConfig containing registry URL and namespace
        repository_name: The repository name

    Returns:
        Full external reference (e.g., "registry.example.com/namespace/repo")
    """
    url = config.external_registry_url.rstrip("/")
    # Remove protocol prefix if present
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]

    return f"{url}/{config.external_namespace}/{repository_name}"


def _ensure_local_repository(
    config: OrgMirrorConfig,
    org_mirror_repo: OrgMirrorRepository,
) -> Optional[Repository]:
    """
    Ensure the local Quay repository exists for the org mirror repo.

    Creates the repository if it doesn't exist, using the visibility from the config.

    Args:
        config: The OrgMirrorConfig
        org_mirror_repo: The OrgMirrorRepository

    Returns:
        The Repository instance or None if creation failed
    """
    org = config.organization
    repo_name = org_mirror_repo.repository_name

    # Check if repo already linked
    if org_mirror_repo.repository:
        return org_mirror_repo.repository

    # Try to find existing repository
    try:
        existing_repo = Repository.get(
            (Repository.namespace_user == org) & (Repository.name == repo_name)
        )
        # Link it to the org mirror repo
        org_mirror_repo.repository = existing_repo
        org_mirror_repo.save()
        return existing_repo
    except Repository.DoesNotExist:
        pass

    # Create new repository
    try:
        visibility_name = config.visibility.name
        new_repo = repository_model.create_repository(
            org.username,
            repo_name,
            config.internal_robot,
            visibility=visibility_name,
            repo_kind="image",
        )
        if new_repo:
            # Set repository state to ORG_MIRROR for org-level mirroring
            repo_db = Repository.get(Repository.id == new_repo.id)
            repo_db.state = RepositoryState.ORG_MIRROR
            repo_db.save()

            # Link to org mirror repo
            org_mirror_repo.repository = repo_db
            org_mirror_repo.save()

            logger.info(
                "Created mirror repository %s/%s for org mirror",
                org.username,
                repo_name,
            )
            return repo_db
    except Exception:
        logger.exception("Failed to create repository %s/%s", org.username, repo_name)

    return None


def _get_all_tags_for_org_mirror(
    skopeo: SkopeoMirror,
    config: OrgMirrorConfig,
    external_reference: str,
) -> list[str]:
    """
    Get all tags from the external registry for an org mirror repository.

    Args:
        skopeo: SkopeoMirror instance
        config: The OrgMirrorConfig containing credentials
        external_reference: The full external reference

    Returns:
        List of tag names

    Raises:
        RepoMirrorSkopeoException: If skopeo fails to list tags
    """
    verbose_logs = os.getenv("DEBUGLOG", "false").lower() == "true"

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
    except DecryptionFailureException as e:
        logger.exception(
            "Failed to decrypt credentials for org mirror when listing tags for %s",
            external_reference,
        )
        raise RepoMirrorSkopeoException(
            f"Failed to decrypt credentials: {e}",
            stdout="",
            stderr=str(e),
        ) from e

    skopeo_timeout = config.skopeo_timeout

    with database.CloseForLongOperation(app.config):
        result = skopeo.tags(
            f"docker://{external_reference}",
            timeout=skopeo_timeout,
            username=username,
            password=password,
            verbose_logs=verbose_logs,
            verify_tls=config.external_registry_config.get("verify_tls", True),
            proxy=config.external_registry_config.get("proxy", {}),
        )

    if not result.success:
        raise RepoMirrorSkopeoException(
            f"skopeo list-tags failed: {_skopeo_inspect_failure(result)}",
            result.stdout,
            result.stderr,
        )

    return result.tags


def emit_org_mirror_log(
    config: OrgMirrorConfig,
    org_mirror_repo: OrgMirrorRepository,
    log_kind: str,
    verb: str,
    message: str,
    tag: Optional[str] = None,
    tags: Optional[str] = None,
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
):
    """
    Emit a log entry for organization-level mirror operations.

    Args:
        config: The OrgMirrorConfig
        org_mirror_repo: The OrgMirrorRepository being processed
        log_kind: The type of log entry
        verb: Action verb (start, end, etc.)
        message: Log message
        tag: Optional single tag
        tags: Optional comma-separated list of tags
        stdout: Optional stdout from skopeo
        stderr: Optional stderr from skopeo
    """
    org = config.organization
    repo_name = org_mirror_repo.repository_name

    logs_model.log_action(
        log_kind,
        namespace_name=org.username,
        repository_name=repo_name,
        metadata={
            "verb": verb,
            "namespace": org.username,
            "repo": repo_name,
            "message": message,
            "tag": tag,
            "tags": tags,
            "stdout": stdout,
            "stderr": stderr,
        },
    )
