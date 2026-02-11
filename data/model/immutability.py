import logging
import re
from functools import lru_cache
from re import Pattern
from typing import Optional, TypedDict

from data.database import (
    NamespaceImmutabilityPolicy as NamespaceImmutabilityPolicyTable,
)
from data.database import Repository
from data.database import (
    RepositoryImmutabilityPolicy as RepositoryImmutabilityPolicyTable,
)
from data.database import Tag, User, get_epoch_timestamp_ms
from data.model import (
    DuplicateImmutabilityPolicy,
    ImmutabilityPolicyDoesNotExist,
    InvalidImmutabilityPolicy,
    InvalidRepositoryException,
    db_transaction,
    repository,
)
from data.model.user import get_active_namespace_user_by_username

logger = logging.getLogger(__name__)


class PolicyConfig(TypedDict, total=False):
    tag_pattern: str
    tag_pattern_matches: bool


class NamespaceImmutabilityPolicy:
    def __init__(self, db_row: NamespaceImmutabilityPolicyTable) -> None:
        config = db_row.policy
        self._db_row = db_row
        self.uuid: str = db_row.uuid
        self.tag_pattern: Optional[str] = config.get("tag_pattern")
        self.tag_pattern_matches: bool = config.get("tag_pattern_matches", True)

    def get_view(self) -> dict[str, str | bool | None]:
        return {
            "uuid": self.uuid,
            "tagPattern": self.tag_pattern,
            "tagPatternMatches": self.tag_pattern_matches,
        }


class RepositoryImmutabilityPolicy:
    def __init__(self, db_row: RepositoryImmutabilityPolicyTable) -> None:
        config = db_row.policy
        self._db_row = db_row
        self.uuid: str = db_row.uuid
        self.tag_pattern: Optional[str] = config.get("tag_pattern")
        self.tag_pattern_matches: bool = config.get("tag_pattern_matches", True)

    def get_view(self) -> dict[str, str | bool | None]:
        return {
            "uuid": self.uuid,
            "tagPattern": self.tag_pattern,
            "tagPatternMatches": self.tag_pattern_matches,
        }


def _validate_policy(policy_config: PolicyConfig) -> None:
    """Validate policy config. Raises InvalidImmutabilityPolicy on error."""
    tag_pattern = policy_config.get("tag_pattern")

    if not tag_pattern or not isinstance(tag_pattern, str):
        raise InvalidImmutabilityPolicy("tag_pattern is required and must be a non-empty string")

    if len(tag_pattern) > 256:
        raise InvalidImmutabilityPolicy("tag_pattern must be 256 characters or less")

    try:
        re.compile(tag_pattern)
    except re.error as e:
        raise InvalidImmutabilityPolicy(f"Invalid regex pattern: {e}")

    tag_pattern_matches = policy_config.get("tag_pattern_matches")
    if tag_pattern_matches is not None and not isinstance(tag_pattern_matches, bool):
        raise InvalidImmutabilityPolicy("tag_pattern_matches must be a boolean")


@lru_cache(maxsize=256)
def _compile_pattern(pattern: str) -> Pattern[str]:
    return re.compile(pattern)


def _matches_policy(tag_name: str, tag_pattern: str, tag_pattern_matches: bool) -> bool:
    """Check if tag should be immutable based on pattern."""
    try:
        matches = bool(_compile_pattern(tag_pattern).match(tag_name))
    except re.error:
        return False
    return matches if tag_pattern_matches else not matches


