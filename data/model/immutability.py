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
from data.database import User
from data.model import (
    DuplicateImmutabilityPolicy,
    ImmutabilityPolicyDoesNotExist,
    InvalidImmutabilityPolicy,
    InvalidRepositoryException,
    db_transaction,
    repository,
)
from data.model.user import get_active_namespace_user_by_username


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


def _is_duplicate_namespace_policy(
    namespace_id: int, policy_config: PolicyConfig, exclude_uuid: Optional[str] = None
) -> bool:
    """Check if a policy with the same tag_pattern already exists for namespace."""
    new_pattern = policy_config.get("tag_pattern")
    new_matches = policy_config.get("tag_pattern_matches", True)

    for row in NamespaceImmutabilityPolicyTable.select().where(
        NamespaceImmutabilityPolicyTable.namespace == namespace_id
    ):
        if exclude_uuid and row.uuid == exclude_uuid:
            continue
        existing = row.policy
        if (
            existing.get("tag_pattern") == new_pattern
            and existing.get("tag_pattern_matches", True) == new_matches
        ):
            return True
    return False


def _is_duplicate_repository_policy(
    repo_id: int, policy_config: PolicyConfig, exclude_uuid: Optional[str] = None
) -> bool:
    """Check if a policy with the same tag_pattern already exists for repository."""
    new_pattern = policy_config.get("tag_pattern")
    new_matches = policy_config.get("tag_pattern_matches", True)

    for row in RepositoryImmutabilityPolicyTable.select().where(
        RepositoryImmutabilityPolicyTable.repository == repo_id
    ):
        if exclude_uuid and row.uuid == exclude_uuid:
            continue
        existing = row.policy
        if (
            existing.get("tag_pattern") == new_pattern
            and existing.get("tag_pattern_matches", True) == new_matches
        ):
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
            raise DuplicateImmutabilityPolicy(
                "A policy with the same tag_pattern and tag_pattern_matches already exists"
            )

        return NamespaceImmutabilityPolicyTable.create(namespace=namespace.id, policy=policy_config)


def update_namespace_immutability_policy(
    orgname: str, uuid: str, policy_config: PolicyConfig
) -> bool:
    """Update namespace immutability policy."""
    _validate_policy(policy_config)
    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)

        if not get_namespace_immutability_policy(orgname, uuid):
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        if _is_duplicate_namespace_policy(namespace.id, policy_config, exclude_uuid=uuid):
            raise DuplicateImmutabilityPolicy(
                "A policy with the same tag_pattern and tag_pattern_matches already exists"
            )

        NamespaceImmutabilityPolicyTable.update(policy=policy_config).where(
            NamespaceImmutabilityPolicyTable.uuid == uuid,
            NamespaceImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
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
            raise DuplicateImmutabilityPolicy(
                "A policy with the same tag_pattern and tag_pattern_matches already exists"
            )

        return RepositoryImmutabilityPolicyTable.create(
            namespace=namespace.id, repository=repo.id, policy=policy_config
        )


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

        if not get_repository_immutability_policy(orgname, repo_name, uuid):
            raise ImmutabilityPolicyDoesNotExist(f"Policy {uuid} not found")

        if _is_duplicate_repository_policy(repo.id, policy_config, exclude_uuid=uuid):
            raise DuplicateImmutabilityPolicy(
                "A policy with the same tag_pattern and tag_pattern_matches already exists"
            )

        RepositoryImmutabilityPolicyTable.update(policy=policy_config).where(
            RepositoryImmutabilityPolicyTable.uuid == uuid,
            RepositoryImmutabilityPolicyTable.namespace == namespace.id,
        ).execute()
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
