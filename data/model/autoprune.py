import json
import logging.config
import re
from enum import Enum

from data.database import AutoPruneTaskStatus
from data.database import NamespaceAutoPrunePolicy as NamespaceAutoPrunePolicyTable
from data.database import Repository
from data.database import RepositoryAutoPrunePolicy as RepositoryAutoPrunePolicyTable
from data.database import RepositoryState, User, db_for_update, get_epoch_timestamp_ms
from data.model import (
    InvalidNamespaceAutoPruneMethod,
    InvalidNamespaceAutoPrunePolicy,
    InvalidNamespaceException,
    InvalidRepositoryAutoPrunePolicy,
    InvalidRepositoryException,
    NamespaceAutoPrunePolicyAlreadyExists,
    NamespaceAutoPrunePolicyDoesNotExist,
    RepositoryAutoPrunePolicyAlreadyExists,
    RepositoryAutoPrunePolicyDoesNotExist,
    db_transaction,
    log,
    modelutil,
    oci,
    repository,
    user,
)
from data.model.user import get_active_namespace_user_by_username
from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)
# Define a constant for the SKIP_LOCKED flag for testing purposes,
# since we test with mysql 5.7 which does not support this flag.
SKIP_LOCKED = True


class AutoPruneMethod(Enum):
    NUMBER_OF_TAGS = "number_of_tags"
    CREATION_DATE = "creation_date"


class NamespaceAutoPrunePolicy:
    def __init__(self, db_row=None, policy_dict=None):
        if db_row is not None:
            config = json.loads(db_row.policy)
            self._db_row = db_row
            self.uuid = db_row.uuid
            self.method = config.get("method")
            self.config = config
        elif policy_dict is not None:
            self._db_row = None
            self.uuid = None
            self.method = policy_dict.get("method")
            self.config = policy_dict

    def get_row(self):
        return self._db_row

    def get_view(self):
        return {
            "uuid": self.uuid,
            "method": self.method,
            "value": self.config.get("value"),
            "tagPattern": self.config.get("tag_pattern"),
            "tagPatternMatches": self.config.get("tag_pattern_matches"),
        }


class RepositoryAutoPrunePolicy:
    def __init__(self, db_row=None, policy_dict=None):
        if db_row is not None:
            config = json.loads(db_row.policy)
            self._db_row = db_row
            self.uuid = db_row.uuid
            self.method = config.get("method")
            self.config = config
            self.repository_id = db_row.repository_id
        elif policy_dict is not None:
            self._db_row = None
            self.uuid = None
            self.method = policy_dict.get("method")
            self.config = policy_dict
            self.repository_id = None

    def get_row(self):
        return self._db_row

    def get_view(self):
        return {
            "uuid": self.uuid,
            "method": self.method,
            "value": self.config.get("value"),
            "tagPattern": self.config.get("tag_pattern"),
            "tagPatternMatches": self.config.get("tag_pattern_matches"),
        }


def valid_value(method, value):
    """
    Method for validating the value provided for the policy method.
    """

    if not value:
        return False

    if method == AutoPruneMethod.NUMBER_OF_TAGS and isinstance(value, int) and value > 0:
        return True

    elif method == AutoPruneMethod.CREATION_DATE:
        if isinstance(value, str):
            try:
                convert_to_timedelta(value)
                return True
            except ValueError:
                return False

    return False


def assert_valid_namespace_autoprune_policy(policy_config):
    """
    Asserts that the policy config is valid.
    """
    try:
        method = AutoPruneMethod(policy_config.get("method"))
    except ValueError:
        raise InvalidNamespaceAutoPrunePolicy("Invalid method provided")

    if not valid_value(method, policy_config.get("value")):
        raise InvalidNamespaceAutoPrunePolicy("Invalid value given for method type")

    if policy_config.get("tag_pattern") is not None:
        if not isinstance(policy_config.get("tag_pattern"), str):
            raise InvalidNamespaceAutoPrunePolicy("tag_pattern must be string")

        if policy_config.get("tag_pattern") == "":
            raise InvalidNamespaceAutoPrunePolicy("tag_pattern cannot be empty")

    if policy_config.get("tag_pattern_matches") is not None and not isinstance(
        policy_config.get("tag_pattern_matches"), bool
    ):
        raise InvalidNamespaceAutoPrunePolicy("tag_pattern_matches must be bool")