def _fetch_candidate_tags_batch(
    namespace_id: int,
    repository_id: Optional[int],
    last_id: int,
    limit: int,
) -> list[Tag]:
    """
    Fetch a batch of alive, non-hidden tags for processing using keyset pagination.

    Uses WHERE id > last_id instead of OFFSET for O(1) performance per batch,
    regardless of position in the result set.

    For namespace policies (repository_id=None): all tags across all repositories in namespace.
    For repository policies: tags only in the specific repository.
    """
    now_ms = get_epoch_timestamp_ms()

    if repository_id is not None:
        # Repository-scoped query
        query = Tag.select(Tag.id, Tag.name, Tag.immutable).where(
            Tag.repository == repository_id,
            Tag.hidden == False,  # noqa: E712
            (Tag.lifetime_end_ms.is_null()) | (Tag.lifetime_end_ms > now_ms),
            Tag.id > last_id,
        )
        query = query.order_by(Tag.id).limit(limit)  # type: ignore[func-returns-value]
    else:
        # Namespace-scoped query - join with Repository to filter by namespace
        query = (
            Tag.select(Tag.id, Tag.name, Tag.immutable)
            .join(Repository)
            .where(
                Repository.namespace_user == namespace_id,
                Tag.hidden == False,  # noqa: E712
                (Tag.lifetime_end_ms.is_null()) | (Tag.lifetime_end_ms > now_ms),
                Tag.id > last_id,
            )
        )
        query = query.order_by(Tag.id).limit(limit)  # type: ignore[func-returns-value]

    return list(query)


def _mark_tags_immutable_batch(tag_ids: list[int]) -> int:
    """
    Mark a batch of tags as immutable.

    Returns the number of tags updated.
    """
    if not tag_ids:
        return 0

    return (
        Tag.update(immutable=True)
        .where(
            Tag.id << tag_ids,
            Tag.immutable == False,  # noqa: E712 - Idempotent: only update if not already immutable
        )
        .execute()
    )


def apply_immutability_policy_to_existing_tags(
    namespace_id: int,
    repository_id: Optional[int],
    tag_pattern: str,
    tag_pattern_matches: bool,
    batch_size: int = 500,
) -> int:
    """
    Retroactively apply an immutability policy to existing tags.

    Fetches tags in batches, filters matching tags using _matches_policy(),
    and marks them as immutable.

    Args:
        namespace_id: The namespace ID
        repository_id: The repository ID (None for namespace-wide policies)
        tag_pattern: The regex pattern to match tag names
        tag_pattern_matches: If True, matching tags become immutable.
                            If False, non-matching tags become immutable.
        batch_size: Number of tags to process per batch

    Returns:
        Total count of newly marked tags
    """
    total_marked = 0
    last_id = 0

    while True:
        tags = _fetch_candidate_tags_batch(namespace_id, repository_id, last_id, batch_size)

        if not tags:
            break

        # Filter to tags that match the policy and are not already immutable
        tag_ids_to_mark = [
            tag.id
            for tag in tags
            if not tag.immutable and _matches_policy(tag.name, tag_pattern, tag_pattern_matches)
        ]

        if tag_ids_to_mark:
            marked = _mark_tags_immutable_batch(tag_ids_to_mark)
            total_marked += marked

        last_id = tags[-1].id

    return total_marked


def _is_duplicate_namespace_policy(
    namespace_id: int, policy_config: PolicyConfig, exclude_uuid: Optional[str] = None
) -> bool:
    """Check if a policy with the same tag_pattern already exists for namespace."""
    new_pattern = policy_config.get("tag_pattern")

    for row in NamespaceImmutabilityPolicyTable.select().where(
        NamespaceImmutabilityPolicyTable.namespace == namespace_id
    ):
        if exclude_uuid and row.uuid == exclude_uuid:
            continue
        existing = row.policy
        if existing.get("tag_pattern") == new_pattern:
            return True
    return False


def _is_duplicate_repository_policy(
    repo_id: int, policy_config: PolicyConfig, exclude_uuid: Optional[str] = None
) -> bool:
    """Check if a policy with the same tag_pattern already exists for repository."""
    new_pattern = policy_config.get("tag_pattern")

    for row in RepositoryImmutabilityPolicyTable.select().where(
        RepositoryImmutabilityPolicyTable.repository == repo_id
    ):
        if exclude_uuid and row.uuid == exclude_uuid:
            continue
        existing = row.policy
        if existing.get("tag_pattern") == new_pattern:
            return True
    return False


