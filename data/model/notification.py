import json

from peewee import SQL

from data.database import (
    Notification,
    NotificationKind,
    User,
    Team,
    TeamMember,
    TeamRole,
    RepositoryNotification,
    ExternalNotificationEvent,
    Repository,
    ExternalNotificationMethod,
    Namespace,
    db_for_update,
)
from data.model import InvalidNotificationException, db_transaction


def create_notification(kind_name, target, metadata={}, lookup_path=None):
    kind_ref = NotificationKind.get(name=kind_name)
    notification = Notification.create(
        kind=kind_ref, target=target, metadata_json=json.dumps(metadata), lookup_path=lookup_path
    )
    return notification


def create_unique_notification(kind_name, target, metadata={}):
    with db_transaction():
        if list_notifications(target, kind_name).count() == 0:
            create_notification(kind_name, target, metadata)


def lookup_notification(user, uuid):
    results = list(list_notifications(user, id_filter=uuid, include_dismissed=True, limit=1))
    if not results:
        return None

    return results[0]


def lookup_notifications_by_path_prefix(prefix):
    return list((Notification.select().where(Notification.lookup_path % prefix)))


def list_notifications(
    user, kind_name=None, id_filter=None, include_dismissed=False, page=None, limit=None
):

    base_query = Notification.select(
        Notification.id,
        Notification.uuid,
        Notification.kind,
        Notification.metadata_json,
        Notification.dismissed,
        Notification.lookup_path,
        Notification.created,
        Notification.created.alias("cd"),
        Notification.target,
    ).join(NotificationKind)

    if kind_name is not None:
        base_query = base_query.where(NotificationKind.name == kind_name)

    if id_filter is not None:
        base_query = base_query.where(Notification.uuid == id_filter)

    if not include_dismissed:
        base_query = base_query.where(Notification.dismissed == False)

    # Lookup directly for the user.
    user_direct = base_query.clone().where(Notification.target == user)

    # Lookup via organizations admined by the user.
    Org = User.alias()
    AdminTeam = Team.alias()
    AdminTeamMember = TeamMember.alias()
    AdminUser = User.alias()

    via_orgs = (
        base_query.clone()
        .join(Org, on=(Org.id == Notification.target))
        .join(AdminTeam, on=(Org.id == AdminTeam.organization))
        .join(TeamRole, on=(AdminTeam.role == TeamRole.id))
        .switch(AdminTeam)
        .join(AdminTeamMember, on=(AdminTeam.id == AdminTeamMember.team))
        .join(AdminUser, on=(AdminTeamMember.user == AdminUser.id))
        .where((AdminUser.id == user) & (TeamRole.name == "admin"))
    )

    query = user_direct | via_orgs

    if page:
        query = query.paginate(page, limit)
    elif limit:
        query = query.limit(limit)

    return query.order_by(SQL("cd desc"))


def delete_all_notifications_by_path_prefix(prefix):
    (Notification.delete().where(Notification.lookup_path ** (prefix + "%")).execute())


def delete_all_notifications_by_kind(kind_name):
    kind_ref = NotificationKind.get(name=kind_name)
    (Notification.delete().where(Notification.kind == kind_ref).execute())


def delete_notifications_by_kind(target, kind_name):
    kind_ref = NotificationKind.get(name=kind_name)
    Notification.delete().where(
        Notification.target == target, Notification.kind == kind_ref
    ).execute()


def delete_matching_notifications(target, kind_name, **kwargs):
    kind_ref = NotificationKind.get(name=kind_name)

    # Load all notifications for the user with the given kind.
    notifications = Notification.select().where(
        Notification.target == target, Notification.kind == kind_ref
    )

    # For each, match the metadata to the specified values.
    for notification in notifications:
        matches = True
        try:
            metadata = json.loads(notification.metadata_json)
        except:
            continue

        for (key, value) in kwargs.items():
            if not key in metadata or metadata[key] != value:
                matches = False
                break

        if not matches:
            continue

        notification.delete_instance()


def increment_notification_failure_count(uuid):
    """
    This increments the number of failures by one.
    """
    (
        RepositoryNotification.update(
            number_of_failures=RepositoryNotification.number_of_failures + 1
        )
        .where(RepositoryNotification.uuid == uuid)
        .execute()
    )


def reset_notification_number_of_failures(namespace_name, repository_name, uuid):
    """
    This resets the number of failures for a repo notification to 0.
    """
    try:
        notification = (
            RepositoryNotification.select().where(RepositoryNotification.uuid == uuid).get()
        )
        if (
            notification.repository.namespace_user.username != namespace_name
            or notification.repository.name != repository_name
        ):
            raise InvalidNotificationException(
                "No repository notification found with uuid: %s" % uuid
            )
        reset_number_of_failures_to_zero(notification.id)
        return notification
    except RepositoryNotification.DoesNotExist:
        return None


def reset_number_of_failures_to_zero(notification_id):
    """
    This resets the number of failures for a repo notification to 0.
    """
    RepositoryNotification.update(number_of_failures=0).where(
        RepositoryNotification.id == notification_id
    ).execute()


def create_repo_notification(
    repo, event_name, method_name, method_config, event_config, title=None
):
    event = ExternalNotificationEvent.get(ExternalNotificationEvent.name == event_name)
    method = ExternalNotificationMethod.get(ExternalNotificationMethod.name == method_name)

    return RepositoryNotification.create(
        repository=repo,
        event=event,
        method=method,
        config_json=json.dumps(method_config),
        title=title,
        event_config_json=json.dumps(event_config),
    )


def _base_get_notification(uuid):
    """
    This is a base query for get statements.
    """
    return (
        RepositoryNotification.select(RepositoryNotification, Repository, Namespace)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(RepositoryNotification.uuid == uuid)
    )


def get_enabled_notification(uuid):
    """
    This returns a notification with less than 3 failures.
    """
    try:
        return (
            _base_get_notification(uuid).where(RepositoryNotification.number_of_failures < 3).get()
        )
    except RepositoryNotification.DoesNotExist:
        raise InvalidNotificationException("No repository notification found with uuid: %s" % uuid)


def get_repo_notification(uuid):
    try:
        return _base_get_notification(uuid).get()
    except RepositoryNotification.DoesNotExist:
        raise InvalidNotificationException("No repository notification found with uuid: %s" % uuid)


def delete_repo_notification(namespace_name, repository_name, uuid):
    found = get_repo_notification(uuid)
    if (
        found.repository.namespace_user.username != namespace_name
        or found.repository.name != repository_name
    ):
        raise InvalidNotificationException("No repository notifiation found with uuid: %s" % uuid)
    found.delete_instance()
    return found


def list_repo_notifications(namespace_name, repository_name, event_name=None):
    query = (
        RepositoryNotification.select(RepositoryNotification, Repository, Namespace)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
    )

    if event_name:
        query = (
            query.switch(RepositoryNotification)
            .join(ExternalNotificationEvent)
            .where(ExternalNotificationEvent.name == event_name)
        )

    return query