def assert_valid_repository_autoprune_policy(policy_config):
    """
    Asserts that the policy config is valid.
    """
    try:
        method = AutoPruneMethod(policy_config.get("method"))
    except ValueError:
        raise InvalidRepositoryAutoPrunePolicy("Invalid method provided")

    if not valid_value(method, policy_config.get("value")):
        raise InvalidRepositoryAutoPrunePolicy("Invalid value given for method type")

    if policy_config.get("tag_pattern") is not None:
        if not isinstance(policy_config.get("tag_pattern"), str):
            raise InvalidRepositoryAutoPrunePolicy("tag_pattern must be string")

        if policy_config.get("tag_pattern") == "":
            raise InvalidRepositoryAutoPrunePolicy("tag_pattern cannot be empty")

    if policy_config.get("tag_pattern_matches") is not None and not isinstance(
        policy_config.get("tag_pattern_matches"), bool
    ):
        raise InvalidRepositoryAutoPrunePolicy("tag_pattern_matches must be bool")


def get_namespace_autoprune_policies_by_orgname(orgname):
    """
    Get the autopruning policies for the specified namespace.
    """
    query = (
        NamespaceAutoPrunePolicyTable.select(NamespaceAutoPrunePolicyTable)
        .join(User)
        .where(
            User.username == orgname,
        )
    )
    return [NamespaceAutoPrunePolicy(row) for row in query]


def get_repository_autoprune_policies_by_repo_name(orgname, repo_name):
    """
    Get the autopruning policies for the specified repository.
    """
    query = (
        RepositoryAutoPrunePolicyTable.select(RepositoryAutoPrunePolicyTable)
        .join(Repository)
        .join(User)
        .where(
            User.username == orgname,
            RepositoryAutoPrunePolicyTable.repository == Repository.id,
            Repository.name == repo_name,
        )
    )
    return [RepositoryAutoPrunePolicy(row) for row in query]


def get_repository_autoprune_policies_by_repo_id(repo_id):
    """
    Get the autopruning policies for the specified repository.
    """

    query = RepositoryAutoPrunePolicyTable.select().where(
        RepositoryAutoPrunePolicyTable.repository == repo_id,
    )
    return [RepositoryAutoPrunePolicy(row) for row in query]


def get_namespace_autoprune_policies_by_id(namespace_id):
    """
    Get the autopruning policies for the namespace by id.
    """
    query = NamespaceAutoPrunePolicyTable.select().where(
        NamespaceAutoPrunePolicyTable.namespace == namespace_id,
    )
    return [NamespaceAutoPrunePolicy(row) for row in query]


def get_repository_autoprune_policies_by_namespace_id(namespace_id):
    """
    Get all repository autopruning policies for a namespace by id.
    """
    query = RepositoryAutoPrunePolicyTable.select().where(
        RepositoryAutoPrunePolicyTable.namespace == namespace_id,
    )
    return [RepositoryAutoPrunePolicy(row) for row in query]


def get_namespace_autoprune_policy(orgname, uuid):
    """
    Get the specific autopruning policy for the specified namespace by uuid.
    """
    try:
        row = (
            NamespaceAutoPrunePolicyTable.select(NamespaceAutoPrunePolicyTable)
            .join(User)
            .where(NamespaceAutoPrunePolicyTable.uuid == uuid, User.username == orgname)
            .get()
        )
        return NamespaceAutoPrunePolicy(row)
    except NamespaceAutoPrunePolicyTable.DoesNotExist:
        return None


