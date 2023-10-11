import json
import logging.config
from enum import Enum

from data.database import AutoPruneTaskStatus, DeletedNamespace
from data.database import NamespaceAutoPrunePolicy as NamespaceAutoPrunePolicyTable
from data.database import (
    Repository,
    RepositoryState,
    User,
    db_for_update,
    get_epoch_timestamp_ms,
)
from data.model import (
    InvalidNamespaceAutoPrunePolicy,
    InvalidNamespaceException,
    NamespaceAutoPrunePolicyAlreadyExists,
    NamespaceAutoPrunePolicyDoesNotExist,
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
PAGINATE_SIZE = 50


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


def get_namespace_autoprune_policies_by_id(namespace_id):
    """
    Get the autopruning policies for the namespace by id.
    """
    query = NamespaceAutoPrunePolicyTable.select().where(
        NamespaceAutoPrunePolicyTable.namespace == namespace_id,
    )
    return [NamespaceAutoPrunePolicy(row) for row in query]


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


def delete_namespace_autoprune_policy(orgname, uuid):
    """
    Deletes the policy specified by the uuid
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


def namespace_has_autoprune_policy(namespace_id):
    return (
        NamespaceAutoPrunePolicyTable.select(1)
        .where(NamespaceAutoPrunePolicyTable.namespace == namespace_id)
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
        task.last_ran_ms = get_epoch_timestamp_ms()
        task.save()
    except AutoPruneTaskStatus.DoesNotExist:
        return None
    except Exception as err:
        raise Exception(
            f"Error updating autoprune task for namespace id: {task.namespace_id}, task_status: {task_status} with error as: {str(err)}"
        )


def fetch_autoprune_task():
    """
    Get the auto prune task prioritized by last_ran_ms = None followed by asc order of last_ran_ms
    """
    with db_transaction():
        try:
            query = (
                AutoPruneTaskStatus.select()
                .where(
                    AutoPruneTaskStatus.namespace.not_in(
                        DeletedNamespace.select(DeletedNamespace.namespace)
                    )
                )
                .order_by(
                    AutoPruneTaskStatus.last_ran_ms.asc(nulls="first"), AutoPruneTaskStatus.id
                )
            )
            return db_for_update(query, skip_locked=True).get()
        except AutoPruneTaskStatus.DoesNotExist:
            return []


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


def prune_repo_by_number_of_tags(repo, policy_config, namespace):
    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.NUMBER_OF_TAGS.value or not valid_value(
        AutoPruneMethod(policy_method), policy_config.get("value")
    ):
        raise KeyError("Unsupported policy config provided", policy_config)

    page_token = None
    while True:
        tags, page_token = oci.tag.fetch_paginated_autoprune_repo_tags_by_number(
            repo.id, int(policy_config["value"]), page_token, PAGINATE_SIZE
        )
        tags_list = [row for row in tags]

        for tag in tags_list:
            try:
                oci.tag.delete_tag(repo.id, tag.name)
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

        if page_token is None:
            break


def prune_repo_by_creation_date(repo, policy_config, namespace):
    policy_method = policy_config.get("method", None)

    if policy_method != AutoPruneMethod.CREATION_DATE.value or not valid_value(
        AutoPruneMethod(policy_method), policy_config.get("value")
    ):
        raise KeyError("Unsupported policy config provided", policy_config)

    time_ms = int(convert_to_timedelta(policy_config["value"]).total_seconds() * 1000)

    page_token = None
    while True:
        tags, page_token = oci.tag.fetch_paginated_autoprune_repo_tags_older_than_ms(
            repo.id, time_ms, page_token, PAGINATE_SIZE
        )
        tags_list = [row for row in tags]

        for tag in tags_list:
            try:
                oci.tag.delete_tag(repo.id, tag.name)
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

        if page_token is None:
            break


def execute_poilcy_on_repo(policy, repo_id, namespace_id):
    policy_to_func_map = {
        AutoPruneMethod.NUMBER_OF_TAGS.value: prune_repo_by_number_of_tags,
        AutoPruneMethod.CREATION_DATE.value: prune_repo_by_creation_date,
    }

    if policy_to_func_map.get(policy.method, None) is None:
        raise KeyError("Unsupported policy provided", policy.method)

    namespace = user.get_namespace_user_by_user_id(namespace_id)
    repo = repository.lookup_repository(repo_id)

    policy_to_func_map[policy.method](repo, policy.config, namespace)


def execute_policies_for_repo(policies, repo, namespace_id):
    list(map(lambda policy: execute_poilcy_on_repo(policy, repo, namespace_id), policies))


def get_paginated_repositories_for_namespace(namespace_id, page_token=None):
    try:
        query = Repository.select(
            Repository.name,
            Repository.id,
            Repository.visibility,
            Repository.kind,
            Repository.state,
        ).where(
            Repository.state != RepositoryState.MARKED_FOR_DELETION,
            Repository.namespace_user == namespace_id,
        )
        repos, next_page_token = modelutil.paginate(
            query,
            Repository,
            page_token=page_token,
            limit=PAGINATE_SIZE,
        )
        return repos, next_page_token
    except Exception as err:
        raise Exception(
            f"Error fetching paginated repositories for namespace id: {namespace_id} with error as: {str(err)}"
        )


def execute_namespace_polices(policies, namespace_id):
    if not policies:
        return
    page_token = None

    while True:
        repos, page_token = get_paginated_repositories_for_namespace(namespace_id, page_token)
        repo_list = [row for row in repos]

        # When implementing repo policies, fetch repo policies and add it to the policies list here
        list(map(lambda repo: execute_policies_for_repo(policies, repo, namespace_id), repo_list))

        if page_token is None:
            break
