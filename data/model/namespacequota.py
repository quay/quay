import json

from peewee import fn, JOIN

from data.database import (
    Repository,
    QuotaLimits,
    UserOrganizationQuota,
    QuotaType,
    Manifest,
    get_epoch_timestamp_ms,
    Tag,
    RepositorySize,
    User,
)
from data import model
from data.model import (
    organization,
    user,
    InvalidUsernameException,
    notification,
    config,
    InvalidSystemQuotaConfig,
)


def verify_namespace_quota(repository_ref):
    model.repository.get_repository_size_and_cache(repository_ref._db_id)
    namespace_size = get_namespace_size(repository_ref.namespace_name)
    return check_limits(repository_ref.namespace_name, namespace_size)


def verify_namespace_quota_force_cache(repository_ref):
    force_cache_repo_size(repository_ref)
    namespace_size = get_namespace_size(repository_ref.namespace_name)
    return check_limits(repository_ref.namespace_name, namespace_size)


def verify_namespace_quota_during_upload(repository_ref):
    size = model.repository.get_size_during_upload(repository_ref._db_id)
    namespace_size = get_namespace_size(repository_ref.namespace_name)
    if namespace_size is None:
        namespace_size = 0

    return check_limits(repository_ref.namespace_name, size + namespace_size)


def check_limits(namespace_name, size):
    limits = get_namespace_limits(namespace_name)
    limit_bytes = 0
    severity_level = None
    for limit in limits:
        if size > limit["bytes_allowed"]:
            if limit_bytes < limit["bytes_allowed"]:
                limit_bytes = limit["bytes_allowed"]
                severity_level = limit["name"]

    return {"limit_bytes": limit_bytes, "severity_level": severity_level}


def notify_organization_admins(repository_ref, notification_kind, metadata={}):
    namespace = model.user.get_namespace_user(repository_ref.namespace_name)
    if namespace is None:
        raise InvalidUsernameException("Namespace does not exist")

    if namespace.organization:
        admins = organization.get_admin_users(namespace)

        for admin in admins:
            notification.create_notification(
                notification_kind, admin, {"namespace": repository_ref.namespace_name}
            )
    else:
        notification.create_notification(
            notification_kind,
            repository_ref.namespace_name,
            {"namespace": repository_ref.namespace_name},
        )


def force_cache_repo_size(repository_ref):
    return model.repository.force_cache_repo_size(repository_ref._db_id)


def create_namespace_quota(name, limit_bytes, superuser=False):
    user_object = user.get_namespace_user(name)
    try:
        return UserOrganizationQuota.create(namespace_id=user_object.id, limit_bytes=limit_bytes, set_by_super=superuser)
    except model.DataModelException as ex:
        return None


def create_namespace_limit(orgname, quota_type_id, percent_of_limit):
    quota = get_namespace_quota(orgname)

    if quota is None:
        raise InvalidUsernameException("Quota Does Not Exist for : " + orgname)

    new_limit = QuotaLimits.create(
        quota_id=quota.id,
        percent_of_limit=percent_of_limit,
        quota_type_id=quota_type_id,
    )

    return new_limit


def get_namespace_quota(name):
    try:
        space = user.get_namespace_user(name)
        if space is None:
            raise InvalidUsernameException("This Namespace does not exist : " + name)

        quota = UserOrganizationQuota.select().where(UserOrganizationQuota.namespace_id == space.id)
        # TODO: I dont like this so we will need to find a better way to test if the query is empty.
        return quota.get()
    except UserOrganizationQuota.DoesNotExist:
        return None


def check_system_quota_bytes_enabled():

    if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") < 0:
        raise InvalidSystemQuotaConfig(
            "Invalid Configuration: Quota bytes must be greater than or equal to 0"
        )

    if config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
        return True
    else:
        return False