def get_repository_autoprune_policy_by_uuid(repo_name, uuid):
    """
    Get the specific autopruning policy for the specified repository by uuid.
    """
    try:
        row = (
            RepositoryAutoPrunePolicyTable.select(RepositoryAutoPrunePolicyTable)
            .join(Repository)
            .where(Repository.name == repo_name, RepositoryAutoPrunePolicyTable.uuid == uuid)
            .get()
        )
        return RepositoryAutoPrunePolicy(row)
    except RepositoryAutoPrunePolicyTable.DoesNotExist:
        return None


def create_namespace_autoprune_policy(orgname, policy_config, create_task=False):
    """
    Creates the namespace auto-prune policy. If create_task is True, then it will also create
    the auto-prune task for the namespace. This will be used to run the auto-prune task. Deletion
    of the task will be handled by the autoprune worker.
    """

    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)
        namespace_id = namespace.id

        assert_valid_namespace_autoprune_policy(policy_config)

        if duplicate_namespace_policy(namespace_id, policy_config):
            raise NamespaceAutoPrunePolicyAlreadyExists(
                "Existing policy with same values for this namespace, duplicate policies are not permitted"
            )

        new_policy = NamespaceAutoPrunePolicyTable.create(
            namespace=namespace_id, policy=json.dumps(policy_config)
        )

        if create_task and not namespace_has_autoprune_task(namespace_id):
            create_autoprune_task(namespace_id)

        return new_policy


def create_repository_autoprune_policy(orgname, repo_name, policy_config, create_task=False):
    """
    Creates the repository auto-prune policy. If create_task is True, it will check if auto-prune task is not already present,
    and only then it will create the auto-prune task. Deletion of the task will be handled by the autoprune worker.
    """

    with db_transaction():
        namespace = get_active_namespace_user_by_username(orgname)
        namespace_id = namespace.id

        repo = repository.get_repository(orgname, repo_name)

        if repo is None:
            raise InvalidRepositoryException("Repository does not exist: %s" % repo_name)

        assert_valid_repository_autoprune_policy(policy_config)

        if duplicate_repository_policy(repo.id, policy_config):
            raise RepositoryAutoPrunePolicyAlreadyExists(
                "Existing policy with same values for this repository, duplicate policies are not permitted"
            )

        new_policy = RepositoryAutoPrunePolicyTable.create(
            namespace=namespace_id, repository=repo.id, policy=json.dumps(policy_config)
        )
        if create_task and not namespace_has_autoprune_task(namespace_id):
            create_autoprune_task(namespace_id)

        return new_policy


def update_namespace_autoprune_policy(orgname, uuid, policy_config):
    """
    Updates the namespace auto-prune policy with the provided policy config
    for the specified uuid.
    """

    namespace = get_active_namespace_user_by_username(orgname)
    namespace_id = namespace.id

    policy = get_namespace_autoprune_policy(orgname, uuid)
    if policy is None:
        raise NamespaceAutoPrunePolicyDoesNotExist(
            f"Policy not found for namespace: {orgname} with uuid: {uuid}"
        )

    assert_valid_namespace_autoprune_policy(policy_config)

    (
        NamespaceAutoPrunePolicyTable.update(policy=json.dumps(policy_config))
        .where(
            NamespaceAutoPrunePolicyTable.uuid == uuid,
            NamespaceAutoPrunePolicyTable.namespace == namespace_id,
        )
        .execute()
    )
    return True


