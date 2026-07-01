import logging
from datetime import datetime, timedelta

from data.database import QuotaNotificationState
from data.model import config, db_transaction

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 86400


def _get_cooldown_seconds():
    if config.app_config is None:
        return DEFAULT_COOLDOWN_SECONDS
    return config.app_config.get("QUOTA_NOTIFICATION_COOLDOWN_SECONDS", DEFAULT_COOLDOWN_SECONDS)


def should_notify(namespace_user, threshold_percent):
    """
    Returns True if a notification should be sent for this namespace + threshold_percent.
    A notification is eligible if no state row exists, or the cooldown has expired.
    """
    state = QuotaNotificationState.get_or_none(
        QuotaNotificationState.namespace == namespace_user,
        QuotaNotificationState.threshold_percent == threshold_percent,
    )

    if state is None:
        return True

    if state.last_notified_at is None:
        return True

    cooldown = timedelta(seconds=_get_cooldown_seconds())
    return datetime.utcnow() >= state.last_notified_at + cooldown


def record_notification(namespace_user, threshold_percent):
    """
    Creates or updates the state row: sets cleared=False, last_notified_at=now.
    """
    now = datetime.utcnow()

    with db_transaction():
        state = QuotaNotificationState.get_or_none(
            QuotaNotificationState.namespace == namespace_user,
            QuotaNotificationState.threshold_percent == threshold_percent,
        )

        if state is None:
            QuotaNotificationState.create(
                namespace=namespace_user,
                threshold_percent=threshold_percent,
                last_notified_at=now,
                cleared=False,
            )
        else:
            state.last_notified_at = now
            state.cleared = False
            state.save()


def clear_notification(namespace_user, threshold_percent):
    """
    Sets cleared=True for the matching row. No-op if no row exists.
    """
    QuotaNotificationState.update(cleared=True).where(
        QuotaNotificationState.namespace == namespace_user,
        QuotaNotificationState.threshold_percent == threshold_percent,
    ).execute()


def clear_all_for_namespace(namespace_user):
    """
    Deletes all QuotaNotificationState rows for the given namespace.
    """
    QuotaNotificationState.delete().where(
        QuotaNotificationState.namespace == namespace_user,
    ).execute()
