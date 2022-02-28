import json
import humanfriendly

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
)
from data.model import (
    InvalidOrganizationException,
    _basequery,
    organization,
    user,
    InvalidUsernameException,
    repository,
    notification,
)

HUMANIZED_QUOTA_UNITS = [i.decimal.symbol for i in humanfriendly.disk_size_units] + ["bytes"]


def verify_namespace_quota(namespace_name, repository_ref):
    repository.get_repository_size_and_cache(repository_ref._db_id)
    namespace_size = get_namespace_size(namespace_name)
    return check_limits(namespace_name, namespace_size)


def verify_namespace_quota_force_cache(namespace_name, repository_ref):
    force_cache_repo_size(repository_ref)
    namespace_size = get_namespace_size(namespace_name)
    return check_limits(namespace_name, namespace_size)


def verify_namespace_quota_during_upload(namespace_name, repository_ref):
    size = __gather_size_by_chunk_upload(repository_ref._db_id)
    namespace_size = get_namespace_size(namespace_name)
    if namespace_size is None:
        namespace_size = 0

    return check_limits(namespace_name, size + namespace_size)


def check_limits(namespace_name, size):
    limits = __get_namespace_limits(namespace_name)
    limit_bytes = 0
    severity_level = None
    for limit in limits:
        if size > limit["bytes_allowed"]:
            if limit_bytes < limit["bytes_allowed"]:
                limit_bytes = limit["bytes_allowed"]
                severity_level = limit["type_id"]

    return {"limit_bytes": limit_bytes, "severity_level": severity_level}


def __gather_size_by_chunk_upload(repo_id):
    return repository.get_size_during_upload(repo_id)


def notify_organization_admins(repository_ref, notification_kind, metadata={}):
    if repository_ref.namespace_user.organization:
        org = organization.get_organization(repository_ref.namespace_user)
        admins = organization.get_admin_users(org)

        for admin in admins:
            notification.create_notification(
                notification_kind, admin, {"namespace": repository_ref.namespace_user}
            )
    else:
        notification.create_notification(
            notification_kind,
            repository_ref.namespace_user,
            {"namespace": repository_ref.namespace_user},
        )


def __get_namespace_limits(namespace_name):
    return get_namespace_limits(namespace_name)


def force_cache_repo_size(repository_ref):
    return repository.force_cache_repo_size(repository_ref._db_id)


def create_namespace_quota(name, limit_bytes):
    user_object = user.get_namespace_user(name)

    UserOrganizationQuota.create(namespace_id=user_object.id, limit_bytes=limit_bytes)

    return UserOrganizationQuota


def create_namespace_limit(orgname, quota_type_id, percent_of_limit):
    quota = get_namespace_quota(orgname)

    if quota is None:
        raise InvalidUsernameException("Quota Does Not Exist for : " + orgname)

    quota = quota.get()

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


def get_namespace_limits(name):
    return _basequery.get_namespace_quota_limits(name)


def get_namespace_limit(name, quota_type_id, percent_of_limit):
    try:
        quota = get_namespace_quota(name)

        if quota is None:
            raise InvalidUsernameException("Quota for this namespace does not exist")

        quota = quota.get()

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

        quota = quota.get()

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

        quota = quota.get()

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


def get_namespace_limit_types_for_id(quota_limit_type_id):
    return QuotaType.select().where(QuotaType.id == quota_limit_type_id).get()


def get_namespace_limit_types_for_name(name):
    return QuotaType.select().where(QuotaType.name == name).get()


def change_namespace_quota(name, limit_bytes):
    org = user.get_namespace_user(name)
    quota = UserOrganizationQuota.select().where(UserOrganizationQuota.namespace_id == org.id).get()

    quota.limit_bytes = limit_bytes
    quota.save()

    return quota


def change_namespace_quota_limit(name, percent_of_limit, quota_type_id, new_percent_of_limit):
    quota_limit = get_namespace_limit(name, quota_type_id, percent_of_limit)

    quota_limit.percent_of_limit = new_percent_of_limit
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
    repo_quota = repository.get_repository_size_and_cache(repo_id).get("repository_size", 0)
    namespace_quota = get_namespace_quota(namespace)
    namespace_quota = namespace_quota.get() if namespace_quota else None
    percent_consumed = None
    if namespace_quota:
        percent_consumed = str(round((repo_quota / namespace_quota.limit_bytes) * 100, 2))

    return {
        "quota_consumed": humanfriendly.format_size(repo_quota),
        "percent_consumed": percent_consumed,
        "quota_bytes": repo_quota,
    }


def get_org_quota_for_view(namespace):
    namespace_quota_consumed = get_namespace_size(namespace) or 0
    configured_namespace_quota = get_namespace_quota(namespace)
    configured_namespace_quota = (
        configured_namespace_quota.get() if configured_namespace_quota else None
    )
    percent_consumed = None
    if configured_namespace_quota:
        percent_consumed = str(
            round((namespace_quota_consumed / configured_namespace_quota.limit_bytes) * 100, 2)
        )

    return {
        "quota_consumed": humanfriendly.format_size(namespace_quota_consumed),
        "percent_consumed": percent_consumed,
        "quota_bytes": str(namespace_quota_consumed),
    }