def update_repository_autoprune_policy(orgname, repo_name, uuid, policy_config):
    """
    Updates the repository auto-prune policy with the provided policy config
    for the specified uuid.
    """

    namespace = get_active_namespace_user_by_username(orgname)
    namespace_id = namespace.id

    repo = repository.get_repository(orgname, repo_name)
    if repo is None:
        raise InvalidRepositoryException("Repository does not exist: %s" % repo_name)

    policy = get_repository_autoprune_policy_by_uuid(repo_name, uuid)
    if policy is None:
        raise RepositoryAutoPrunePolicyDoesNotExist(
            f"Policy not found for repository: {repo_name} with uuid: {uuid}"
        )

    assert_valid_repository_autoprune_policy(policy_config)

    (
        RepositoryAutoPrunePolicyTable.update(policy=json.dumps(policy_config))
        .where(
            RepositoryAutoPrunePolicyTable.uuid == uuid,
            RepositoryAutoPrunePolicyTable.namespace == namespace_id,
        )
        .execute()
    )
    return True


def delete_namespace_autoprune_policy(orgname, uuid):
    """
    Deletes the namespace policy specified by the uuid
    """

    with db_transaction():
        try:
            namespace_id = User.select().where(User.username == orgname).get().id
        except User.DoesNotExist:
            raise InvalidNamespaceException("Invalid namespace provided: %s" % (orgname))

        policy = get_namespace_autoprune_policy(orgname, uuid)
        if policy is None:
            raise NamespaceAutoPrunePolicyDoesNotExist(
                f"Policy not found for namespace: {orgname} with uuid: {uuid}"
            )

        response = (
            NamespaceAutoPrunePolicyTable.delete()
            .where(
                NamespaceAutoPrunePolicyTable.uuid == uuid,
                NamespaceAutoPrunePolicyTable.namespace == namespace_id,
            )
            .execute()
        )

        if not response:
            raise NamespaceAutoPrunePolicyTable.DoesNotExist(
                f"Policy not found for namespace: {orgname} with uuid: {uuid}"
            )
        return True


def delete_repository_autoprune_policy(orgname, repo_name, uuid):
    """
    Deletes the repository policy specified by the uuid
    """

    with db_transaction():
        try:
            namespace_id = User.select().where(User.username == orgname).get().id
        except User.DoesNotExist:
            raise InvalidNamespaceException("Invalid namespace provided: %s" % (orgname))

        repo = repository.get_repository(orgname, repo_name)
        if repo is None:
            raise InvalidRepositoryException("Repository does not exist: %s" % repo_name)

        policy = get_repository_autoprune_policy_by_uuid(repo_name, uuid)
        if policy is None:
            raise RepositoryAutoPrunePolicyDoesNotExist(
                f"Policy not found for repository: {repo_name} with uuid: {uuid}"
            )

        response = (
            RepositoryAutoPrunePolicyTable.delete()
            .where(
                RepositoryAutoPrunePolicyTable.uuid == uuid,
                RepositoryAutoPrunePolicyTable.namespace == namespace_id,
            )
            .execute()
        )

        if not response:
            raise RepositoryAutoPrunePolicyTable.DoesNotExist(
                f"Policy not found for repository: {repo_name} with uuid: {uuid}"
            )
        return True


def check_existing_policy(db_policy, policy_config):
    if (
        db_policy["method"] == policy_config["method"]
        and db_policy["value"] == policy_config["value"]
        and db_policy.get("tag_pattern", None) == policy_config.get("tag_pattern", None)
        and db_policy.get("tag_pattern_matches", True)
        == policy_config.get("tag_pattern_matches", True)
    ):
        return True
    return False


def duplicate_namespace_policy(namespace_id, policy_config):
    result = NamespaceAutoPrunePolicyTable.select().where(
        NamespaceAutoPrunePolicyTable.namespace == namespace_id
    )

    for r in result:
        db_policy = json.loads(r.policy)
        if check_existing_policy(db_policy, policy_config):
            return True
    return False


def duplicate_repository_policy(repo_id, policy_config):
    result = RepositoryAutoPrunePolicyTable.select().where(
        RepositoryAutoPrunePolicyTable.repository == repo_id
    )

    for r in result:
        db_policy = json.loads(r.policy)
        if check_existing_policy(db_policy, policy_config):
            return True
    return False