def get_namespace_limits(name):
    query = (
        UserOrganizationQuota.select(
            UserOrganizationQuota.limit_bytes,
            QuotaLimits.percent_of_limit,
            QuotaLimits.quota_id,
            QuotaLimits.id,
            QuotaType.name,
            QuotaType.id,
            (
                UserOrganizationQuota.limit_bytes.cast("decimal")
                * (QuotaLimits.percent_of_limit.cast("decimal") / 100.0).cast("decimal")
            ).alias("bytes_allowed"),
            QuotaType.id.alias("type_id"),
        )
        .join(User, on=(UserOrganizationQuota.namespace_id == User.id))
        .join(QuotaLimits, on=(UserOrganizationQuota.id == QuotaLimits.quota_id))
        .join(QuotaType, on=(QuotaLimits.quota_type_id == QuotaType.id))
        .where(User.username == name)
    ).dicts()

    # define limits if a system default is defined in config.py and no namespace specific limits are set
    if check_system_quota_bytes_enabled() and len(query) == 0:
        query = [
            {
                "limit_bytes": config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES"),
                "percent_of_limit": 80,
                "name": "System Warning Limit",
                "bytes_allowed": config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") * 0.8,
                "type_id": 1,
            },
            {
                "limit_bytes": config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES"),
                "percent_of_limit": 100,
                "name": "System Reject Limit",
                "bytes_allowed": config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES"),
                "type_id": 2,
            },
        ]

    return query


def get_namespace_limit(name, quota_type_id, percent_of_limit):
    try:
        quota = get_namespace_quota(name)

        if quota is None:
            raise InvalidUsernameException("Quota for this namespace does not exist")

        query = (
            QuotaLimits.select()
            .join(QuotaType)
            .where(QuotaLimits.quota_id == quota.id)
            .where(QuotaLimits.quota_type_id == quota_type_id)
            .where(QuotaLimits.percent_of_limit == percent_of_limit)
        )

        return query.get()

    except QuotaLimits.DoesNotExist:
        return None


def get_namespace_limit_from_id(name, quota_limit_id):
    try:
        quota = get_namespace_quota(name)

        if quota is None:
            raise InvalidUsernameException("Quota for this namespace does not exist")

        query = (
            QuotaLimits.select()
            .join(QuotaType)
            .where(QuotaLimits.quota_id == quota.id)
            .where(QuotaLimits.id == quota_limit_id)
        )

        return query.get()

    except QuotaLimits.DoesNotExist:
        return None


def get_namespace_reject_limit(name):
    try:
        quota = get_namespace_quota(name)

        if quota is None:
            raise InvalidUsernameException("Quota for this namespace does not exist")

        # QuotaType
        query = (
            QuotaLimits.select()
            .join(QuotaType)
            .where(QuotaType.name == "Reject")
            .where(QuotaLimits.quota_id == quota.id)
        )

        return query.get()

    except QuotaLimits.DoesNotExist:
        return None


def get_namespace_limit_types():
    return [{"quota_type_id": qtype.id, "name": qtype.name} for qtype in QuotaType.select()]


def fetch_limit_id_from_name(name):
    for i in get_namespace_limit_types():
        if name == i["name"]:
            return i["quota_type_id"]
    return None


def is_reject_limit_type(quota_type_id):
    if quota_type_id == fetch_limit_id_from_name("Reject"):
        return True
    return False


def get_namespace_limit_types_for_id(quota_limit_type_id):
    return QuotaType.select().where(QuotaType.id == quota_limit_type_id).get()


def get_namespace_limit_types_for_name(name):
    return QuotaType.select().where(QuotaType.name == name).get()


def change_namespace_quota(name, limit_bytes, superuser=False):
    org = user.get_namespace_user(name)
    quota = UserOrganizationQuota.select().where(UserOrganizationQuota.namespace_id == org.id).get()

    quota.limit_bytes = limit_bytes
    quota.set_by_super = superuser
    quota.save()

    return quota


def change_namespace_quota_limit(name, percent_of_limit, quota_type_id, quota_limit_id):
    quota_limit = get_namespace_limit_from_id(name, quota_limit_id)

    quota_limit.percent_of_limit = percent_of_limit
    quota_limit.quota_type_id = quota_type_id
    quota_limit.save()

    return quota_limit


def delete_namespace_quota_limit(name, quota_limit_id):
    quota_limit = get_namespace_limit_from_id(name, quota_limit_id)

    if quota_limit is not None:
        quota_limit.delete_instance()
        return 1

    return 0


