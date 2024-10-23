import json
import logging

from app import app
from data.database import (
    ExternalNotificationEvent,
    RepositoryNotification,
    TagNotificationSuccess,
    db_for_update,
    get_epoch_timestamp_ms,
)
from data.model import db_transaction, oci
from data.model.autoprune import fetch_tags_expiring_due_to_auto_prune_policies
from data.model.user import get_namespace_by_user_id
from data.registry_model import registry_model
from notifications import spawn_notification

logger = logging.getLogger(__name__)
BATCH_SIZE = 10

# Define a constant for the SKIP_LOCKED flag for testing purposes,
# since we test with mysql 5.7 which does not support this flag.
SKIP_LOCKED = True

# interval in minutes that specifies how long a task must wait before being run again, defaults to 5hrs
NOTIFICATION_TASK_RUN_MINIMUM_INTERVAL_MINUTES = app.config.get(
    "NOTIFICATION_TASK_RUN_MINIMUM_INTERVAL_MINUTES", 5 * 60
)


def fetch_active_notification(event):
    with db_transaction():
        try:
            # Fetch active notifications that match the event_name
            query = (
                RepositoryNotification.select(
                    RepositoryNotification.id,
                    RepositoryNotification.uuid,
                    RepositoryNotification.method,
                    RepositoryNotification.repository,
                    RepositoryNotification.event_config_json,
                )
                .where(
                    RepositoryNotification.event == event.id,
                    RepositoryNotification.number_of_failures < 3,
                    (
                        RepositoryNotification.last_ran_ms
                        < get_epoch_timestamp_ms()
                        - (NOTIFICATION_TASK_RUN_MINIMUM_INTERVAL_MINUTES * 60 * 1000)
                    )
                    | (RepositoryNotification.last_ran_ms.is_null(True)),
                )
                .order_by(RepositoryNotification.last_ran_ms.asc(nulls="first"))
            )
            notification = db_for_update(query, skip_locked=SKIP_LOCKED).get()

            RepositoryNotification.update(last_ran_ms=get_epoch_timestamp_ms()).where(
                RepositoryNotification.id == notification.id
            ).execute()
            return notification

        except RepositoryNotification.DoesNotExist:
            return None


def track_tags_to_notify(tags, notification):
    for tag in tags:
        TagNotificationSuccess.create(
            notification=notification.id, tag=tag.id, method=notification.method
        )


def fetch_notified_tag_ids_for_event(notification):
    response = (
        TagNotificationSuccess.select(TagNotificationSuccess.tag)
        .where(
            TagNotificationSuccess.notification == notification.id,
            TagNotificationSuccess.method == notification.method,
        )
        .distinct()
    )
    return [r.tag.id for r in response]


def scan_for_image_expiry_notifications(event_name, batch_size=BATCH_SIZE):
    """
    Get the repository notification prioritized by last_ran_ms = None followed by asc order of last_ran_ms.
    """
    event = ExternalNotificationEvent.get(ExternalNotificationEvent.name == event_name)
    for _ in range(batch_size):
        notification = fetch_active_notification(event)
        if not notification:
            return

        repository = notification.repository
        repo_id = repository.id
        config = json.loads(notification.event_config_json)

        if not config.get("days", None):
            logger.error(
                f"Missing key days in config for notification_id:{notification.id} created for repository_id:{repo_id}"
            )
            continue

        # Fetch tags that were already notified
        notified_tags = fetch_notified_tag_ids_for_event(notification)

        # Fetch tags matching notification's config
        tags = oci.tag.fetch_repo_tags_for_image_expiry_expiry_event(
            repo_id, config["days"], notified_tags
        )
        autoprune_tags = fetch_tags_expiring_due_to_auto_prune_policies(
            repo_id, repository.namespace_user, config
        )

        if len(autoprune_tags):
            tags.extend(autoprune_tags)

        if not len(tags):
            continue

        track_tags_to_notify(tags, notification)

        namespace_name = get_namespace_by_user_id(repository.namespace_user)
        repository_ref = registry_model.lookup_repository(namespace_name, repository.name)

        # Push tags into queue notification worker queue
        spawn_notification(
            repository_ref,
            event_name,
            {
                "notification_uuid": notification.uuid,
                "tags": [tag.name for tag in tags],
                "expiring_in": f"{config['days']} days",
            },
        )

    return