def namespace_has_autoprune_policy(namespace_id):
    return (
        NamespaceAutoPrunePolicyTable.select(1)
        .where(NamespaceAutoPrunePolicyTable.namespace == namespace_id)
        .exists()
    )


def repository_has_autoprune_policy(repository_id):
    return (
        RepositoryAutoPrunePolicyTable.select(1)
        .where(RepositoryAutoPrunePolicyTable.repository == repository_id)
        .exists()
    )


def namespace_has_autoprune_task(namespace_id):
    return (
        AutoPruneTaskStatus.select(1).where(AutoPruneTaskStatus.namespace == namespace_id).exists()
    )


def create_autoprune_task(namespace_id):
    AutoPruneTaskStatus.create(namespace=namespace_id, status="queued", last_ran_ms=None)


def update_autoprune_task(task, task_status):
    try:
        task.status = task_status
        task.save()
    except AutoPruneTaskStatus.DoesNotExist:
        return None
    except Exception as err:
        raise Exception(
            f"Error updating autoprune task for namespace id: {task.namespace_id}, task_status: {task_status} with error as: {str(err)}"
        )


def fetch_autoprune_task(task_run_interval_ms=60 * 60 * 1000):
    """
    Get the auto prune task prioritized by last_ran_ms = None followed by asc order of last_ran_ms.
    task_run_interval_ms specifies how long a task must wait before being ran again.
    Prevents the other workers from picking up the same task by updating last_ran_ms on the task.
    """
    with db_transaction():
        try:
            # We have to check for enabled User as a sub query since a join would lock the User row too
            query = (
                AutoPruneTaskStatus.select(AutoPruneTaskStatus)
                .where(
                    AutoPruneTaskStatus.namespace.not_in(
                        # this basically skips ns if user is not enabled
                        User.select(User.id).where(
                            User.enabled == False, User.id == AutoPruneTaskStatus.namespace
                        )
                    ),
                    (
                        AutoPruneTaskStatus.last_ran_ms
                        < get_epoch_timestamp_ms() - task_run_interval_ms
                    )
                    | (AutoPruneTaskStatus.last_ran_ms.is_null(True)),
                )
                .order_by(AutoPruneTaskStatus.last_ran_ms.asc(nulls="first"))
            )
            task = db_for_update(query, skip_locked=SKIP_LOCKED).get()
        except AutoPruneTaskStatus.DoesNotExist:
            return None

        task.last_ran_ms = get_epoch_timestamp_ms()
        task.status = "running"
        task.save()

        return task


def fetch_autoprune_task_by_namespace_id(namespace_id):
    try:
        return (
            AutoPruneTaskStatus.select().where(AutoPruneTaskStatus.namespace == namespace_id).get()
        )
    except AutoPruneTaskStatus.DoesNotExist:
        return None


def delete_autoprune_task(task):
    try:
        task.delete_instance()
    except AutoPruneTaskStatus.DoesNotExist:
        return None
    except Exception as err:
        raise Exception(
            f"Error deleting autoprune task for namespace id: {task.namespace_id} with error as: {str(err)}"
        )


def prune_tags(tags, repo, namespace):
    for tag in tags:
        try:
            tag = oci.tag.delete_tag(repo.id, tag.name)
            if tag is not None:
                log.log_action(
                    "autoprune_tag_delete",
                    namespace.username,
                    repository=repo,
                    metadata={
                        "performer": "autoprune worker",
                        "namespace": namespace.username,
                        "repo": repo.name,
                        "tag": tag.name,
                    },
                )
        except Exception as err:
            raise Exception(
                f"Error deleting tag with name: {tag.name} with repository id: {repo.id} with error as: {str(err)}"
            )