def delete_all_namespace_quota_limits(quota):
    return QuotaLimits.delete().where(QuotaLimits.quota_id == quota.id).execute()


def delete_namespace_quota(name):
    org = user.get_namespace_user(name)

    try:
        quota = (
            UserOrganizationQuota.select().where(UserOrganizationQuota.namespace_id == org.id)
        ).get()
    except UserOrganizationQuota.DoesNotExist:
        return 0

    if quota is not None:
        delete_all_namespace_quota_limits(quota)
        UserOrganizationQuota.delete().where(UserOrganizationQuota.namespace_id == org.id).execute()
        return 1

    return 0


def get_namespace_repository_sizes_and_cache(namespace_name):
    return cache_namespace_repository_sizes(namespace_name)


def cache_namespace_repository_sizes(namespace_name):
    namespace = user.get_user_or_org(namespace_name)
    now_ms = get_epoch_timestamp_ms()

    subquery = (
        Tag.select(Tag.repository_id)
        .where(Tag.hidden == False)
        .where((Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms > now_ms))
        .group_by(Tag.repository_id)
        .having(fn.Count(Tag.name) > 0)
    )

    namespace_repo_sizes = (
        Manifest.select(
            (Repository.id).alias("repository_id"),
            (Repository.name).alias("repository_name"),
            fn.sum(Manifest.layers_compressed_size).alias("repository_size"),
        )
        .join(Repository)
        .join(subquery, on=(subquery.c.repository_id == Repository.id))
        .where(Repository.namespace_user == namespace.id)
        .group_by(Repository.id)
    )

    insert_query = (
        namespace_repo_sizes.select(Repository.id, fn.sum(Manifest.layers_compressed_size))
        .join_from(Repository, RepositorySize, JOIN.LEFT_OUTER)
        .where(RepositorySize.repository_id.is_null())
    )

    RepositorySize.insert_from(
        insert_query,
        fields=[RepositorySize.repository_id, RepositorySize.size_bytes],
    ).execute()

    output = []

    for size in namespace_repo_sizes.dicts():
        output.append(
            {
                "repository_name": size["repository_name"],
                "repository_id": size["repository_id"],
                "repository_size": str(size["repository_size"]),
            }
        )

    return json.dumps(output)


def get_namespace_size(namespace_name):
    namespace = user.get_user_or_org(namespace_name)
    now_ms = get_epoch_timestamp_ms()

    subquery = (
        Tag.select(Tag.repository_id)
        .where(Tag.hidden == False)
        .where((Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms > now_ms))
        .group_by(Tag.repository_id)
        .having(fn.Count(Tag.name) > 0)
    )

    namespace_size = (
        Manifest.select(fn.sum(Manifest.layers_compressed_size))
        .join(Repository)
        .join(subquery, on=(subquery.c.repository_id == Repository.id))
        .where(Repository.namespace_user == namespace.id)
    ).scalar()

    return namespace_size


def get_repo_quota_for_view(repo_id, namespace):
    repo_quota = model.repository.get_repository_size_and_cache(repo_id).get("repository_size", 0)
    namespace_quota = get_namespace_quota(namespace)
    percent_consumed = None
    if namespace_quota:
        percent_consumed = str(round((repo_quota / namespace_quota.limit_bytes) * 100, 2))

    return {
        "percent_consumed": percent_consumed,
        "quota_bytes": repo_quota,
    }


def get_org_quota_for_view(namespace):
    namespace_quota_consumed = get_namespace_size(namespace) or 0
    configured_namespace_quota = get_namespace_quota(namespace)
    configured_namespace_quota = (
        configured_namespace_quota.limit_bytes if configured_namespace_quota else None
    )
    percent_consumed = None
    if configured_namespace_quota:
        percent_consumed = str(
            round((namespace_quota_consumed / configured_namespace_quota) * 100, 2)
        )

    return {
        "percent_consumed": percent_consumed,
        "quota_bytes": str(namespace_quota_consumed),
        "configured_quota": configured_namespace_quota,
    }
