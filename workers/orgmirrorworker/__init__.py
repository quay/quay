"""
Organization mirror worker main processing logic.

Handles discovery, repository creation, and sync orchestration for organization-level mirroring.
"""

import logging
import time

from prometheus_client import Counter, Gauge, Histogram

import features
from app import app
from data.database import OrgMirrorStatus, UseThenDisconnect
from data.logs_model import logs_model
from data.model.org_mirror import (
    claim_org_mirror,
    record_discovered_repos,
    release_org_mirror,
)
from data.model.repository import create_repository
from workers.orgmirrorworker.discovery import discover_repositories
from workers.orgmirrorworker.filtering import apply_repo_filters

logger = logging.getLogger(__name__)

# Prometheus metrics

# Gauge metrics (current state)
undiscovered_orgs = Gauge(
    "quay_org_mirror_orgs_pending",
    "Number of organization mirrors pending discovery/sync",
)

discovered_repos_pending = Gauge(
    "quay_org_mirror_repos_pending_creation",
    "Number of discovered repositories pending creation",
)

org_mirrors_syncing = Gauge(
    "quay_org_mirror_syncing",
    "Number of organization mirrors currently syncing",
)

# Counter metrics (cumulative totals)
org_mirror_discovery_total = Counter(
    "quay_org_mirror_discovery_total",
    "Total number of organization mirror discovery attempts",
    ["status"],  # Labels: success, failure
)

org_mirror_sync_total = Counter(
    "quay_org_mirror_sync_total",
    "Total number of organization mirror sync attempts",
    ["status"],  # Labels: success, failure
)

org_mirror_repos_created_total = Counter(
    "quay_org_mirror_repos_created_total",
    "Total number of repositories created by organization mirrors",
)

org_mirror_repos_failed_total = Counter(
    "quay_org_mirror_repos_failed_total",
    "Total number of repository creation failures in organization mirrors",
)

org_mirror_repos_discovered_total = Counter(
    "quay_org_mirror_repos_discovered_total",
    "Total number of repositories discovered by organization mirrors",
)

# Histogram metrics (duration tracking)
org_mirror_discovery_duration_seconds = Histogram(
    "quay_org_mirror_discovery_duration_seconds",
    "Time taken to discover repositories for an organization mirror",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],  # 1s to 10min
)

org_mirror_sync_duration_seconds = Histogram(
    "quay_org_mirror_sync_duration_seconds",
    "Time taken to complete full sync for an organization mirror (discovery + creation)",
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],  # 10s to 1hr
)

org_mirror_repo_creation_duration_seconds = Histogram(
    "quay_org_mirror_repo_creation_duration_seconds",
    "Time taken to create a single repository",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],  # 100ms to 30s
)


class PreemptedException(Exception):
    """
    Raised when another worker pre-empts us by claiming the mirror first.
    """

    pass


class DiscoveryException(Exception):
    """
    Raised when repository discovery fails.
    """

    pass


def process_org_mirrors(model, token=None):
    """
    Process organization mirrors ready for sync.

    Iterates through org mirrors, claims them, performs discovery and creation,
    then releases them. Uses pagination via tokens for resumable processing.

    Args:
        model: OrgMirrorWorkerDataInterface implementation
        token: Optional pagination token to resume from

    Returns:
        Next pagination token or None if no more work
    """
    if not features.ORG_MIRROR:
        logger.debug("Organization mirror disabled")
        return None

    iterator, next_token = model.orgs_to_mirror(start_token=token)
    if not iterator:
        logger.debug("No organization mirrors to process")
        undiscovered_orgs.set(0)
        return next_token

    with UseThenDisconnect(app.config):
        for mirror, abt, num_remaining in iterator:
            try:
                perform_org_mirror(model, mirror)
            except PreemptedException:
                logger.info(
                    "Another worker pre-empted us for org: %s", mirror.organization.username
                )
                abt.set()
            except Exception as e:
                logger.exception("Organization mirror service unavailable: %s" % e)
                return None

            undiscovered_orgs.set(num_remaining)

    return next_token