def fetch_tags_expiring_by_tag_count_policy(
    repo_id, policy_config, tag_page_limit=100, exclude_tags=None
):
    """
    Fetch tags in the given repository based on the number of tags specified in the policy config.
    """
    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.NUMBER_OF_TAGS.value:
        raise InvalidNamespaceAutoPruneMethod(
            f"Expected prune method type {AutoPruneMethod.NUMBER_OF_TAGS.value} but got {policy_method}"
        )

    assert_valid_namespace_autoprune_policy(policy_config)
    all_tags = []
    page = 1
    while True:
        tags = oci.tag.fetch_paginated_autoprune_repo_tags_by_number(
            repo_id,
            int(policy_config["value"]),
            tag_page_limit,
            page,
            policy_config.get("tag_pattern"),
            policy_config.get("tag_pattern_matches"),
            exclude_tags,
        )
        if len(tags) == 0:
            break

        all_tags.extend(tags)
        page += 1

    return all_tags


def prune_repo_by_number_of_tags(repo, policy_config, namespace, tag_page_limit):
    tags = fetch_tags_expiring_by_tag_count_policy(repo.id, policy_config, tag_page_limit)
    prune_tags(tags, repo, namespace)


def fetch_tags_expiring_by_creation_date_policy(repo_id, policy_config, tag_page_limit=100):
    """
    Fetch tags in the given repository based on the creation date specified in the policy config,
    where the value is a valid timedelta string. (e.g. 1d, 1w, 1m, 1y)
    """
    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.CREATION_DATE.value:
        raise InvalidNamespaceAutoPruneMethod(
            f"Expected prune method type {AutoPruneMethod.CREATION_DATE.value} but got {policy_method}"
        )

    assert_valid_namespace_autoprune_policy(policy_config)

    all_tags = []
    time_ms = int(convert_to_timedelta(policy_config["value"]).total_seconds() * 1000)
    page = 1
    while True:
        tags = oci.tag.fetch_paginated_autoprune_repo_tags_older_than_ms(
            repo_id,
            time_ms,
            tag_page_limit,
            page,
            policy_config.get("tag_pattern"),
            policy_config.get("tag_pattern_matches"),
        )
        if len(tags) == 0:
            break

        all_tags.extend(tags)
        page += 1
    return all_tags


def prune_repo_by_creation_date(repo, policy_config, namespace, tag_page_limit=100):
    tags = fetch_tags_expiring_by_creation_date_policy(repo.id, policy_config, tag_page_limit)
    prune_tags(tags, repo, namespace)


def execute_policy_on_repo(policy, repo_id, namespace_id, tag_page_limit=100):
    """
    Idenitifies the correct pruning method to execute  for the repository based on the policy method.
    """

    policy_to_func_map = {
        AutoPruneMethod.NUMBER_OF_TAGS.value: prune_repo_by_number_of_tags,
        AutoPruneMethod.CREATION_DATE.value: prune_repo_by_creation_date,
    }

    if policy_to_func_map.get(policy.method, None) is None:
        raise InvalidNamespaceAutoPruneMethod("Unsupported prune method type", policy.method)

    namespace = user.get_namespace_user_by_user_id(namespace_id)
    repo = repository.lookup_repository(repo_id)

    logger.debug("Executing autoprune policy: %s on repo: %s", policy.method, repo.name)

    policy_to_func_map[policy.method](repo, policy.config, namespace, tag_page_limit)


