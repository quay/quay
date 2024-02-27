import json
import logging.config
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
    def __init__(self, db_row):
        config = json.loads(db_row.policy)
        self._db_row = db_row
        self.uuid = db_row.uuid
        self.method = config.get("method")
        self.config = config

    def get_row(self):
        return self._db_row

    def get_view(self):
        return {"uuid": self.uuid, "method": self.method, "value": self.config.get("value")}


class RepositoryAutoPrunePolicy:
    def __init__(self, db_row):
        config = json.loads(db_row.policy)
        self._db_row = db_row
        self.uuid = db_row.uuid
        self.method = config.get("method")
        self.config = config
        self.repository_id = db_row.repository_id

    def get_row(self):
        return self._db_row

    def get_view(self):
        return {"uuid": self.uuid, "method": self.method, "value": self.config.get("value")}


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

        if namespace_has_autoprune_policy(namespace_id):
            raise NamespaceAutoPrunePolicyAlreadyExists(
                "Policy for this namespace already exists, delete existing to create new policy"
            )

        assert_valid_namespace_autoprune_policy(policy_config)

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

        if repository_has_autoprune_policy(repo.id):
            raise RepositoryAutoPrunePolicyAlreadyExists(
                "Policy for this repository already exists, delete existing to create new policy"
            )

        assert_valid_repository_autoprune_policy(policy_config)

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


def prune_repo_by_number_of_tags(repo, policy_config, namespace, tag_page_limit):
    """
    Prunes tags in the given repository based on the number of tags specified in the policy config.
    """

    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.NUMBER_OF_TAGS.value:
        raise InvalidNamespaceAutoPruneMethod(
            f"Expected prune method type {AutoPruneMethod.NUMBER_OF_TAGS.value} but got {policy_method}"
        )

    assert_valid_namespace_autoprune_policy(policy_config)

    while True:
        tags = oci.tag.fetch_paginated_autoprune_repo_tags_by_number(
            repo.id, int(policy_config["value"]), tag_page_limit
        )
        if len(tags) == 0:
            break

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


def prune_repo_by_creation_date(repo, policy_config, namespace, tag_page_limit=100):
    """
    Prunes tags in the given repository based on the creation date specified in the policy config,
    where the value is a valid timedelta string. (e.g. 1d, 1w, 1m, 1y)
    """

    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.CREATION_DATE.value:
        raise InvalidNamespaceAutoPruneMethod(
            f"Expected prune method type {AutoPruneMethod.CREATION_DATE.value} but got {policy_method}"
        )

    assert_valid_namespace_autoprune_policy(policy_config)

    time_ms = int(convert_to_timedelta(policy_config["value"]).total_seconds() * 1000)
    while True:
        tags = oci.tag.fetch_paginated_autoprune_repo_tags_older_than_ms(
            repo.id, time_ms, tag_page_limit
        )

        if len(tags) == 0:
            break

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


def execute_policies_for_repo(ns_policies, repo, namespace_id, tag_page_limit=100):
    """
    Executes both repository and namespace level policies for the given repository. The policies
    are applied in a serial fashion and are run asynchronosly in the background.
    """
    for ns_policy in ns_policies:
        repo_policies = get_repository_autoprune_policies_by_repo_id(repo.id)
        # note: currently only one policy is configured per repo
        for repo_policy in repo_policies:
            execute_policy_on_repo(repo_policy, repo.id, namespace_id, tag_page_limit)
        # execute associated namespace policy
        execute_policy_on_repo(ns_policy, repo.id, namespace_id, tag_page_limit)


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


def execute_namespace_polices(
    ns_policies, namespace_id, repository_page_limit=50, tag_page_limit=100
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
            execute_policies_for_repo(ns_policies, repo, namespace_id, tag_page_limit)

        if page_token is None:
            break
