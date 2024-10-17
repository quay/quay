import logging.config
import os
import sys
import time

import features
from app import app
from data.database import User
from data.model import modelutil
from data.model.autoprune import (
    AutoPruneMethod,
    NamespaceAutoPrunePolicy,
    assert_valid_namespace_autoprune_policy,
    delete_autoprune_task,
    execute_namespace_policies,
    execute_policy_on_repo,
    fetch_autoprune_task,
    get_namespace_autoprune_policies_by_id,
    get_repository_autoprune_policies_by_namespace_id,
    get_repository_by_policy_repo_id,
    update_autoprune_task,
)
from data.model.user import get_active_namespaces
from util.locking import GlobalLock, LockNotAcquiredException
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)
POLL_PERIOD = app.config.get("AUTO_PRUNING_POLL_PERIOD", 30)
DEFAULT_POLICY_POLL_PERIOD = app.config.get(
    "AUTO_PRUNING_DEFAULT_POLICY_POLL_PERIOD", 60 * 60 * 24
)  # run once a day (24hrs)
BATCH_SIZE = app.config.get("AUTO_PRUNING_BATCH_SIZE", 10)
DEFAULT_POLICY_BATCH_SIZE = app.config.get("AUTO_PRUNING_DEFAULT_POLICY_BATCH_SIZE", 10)
DEFAULT_POLICY_FETCH_NAMESPACES_LIMIT = app.config.get(
    "AUTO_PRUNING_DEFAULT_POLICY_FETCH_NAMESPACES_LIMIT", 50
)
TASK_RUN_MINIMUM_INTERVAL_MS = (
    app.config.get("AUTOPRUNE_TASK_RUN_MINIMUM_INTERVAL_MINUTES", 60) * 60 * 1000
)  # Convert to ms, this should never be under 30min
FETCH_TAGS_PAGE_LIMIT = app.config.get("AUTOPRUNE_FETCH_TAGS_PAGE_LIMIT", 100)
FETCH_REPOSITORIES_PAGE_LIMIT = app.config.get("AUTOPRUNE_FETCH_REPOSITORIES_PAGE_LIMIT", 50)
TIMEOUT = app.config.get("AUTOPRUNE_DEFAULT_POLICY_TIMEOUT", 60 * 60)  # 1hr


def execute_repo_policies_for_method(autoprune_task, repo_policies, policy_method):
    for policy in repo_policies:
        if policy.method != policy_method:
            continue

        repo_id = policy.repository_id
        repo = get_repository_by_policy_repo_id(repo_id)
        logger.info(
            "processing autoprune task %s for repository %s",
            autoprune_task.id,
            repo.name,
        )
        execute_policy_on_repo(policy, repo_id, autoprune_task.namespace, tag_page_limit=100)


class AutoPruneWorker(Worker):
    def __init__(self):
        super(AutoPruneWorker, self).__init__()
        self.add_operation(self.prune, POLL_PERIOD)
        if app.config.get("DEFAULT_NAMESPACE_AUTOPRUNE_POLICY", None) is not None:
            self.add_operation(self.prune_registry, DEFAULT_POLICY_POLL_PERIOD)

    def prune_registry(self, skip_lock_for_testing=False):
        logger.info("processing default org autoprune policy")
        default_namespace_autoprune_policy = app.config["DEFAULT_NAMESPACE_AUTOPRUNE_POLICY"]

        assert_valid_namespace_autoprune_policy(default_namespace_autoprune_policy)

        if skip_lock_for_testing:
            self._prune_registry(default_namespace_autoprune_policy)
        else:
            try:
                with GlobalLock(
                    "REGISTRY_WIDE_AUTOPRUNE",
                    lock_ttl=TIMEOUT,
                ):
                    self._prune_registry(default_namespace_autoprune_policy)
            except LockNotAcquiredException:
                logger.debug("Could not acquire global lock for registry wide auto-pruning")

    def _prune_registry(self, policy):
        page_token = None
        while True:
            namespaces, page_token = modelutil.paginate(
                get_active_namespaces(),
                User,
                page_token=page_token,
                limit=DEFAULT_POLICY_FETCH_NAMESPACES_LIMIT,
            )

            for namespace in namespaces:
                logger.info("executing default autoprune policy on namespace %s", namespace)
                execute_namespace_policies(
                    [NamespaceAutoPrunePolicy(policy_dict=policy)],
                    namespace,
                    FETCH_REPOSITORIES_PAGE_LIMIT,
                    FETCH_TAGS_PAGE_LIMIT,
                    include_repo_policies=False,
                )

            if not page_token:
                break

    def prune(self):
        for _ in range(BATCH_SIZE):
            autoprune_task = fetch_autoprune_task(TASK_RUN_MINIMUM_INTERVAL_MS)
            if not autoprune_task:
                logger.info("no autoprune tasks found, exiting...")
                return

            logger.info(
                "processing autoprune task %s for namespace %s",
                autoprune_task.id,
                autoprune_task.namespace,
            )
            repo_policies = []
            try:
                ns_policies = get_namespace_autoprune_policies_by_id(autoprune_task.namespace)
                if not ns_policies:
                    repo_policies = get_repository_autoprune_policies_by_namespace_id(
                        autoprune_task.namespace
                    )
                    if not repo_policies:
                        logger.info(
                            "deleting autoprune task %s for namespace %s",
                            autoprune_task.id,
                            autoprune_task.namespace,
                        )
                        delete_autoprune_task(autoprune_task)
                        continue

                execute_namespace_policies(
                    ns_policies,
                    autoprune_task.namespace,
                    FETCH_REPOSITORIES_PAGE_LIMIT,
                    FETCH_TAGS_PAGE_LIMIT,
                )

                # case: only repo policies exists & no namespace policy
                # Prune by age of tags first
                execute_repo_policies_for_method(
                    autoprune_task, repo_policies, AutoPruneMethod.CREATION_DATE.value
                )
                # Then prune by number of tags
                execute_repo_policies_for_method(
                    autoprune_task, repo_policies, AutoPruneMethod.NUMBER_OF_TAGS.value
                )

                update_autoprune_task(autoprune_task, task_status="success")
            except Exception as err:
                update_autoprune_task(autoprune_task, task_status=f"failure: {str(err)}")


def create_gunicorn_worker():
    worker = GunicornWorker(__name__, app, AutoPruneWorker(), features.AUTO_PRUNE)
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.AUTO_PRUNE:
        logger.debug("Auto-prune disabled; skipping autopruneworker")
        while True:
            time.sleep(100000)

    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    if app.config.get("DEFAULT_NAMESPACE_AUTOPRUNE_POLICY", None) is not None:
        GlobalLock.configure(app.config)
    worker = AutoPruneWorker()
    worker.start()