def perform_org_mirror(model, mirror):
    """
    Perform discovery and repository creation for a single organization mirror.

    Two-phase approach:
    1. Discovery phase: Call registry API to enumerate repositories (stubbed for now)
    2. Creation phase: Create repositories that don't exist

    Args:
        model: OrgMirrorWorkerDataInterface implementation
        mirror: OrgMirrorConfig instance

    Raises:
        PreemptedException: Another worker claimed this mirror
        DiscoveryException: Repository discovery failed
    """
    org_name = mirror.organization.username

    logger.debug("Processing organization mirror for org: %s", org_name)

    # Claim the mirror for processing (optimistic locking)
    claimed = claim_org_mirror(mirror)
    if not claimed:
        raise PreemptedException()

    mirror = claimed
    sync_status = OrgMirrorStatus.FAIL  # Default to failure

    # Track syncing state
    org_mirrors_syncing.inc()

    # Start timing full sync
    sync_start_time = time.time()

    try:
        # Phase 1: Discovery
        logger.info("Starting discovery for org mirror: %s", org_name)

        logs_model.log_action(
            "org_mirror_sync_started",
            namespace_name=org_name,
            metadata={
                "external_reference": mirror.external_reference,
            },
        )

        # Time discovery phase
        discovery_start_time = time.time()

        discovered = discover_repositories(mirror)

        discovery_duration = time.time() - discovery_start_time
        org_mirror_discovery_duration_seconds.observe(discovery_duration)

        if discovered is None:
            logger.error("Discovery failed for org mirror: %s", org_name)
            org_mirror_discovery_total.labels(status="failure").inc()
            raise DiscoveryException("Discovery returned None")
        else:
            org_mirror_discovery_total.labels(status="success").inc()

        logger.info("Discovered %d repositories for org: %s", len(discovered), org_name)

        # Apply repository filtering
        if discovered:
            repo_names = [repo["name"] for repo in discovered]
            filtered_names = apply_repo_filters(repo_names, mirror.root_rule)

            # Convert to set for efficient lookup
            filtered_names_set = set(filtered_names)

            # Reconstruct discovered list with only filtered repos
            filtered_discovered = [
                repo for repo in discovered if repo["name"] in filtered_names_set
            ]

            logger.info(
                "Filtered %d repositories to %d for org: %s",
                len(discovered),
                len(filtered_discovered),
                org_name,
            )

            discovered = filtered_discovered

        # Record discovered repositories
        if discovered:
            new_count = record_discovered_repos(mirror, discovered)
            org_mirror_repos_discovered_total.inc(len(discovered))
            logger.info("Recorded %d new repositories for org: %s", new_count, org_name)

            logs_model.log_action(
                "org_mirror_repo_discovered",
                namespace_name=org_name,
                metadata={
                    "repos_discovered": len(discovered),
                    "repos_new": new_count,
                },
            )

        # Phase 2: Repository Creation
        repos_created, repos_skipped, repos_failed = create_repositories(model, mirror)

        # Update creation metrics
        org_mirror_repos_created_total.inc(repos_created)
        org_mirror_repos_failed_total.inc(repos_failed)

        logger.info(
            "Repository creation complete for org %s: created=%d, skipped=%d, failed=%d",
            org_name,
            repos_created,
            repos_skipped,
            repos_failed,
        )

        # Update metrics
        repos_pending = model.repos_to_create(mirror)
        discovered_repos_pending.set(len(repos_pending))

        # Determine overall sync status
        if repos_failed > 0 and repos_created == 0:
            # All creations failed
            sync_status = OrgMirrorStatus.FAIL
            org_mirror_sync_total.labels(status="failure").inc()
            logs_model.log_action(
                "org_mirror_sync_failed",
                namespace_name=org_name,
                metadata={
                    "repos_failed": repos_failed,
                },
            )
        else:
            # At least some succeeded (or nothing to create)
            sync_status = OrgMirrorStatus.SUCCESS
            org_mirror_sync_total.labels(status="success").inc()
            logs_model.log_action(
                "org_mirror_sync_success",
                namespace_name=org_name,
                metadata={
                    "repos_created": repos_created,
                    "repos_skipped": repos_skipped,
                    "repos_failed": repos_failed,
                },
            )

    except DiscoveryException as e:
        logger.error("Discovery failed for org %s: %s", org_name, str(e))
        sync_status = OrgMirrorStatus.FAIL
        org_mirror_sync_total.labels(status="failure").inc()

        logs_model.log_action(
            "org_mirror_sync_failed",
            namespace_name=org_name,
            metadata={
                "error": str(e),
            },
        )

    except Exception as e:
        logger.exception("Unexpected error during org mirror for %s: %s", org_name, str(e))
        sync_status = OrgMirrorStatus.FAIL
        org_mirror_sync_total.labels(status="failure").inc()

        logs_model.log_action(
            "org_mirror_sync_failed",
            namespace_name=org_name,
            metadata={
                "error": str(e),
            },
        )

    finally:
        # Track sync duration
        sync_duration = time.time() - sync_start_time
        org_mirror_sync_duration_seconds.observe(sync_duration)

        # Decrement syncing counter
        org_mirrors_syncing.dec()

        # Always release the mirror
        released = release_org_mirror(mirror, sync_status)
        if not released:
            logger.warning(
                "Failed to release org mirror for %s (may have been modified by another worker)",
                org_name,
            )


