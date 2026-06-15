import logging.config
import time

from peewee import fn

import features
from app import app
from data.database import (
    NamespaceNotification,
    QuotaLimits,
    QuotaNamespaceSize,
    QuotaNotificationState,
    User,
    UserOrganizationQuota,
)
from data.model.namespacequota import maybe_trigger_quota_notification
from data.model.quota_notification_state import clear_notification
from util.locking import GlobalLock
from util.log import logfile_path
from workers.gunicorn_worker import GunicornWorker
from workers.worker import Worker

logger = logging.getLogger(__name__)

POLL_PERIOD = app.config.get("QUOTA_NOTIFICATION_WORKER_POLL_PERIOD", 300)


class QuotaNotificationWorker(Worker):
    def __init__(self):
        super(QuotaNotificationWorker, self).__init__()
        self.add_operation(self._check_quotas, POLL_PERIOD)

    def _check_quotas(self):
        if not features.QUOTA_NOTIFICATIONS:
            return

        namespace_ids = (
            NamespaceNotification.select(NamespaceNotification.namespace)
            .distinct()
            .tuples()
        )
        namespace_id_set = {row[0] for row in namespace_ids}

        if not namespace_id_set:
            return

        for namespace_user in User.select().where(User.id << list(namespace_id_set)):
            try:
                self._check_namespace(namespace_user)
            except Exception:
                logger.exception(
                    "Error checking quota notifications for namespace %s",
                    namespace_user.username,
                )

    def _check_namespace(self, namespace_user):
        quota = (
            UserOrganizationQuota.select()
            .where(UserOrganizationQuota.namespace == namespace_user)
            .first()
        )
        if quota is None:
            return

        try:
            size_row = QuotaNamespaceSize.get(
                QuotaNamespaceSize.namespace_user == namespace_user
            )
            usage_bytes = size_row.size_bytes if size_row.size_bytes is not None else 0
        except QuotaNamespaceSize.DoesNotExist:
            usage_bytes = 0

        limits = list(
            QuotaLimits.select()
            .where(QuotaLimits.quota == quota)
        )
        if not limits:
            return

        quota_limit_bytes = quota.limit_bytes

        for limit in limits:
            threshold_percent = limit.percent_of_limit
            bytes_allowed = int(quota_limit_bytes * threshold_percent / 100)

            if usage_bytes > bytes_allowed:
                quota_result = {
                    "severity_level": limit.quota_type.name,
                    "threshold_percent": threshold_percent,
                    "usage_bytes": usage_bytes,
                    "quota_limit_bytes": quota_limit_bytes,
                    "limit_bytes": bytes_allowed,
                }
                maybe_trigger_quota_notification(namespace_user.username, quota_result)
            else:
                state = QuotaNotificationState.get_or_none(
                    QuotaNotificationState.namespace == namespace_user,
                    QuotaNotificationState.threshold_percent == threshold_percent,
                )
                if state is not None and not state.cleared:
                    clear_notification(namespace_user, threshold_percent)
                    logger.info(
                        "Cleared quota notification state for namespace %s at %d%% threshold",
                        namespace_user.username,
                        threshold_percent,
                    )


def create_gunicorn_worker():
    worker = GunicornWorker(
        __name__, app, QuotaNotificationWorker(), features.QUOTA_NOTIFICATIONS
    )
    return worker


if __name__ == "__main__":
    if app.config.get("ACCOUNT_RECOVERY_MODE", False):
        logger.debug("Quay running in account recovery mode")
        while True:
            time.sleep(100000)

    if not features.QUOTA_NOTIFICATIONS:
        logger.debug("Quota notifications disabled; skipping quotanotificationworker")
        while True:
            time.sleep(100000)

    GlobalLock.configure(app.config)
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)
    worker = QuotaNotificationWorker()
    worker.start()