# Namespace policy CRUD


def get_namespace_immutability_policies(orgname: str) -> list[NamespaceImmutabilityPolicy]:
    """Get all immutability policies for namespace."""
    query = NamespaceImmutabilityPolicyTable.select().join(User).where(User.username == orgname)
    return [NamespaceImmutabilityPolicy(row) for row in query]


def get_namespace_immutability_policy(
    orgname: str, uuid: str
) -> Optional[NamespaceImmutabilityPolicy]:
    """Get specific policy by uuid."""
    try:
        row = (
            NamespaceImmutabilityPolicyTable.select()
            .join(User)
            .where(NamespaceImmutabilityPolicyTable.uuid == uuid, User.username == orgname)
            .get()
        )
        return NamespaceImmutabilityPolicy(row)
    except NamespaceImmutabilityPolicyTable.DoesNotExist:
        return None


def create_namespace_immutability_policy(
    orgname: str, policy_config: PolicyConfig
) -> NamespaceImmutabilityPolicyTable:
    """Create namespace immutability policy."""
    _validate_policy(policy_config)
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)

        if _is_duplicate_namespace_policy(namespace.id, policy_config):
            raise DuplicateImmutabilityPolicy("A policy with the same tag_pattern already exists")

        policy = NamespaceImmutabilityPolicyTable.create(
            namespace=namespace.id, policy=policy_config
        )
        namespace_id = namespace.id
        policy_uuid = policy.uuid

    # Retroactively apply policy to existing tags (outside transaction to avoid long locks)
    # If this fails, delete the policy and re-raise the exception
    try:
        apply_immutability_policy_to_existing_tags(
            namespace_id=namespace_id,
            repository_id=None,
            tag_pattern=policy_config["tag_pattern"],
            tag_pattern_matches=policy_config.get("tag_pattern_matches", True),
        )
    except Exception:
        logger.exception(
            "Failed to retroactively apply namespace immutability policy, rolling back"
        )
        try:
            NamespaceImmutabilityPolicyTable.delete().where(
                NamespaceImmutabilityPolicyTable.uuid == policy_uuid
            ).execute()
        except Exception:
            logger.exception(
                "Failed to rollback policy creation for namespace policy %s. "
                "Manual intervention may be required to delete the orphaned policy.",
                policy_uuid,
            )
        raise

    return policy


