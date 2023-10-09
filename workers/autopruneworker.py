import logging.config
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


class AutoPruneWorker(Worker):
    def __init__(self):
        super(AutoPruneWorker, self).__init__()
        self.add_operation(self.prune, POLL_PERIOD)

    def prune(self):
        for i in range(BATCH_SIZE):
            try:
                autoprune_task = fetch_autoprune_task()
                if not autoprune_task:
                    return
            except Exception as err:
                logger.warning("Exception while fetching autoprune task: %s" % str(err))

                # Return immediately to see if the next poll will succeed
                return

            try:
                policies = get_namespace_autoprune_policies_by_id(autoprune_task.namespace)
                if not policies:
                    # When implementing repo policies, fetch repo policies before deleting the task
                    delete_autoprune_task(autoprune_task)
                    continue

                execute_namespace_polices(policies, autoprune_task.namespace)

                update_autoprune_task(autoprune_task, task_status="success")
            except Exception as err:
                update_autoprune_task(autoprune_task, task_status=str(err))


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