def create_repositories(model, mirror):
    """
    Create repositories that have been discovered but not yet created.

    Handles partial failures gracefully - continues creating repositories even if some fail.

    Args:
        model: OrgMirrorWorkerDataInterface implementation
        mirror: OrgMirrorConfig instance

    Returns:
        Tuple of (created_count, skipped_count, failed_count)
    """
    from data.model.org_mirror import (
        mark_repo_created,
        mark_repo_failed,
        mark_repo_skipped,
    )
    from data.model.repository import get_repository

    org_name = mirror.organization.username
    repos_to_create_list = model.repos_to_create(mirror)

    if not repos_to_create_list:
        logger.debug("No repositories to create for org: %s", org_name)
        return 0, 0, 0

    logger.info("Creating %d repositories for org: %s", len(repos_to_create_list), org_name)

    created_count = 0
    skipped_count = 0
    failed_count = 0

    for org_mirror_repo in repos_to_create_list:
        repo_name = org_mirror_repo.repository_name

        # Time individual repository creation
        repo_start_time = time.time()

        try:
            # Check if repository already exists (double-check)
            existing_repo = get_repository(org_name, repo_name)

            if existing_repo:
                logger.info("Repository %s/%s already exists, skipping", org_name, repo_name)
                mark_repo_skipped(org_mirror_repo, "Repository already exists")
                skipped_count += 1
                continue

            # Create the repository
            logger.debug("Creating repository: %s/%s", org_name, repo_name)

            new_repo = create_repository(
                org_name, repo_name, mirror.internal_robot, description="Created by org mirror"
            )

            # Mark as created
            mark_repo_created(org_mirror_repo, new_repo)

            # Track successful creation duration
            repo_duration = time.time() - repo_start_time
            org_mirror_repo_creation_duration_seconds.observe(repo_duration)

            created_count += 1

            logger.info("Successfully created repository: %s/%s", org_name, repo_name)

            logs_model.log_action(
                "org_mirror_repo_created",
                namespace_name=org_name,
                repository_name=repo_name,
                metadata={
                    "external_reference": org_mirror_repo.external_repo_name,
                },
            )

        except Exception as e:
            logger.exception("Failed to create repository %s/%s: %s", org_name, repo_name, str(e))
            mark_repo_failed(org_mirror_repo, str(e))
            failed_count += 1

            logs_model.log_action(
                "org_mirror_repo_failed",
                namespace_name=org_name,
                repository_name=repo_name,
                metadata={
                    "error": str(e),
                    "external_reference": org_mirror_repo.external_repo_name,
                },
            )

    return created_count, skipped_count, failed_count
