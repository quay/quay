import logging.config
import os
import sys
import time

import features
from app import app
from data.model.autoprune import *
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)
POLL_PERIOD = app.config.get("AUTO_PRUNING_POLL_PERIOD", 30)
BATCH_SIZE = app.config.get("AUTO_PRUNING_BATCH_SIZE", 10)
TASK_RUN_MINIMUM_INTERVAL_MS = (
    app.config.get("AUTOPRUNE_TASK_RUN_MINIMUM_INTERVAL_MINUTES", 60) * 60 * 1000
)  # Convert to ms, this should never be under 30min
FETCH_TAGS_PAGE_LIMIT = app.config.get("AUTOPRUNE_FETCH_TAGS_PAGE_LIMIT", 100)
FETCH_REPOSITORIES_PAGE_LIMIT = app.config.get("AUTOPRUNE_FETCH_REPOSITORIES_PAGE_LIMIT", 50)


class AutoPruneWorker(Worker):
    def __init__(self):
        super(AutoPruneWorker, self).__init__()
        self.add_operation(self.prune, POLL_PERIOD)

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
                        logger.info("deleting autoprune task %s for namespace %s", autoprune_task.id, autoprune_task.namespace)
                        delete_autoprune_task(autoprune_task)
                        continue

                execute_namespace_polices(
                    ns_policies,
                    autoprune_task.namespace,
                    FETCH_REPOSITORIES_PAGE_LIMIT,
                    FETCH_TAGS_PAGE_LIMIT,
                )

                # case: only repo policies exists & no namespace policy
                for policy in repo_policies:
                    repo_id = policy.repository_id
                    repo = get_repository_by_policy_repo_id(repo_id)
                    logger.info(
                        "processing autoprune task %s for repository %s",
                        autoprune_task.id,
                        repo.name,
                    )
                    execute_policy_on_repo(
                        policy, repo_id, autoprune_task.namespace, tag_page_limit=100
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
    worker = AutoPruneWorker()
    worker.start()