def execute_policies_for_repo(
    ns_policies, repo, namespace_id, tag_page_limit=100, include_repo_policies=True
):
    """
    Executes both repository and namespace level policies for the given repository. The policies
    are applied in a serial fashion and are run asynchronously in the background.

    With multiple policy support, need to keep results consistent when running policies with different methods.
    Eg: On a repo with 5 tags, policy1 has method CREATION_DATE and 2 tags are applicable to be pruned here.
        policy2 has method NUMBER_OF_TAGS, value: 4.
        If policy2 is run first, 1 tag is deleted from policy 1 and 2 tags from policy2.
        If policy1 is run first, 2 tags are deleted from policy 1 and none from policy2.
    """
    policies = ns_policies.copy()
    if include_repo_policies:
        policies.extend(get_repository_autoprune_policies_by_repo_id(repo.id))

    # Prune by age of tags first
    for policy in policies:
        if policy.method == AutoPruneMethod.CREATION_DATE.value:
            execute_policy_on_repo(policy, repo.id, namespace_id, tag_page_limit)

    # Then prune by number of tags
    for policy in policies:
        if policy.method == AutoPruneMethod.NUMBER_OF_TAGS.value:
            execute_policy_on_repo(policy, repo.id, namespace_id, tag_page_limit)


def get_paginated_repositories_for_namespace(namespace_id, page_token=None, page_size=50):
    try:
        query = Repository.select(Repository.name, Repository.id,).where(
            Repository.state == RepositoryState.NORMAL,
            Repository.namespace_user == namespace_id,
        )
        repos, next_page_token = modelutil.paginate(
            query,
            Repository,
            page_token=page_token,
            limit=page_size,
        )
        return repos, next_page_token
    except Exception as err:
        raise Exception(
            f"Error fetching paginated repositories for namespace id: {namespace_id} with error as: {str(err)}"
        )


def get_repository_by_policy_repo_id(policy_repo_id):
    try:
        return (
            Repository.select(Repository.name)
            .where(
                Repository.id == policy_repo_id,
                Repository.state == RepositoryState.NORMAL,
            )
            .get()
        )
    except Repository.DoesNotExist:
        return None


def execute_namespace_policies(
    ns_policies,
    namespace_id,
    repository_page_limit=50,
    tag_page_limit=100,
    include_repo_policies=True,
):
    """
    Executes the given policies for the repositories in the provided namespace.
    """

    if not ns_policies:
        return
    page_token = None

    while True:
        repos, page_token = get_paginated_repositories_for_namespace(
            namespace_id, page_token, repository_page_limit
        )

        for repo in repos:
            execute_policies_for_repo(
                ns_policies, repo, namespace_id, tag_page_limit, include_repo_policies
            )

        if page_token is None:
            break


def fetch_tags_for_repo_policies(policies, repo_id, notification_config):
    all_tags = []
    all_tag_names = set()
    creation_date_tags = []

    # first fetch by CREATION_DATE
    for policy in policies:
        if policy.method != AutoPruneMethod.CREATION_DATE.value:
            continue

        # skip policies that have expiry greater that notification's configuration
        if convert_to_timedelta(policy.config["value"]).days > notification_config["days"]:
            continue

        tags = fetch_tags_expiring_by_creation_date_policy(repo_id, policy.config)
        if len(tags) < 1:
            continue

        for tag in tags:
            if tag.name not in all_tag_names:
                all_tags.append(tag)
                all_tag_names.add(tag.name)
                creation_date_tags.append(tag)

    # then fetch by NUMBER_OF_TAGS
    for policy in policies:
        if policy.method != AutoPruneMethod.NUMBER_OF_TAGS.value:
            continue
        tags = fetch_tags_expiring_by_tag_count_policy(
            repo_id, policy.config, tag_page_limit=100, exclude_tags=creation_date_tags
        )
        if len(tags) < 1:
            continue

        for tag in tags:
            if tag.name not in all_tag_names:
                all_tags.append(tag)
                all_tag_names.add(tag.name)

    return all_tags


def fetch_tags_expiring_due_to_auto_prune_policies(repo_id, namespace_id, notification_config):
    all_policies = []
    all_policies.extend(get_namespace_autoprune_policies_by_id(namespace_id))
    all_policies.extend(get_repository_autoprune_policies_by_repo_id(repo_id))
    return fetch_tags_for_repo_policies(all_policies, repo_id, notification_config)