def update_namespace_immutability_policy(
    orgname: str, uuid: str, policy_config: PolicyConfig
) -> bool:
    """Update namespace immutability policy."""
    _validate_policy(policy_config)
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)

        old_policy = get_namespace_immutability_policy(orgname, uuid)
        if not old_policy:
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        # Save old config for potential rollback
        old_config: PolicyConfig = {
            "tag_pattern": old_policy.tag_pattern or "",
            "tag_pattern_matches": old_policy.tag_pattern_matches,
        }

        if _is_duplicate_namespace_policy(namespace.id, policy_config, exclude_uuid=uuid):
            raise DuplicateImmutabilityPolicy("A policy with the same tag_pattern already exists")

        NamespaceImmutabilityPolicyTable.update(policy=policy_config).where(
            NamespaceImmutabilityPolicyTable.uuid == uuid,
            NamespaceImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
        namespace_id = namespace.id

    # Retroactively apply policy to existing tags (outside transaction to avoid long locks)
    # If this fails, restore the old config and re-raise the exception
    try:
        apply_immutability_policy_to_existing_tags(
            namespace_id=namespace_id,
            repository_id=None,
            tag_pattern=policy_config["tag_pattern"],
            tag_pattern_matches=policy_config.get("tag_pattern_matches", True),
        )
    except Exception:
        logger.exception(
            "Failed to retroactively apply namespace immutability policy, rolling back"
        )
        try:
            NamespaceImmutabilityPolicyTable.update(policy=old_config).where(
                NamespaceImmutabilityPolicyTable.uuid == uuid,
                NamespaceImmutabilityPolicyTable.namespace == namespace_id,
            ).execute()
        except Exception:
            logger.exception(
                "Failed to rollback namespace policy %s update. "
                "Policy config may be inconsistent (current: %s, expected: %s). "
                "Manual intervention may be required.",
                uuid,
                policy_config,
                old_config,
            )
        raise

    return True


def delete_namespace_immutability_policy(orgname: str, uuid: str) -> bool:
    """Delete namespace immutability policy."""
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)

        if not get_namespace_immutability_policy(orgname, uuid):
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        NamespaceImmutabilityPolicyTable.delete().where(
            NamespaceImmutabilityPolicyTable.uuid == uuid,
            NamespaceImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
        return True


# Repository policy CRUD


def get_repository_immutability_policies(
    orgname: str, repo_name: str
) -> list[RepositoryImmutabilityPolicy]:
    """Get all immutability policies for repository."""
    query = (
        RepositoryImmutabilityPolicyTable.select()
        .join(Repository)
        .join(User)
        .where(User.username == orgname, Repository.name == repo_name)
    )
    return [RepositoryImmutabilityPolicy(row) for row in query]


def get_repository_immutability_policy(
    orgname: str, repo_name: str, uuid: str
) -> Optional[RepositoryImmutabilityPolicy]:
    """Get specific policy by uuid."""
    try:
        row = (
            RepositoryImmutabilityPolicyTable.select()
            .join(Repository)
            .join(User)
            .where(
                User.username == orgname,
                Repository.name == repo_name,
                RepositoryImmutabilityPolicyTable.uuid == uuid,
            )
            .get()
        )
        return RepositoryImmutabilityPolicy(row)
    except RepositoryImmutabilityPolicyTable.DoesNotExist:
        return None


def create_repository_immutability_policy(
    orgname: str, repo_name: str, policy_config: PolicyConfig
) -> RepositoryImmutabilityPolicyTable:
    """Create repository immutability policy."""
    _validate_policy(policy_config)
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)
        repo = repository.get_repository(orgname, repo_name)

        if repo is None:
            raise InvalidRepositoryException(f"Repository does not exist: {repo_name}")

        if _is_duplicate_repository_policy(repo.id, policy_config):
            raise DuplicateImmutabilityPolicy("A policy with the same tag_pattern already exists")

        policy = RepositoryImmutabilityPolicyTable.create(
            namespace=namespace.id, repository=repo.id, policy=policy_config
        )
        namespace_id = namespace.id
        repo_id = repo.id
        policy_uuid = policy.uuid

    # Retroactively apply policy to existing tags (outside transaction to avoid long locks)
    # If this fails, delete the policy and re-raise the exception
    try:
        apply_immutability_policy_to_existing_tags(
            namespace_id=namespace_id,
            repository_id=repo_id,
            tag_pattern=policy_config["tag_pattern"],
            tag_pattern_matches=policy_config.get("tag_pattern_matches", True),
        )
    except Exception:
        logger.exception(
            "Failed to retroactively apply repository immutability policy, rolling back"
        )
        try:
            RepositoryImmutabilityPolicyTable.delete().where(
                RepositoryImmutabilityPolicyTable.uuid == policy_uuid
            ).execute()
        except Exception:
            logger.exception(
                "Failed to rollback policy creation for repository policy %s. "
                "Manual intervention may be required to delete the orphaned policy.",
                policy_uuid,
            )
        raise

    return policy


def update_repository_immutability_policy(
    orgname: str, repo_name: str, uuid: str, policy_config: PolicyConfig
) -> bool:
    """Update repository immutability policy."""
    _validate_policy(policy_config)
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)
        repo = repository.get_repository(orgname, repo_name)

        if repo is None:
            raise InvalidRepositoryException(f"Repository does not exist: {repo_name}")

        old_policy = get_repository_immutability_policy(orgname, repo_name, uuid)
        if not old_policy:
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        # Save old config for potential rollback
        old_config: PolicyConfig = {
            "tag_pattern": old_policy.tag_pattern or "",
            "tag_pattern_matches": old_policy.tag_pattern_matches,
        }

        if _is_duplicate_repository_policy(repo.id, policy_config, exclude_uuid=uuid):
            raise DuplicateImmutabilityPolicy("A policy with the same tag_pattern already exists")

        RepositoryImmutabilityPolicyTable.update(policy=policy_config).where(
            RepositoryImmutabilityPolicyTable.uuid == uuid,
            RepositoryImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
        namespace_id = namespace.id
        repo_id = repo.id

    # Retroactively apply policy to existing tags (outside transaction to avoid long locks)
    # If this fails, restore the old config and re-raise the exception
    try:
        apply_immutability_policy_to_existing_tags(
            namespace_id=namespace_id,
            repository_id=repo_id,
            tag_pattern=policy_config["tag_pattern"],
            tag_pattern_matches=policy_config.get("tag_pattern_matches", True),
        )
    except Exception:
        logger.exception(
            "Failed to retroactively apply repository immutability policy, rolling back"
        )
        try:
            RepositoryImmutabilityPolicyTable.update(policy=old_config).where(
                RepositoryImmutabilityPolicyTable.uuid == uuid,
                RepositoryImmutabilityPolicyTable.namespace == namespace_id,
            ).execute()
        except Exception:
            logger.exception(
                "Failed to rollback repository policy %s update. "
                "Policy config may be inconsistent (current: %s, expected: %s). "
                "Manual intervention may be required.",
                uuid,
                policy_config,
                old_config,
            )
        raise

    return True


def delete_repository_immutability_policy(orgname: str, repo_name: str, uuid: str) -> bool:
    """Delete repository immutability policy."""
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)
        repo = repository.get_repository(orgname, repo_name)

        if repo is None:
            raise InvalidRepositoryException(f"Repository does not exist: {repo_name}")

        if not get_repository_immutability_policy(orgname, repo_name, uuid):
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        RepositoryImmutabilityPolicyTable.delete().where(
            RepositoryImmutabilityPolicyTable.uuid == uuid,
            RepositoryImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
        return True


# Policy evaluation


def evaluate_immutability_policies(repository_id: int, namespace_id: int, tag_name: str) -> bool:
    """
    Check if tag should be marked immutable based on policies.
    Returns True if any policy matches.

    This function performs two separate queries (repository policies, then namespace
    policies) and returns early on first match. This design is acceptable because:
    - Policy tables are expected to remain small (few policies per namespace/repo)
    - Function is typically called once per tag creation, not in a loop
    - Early return on first match minimizes query overhead in the common case
    """
    # Check repository policies
    for row in RepositoryImmutabilityPolicyTable.select().where(
        RepositoryImmutabilityPolicyTable.repository == repository_id
    ):
        config = row.policy
        if _matches_policy(
            tag_name, config.get("tag_pattern"), config.get("tag_pattern_matches", True)
        ):
            return True

    # Check namespace policies
    for row in NamespaceImmutabilityPolicyTable.select().where(
        NamespaceImmutabilityPolicyTable.namespace == namespace_id
    ):
        config = row.policy
        if _matches_policy(
            tag_name, config.get("tag_pattern"), config.get("tag_pattern_matches", True)
        ):
            return True

    return False


def namespace_has_immutable_tags(namespace_id: int) -> bool:
    """
    Check if any repository in the namespace has immutable tags.
    """
    now_ms = get_epoch_timestamp_ms()

    return (
        Tag.select()
        .join(Repository, on=(Tag.repository == Repository.id))
        .where(
            Repository.namespace_user == namespace_id,
            Tag.immutable == True,  # noqa: E712
            Tag.hidden == False,  # noqa: E712
            (Tag.lifetime_end_ms.is_null()) | (Tag.lifetime_end_ms > now_ms),
        )
        .exists()
    )
