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
    QuotaTypes,
)
from data import model
from data.model import (
    db_transaction,
    organization,
    user,
    InvalidUsernameException,
    InvalidOrganizationException,
    notification,
    config,
    InvalidSystemQuotaConfig,
    InvalidNamespaceQuota,
    InvalidNamespaceQuotaLimit,
    InvalidNamespaceQuotaType,
)


def get_namespace_quota_list(namespace_name):
    quotas = UserOrganizationQuota.select().join(User).where(User.username == namespace_name)

    return list(quotas)


def get_namespace_quota(namespace_name, quota_id):
    quota = (
        UserOrganizationQuota.select()
        .join(User)
        .where(
            User.username == namespace_name,
            UserOrganizationQuota.id == quota_id,
        )
    )

    quota = quota.first()
    return quota


def create_namespace_quota(namespace_user, limit_bytes):
    try:
        UserOrganizationQuota.get(id == namespace_user.id)
        raise InvalidNamespaceQuota("Only one quota per namespace is currently supported")
    except UserOrganizationQuota.DoesNotExist:
        pass

    if limit_bytes > 0:
        try:
            return UserOrganizationQuota.create(namespace=namespace_user, limit_bytes=limit_bytes)
        except model.DataModelException as ex:
            return None
    else:
        raise InvalidNamespaceQuota("Invalid quota size limit value: '%s'" % limit_bytes)


def update_namespace_quota_size(quota, limit_bytes):
    if limit_bytes > 0:
        quota.limit_bytes = limit_bytes
        quota.save()
    else:
        raise InvalidNamespaceQuota("Invalid quota size limit value: '%s'" % limit_bytes)


def delete_namespace_quota(quota):
    with db_transaction():
        QuotaLimits.delete().where(QuotaLimits.quota == quota).execute()
        quota.delete_instance()


def _quota_type(type_name):
    if type_name.lower() == "warning":
        return QuotaTypes.WARNING
    elif type_name.lower() == "reject":
        return QuotaTypes.REJECT
    raise InvalidNamespaceQuotaType(
        "Quota type must be one of [{}, {}]".format(QuotaTypes.WARNING, QuotaTypes.REJECT)
    )


def get_namespace_quota_limit_list(quota, quota_type=None, percent_of_limit=None):
    if percent_of_limit and (not percent_of_limit > 0 or not percent_of_limit <= 100):
        raise InvalidNamespaceQuotaLimit("Quota limit threshold must be between 1 and 100")

    query = QuotaLimits.select().where(QuotaLimits.quota == quota)

    if quota_type:
        quota_type_name = _quota_type(quota_type)
        query = query.where(
            QuotaLimits.quota_type == (QuotaType.get(QuotaType.name == quota_type_name))
        )

    if percent_of_limit:
        query = query.where(QuotaLimits.percent_of_limit == percent_of_limit)

    return list(query)


def get_namespace_quota_limit(quota, limit_id):
    try:
        quota_limit = QuotaLimits.get(QuotaLimits.id == limit_id)
        # This should never happen in theory, as limit ids should be globally unique
        if quota_limit.quota != quota:
            raise InvalidNamespaceQuota()

        return quota_limit
    except QuotaLimits.DoesNotExist:
        return None


def create_namespace_quota_limit(quota, quota_type, percent_of_limit):
    if not percent_of_limit > 0 or not percent_of_limit <= 100:
        raise InvalidNamespaceQuotaLimit("Quota limit threshold must be between 1 and 100")

    quota_type_name = _quota_type(quota_type)

    return QuotaLimits.create(
        quota=quota,
        percent_of_limit=percent_of_limit,
        quota_type=(QuotaType.get(QuotaType.name == quota_type_name)),
    )


def update_namespace_quota_limit_threshold(limit, percent_of_limit):
    if not percent_of_limit > 0 or not percent_of_limit <= 100:
        raise InvalidNamespaceQuotaLimit("Quota limit threshold must be between 1 and 100")

    limit.percent_of_limit = percent_of_limit
    limit.save()


def update_namespace_quota_limit_type(limit, type_name):
    quota_type_name = _quota_type(type_name)
    quota_type_ref = QuotaType.get(name=quota_type_name)

    limit.quota_type = quota_type_ref
    limit.save()


def delete_namespace_quota_limit(limit):
    limit.delete_instance()


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
    namespace_user = model.user.get_user_or_org(namespace_name)
    quotas = get_namespace_quota_list(namespace_user.username)
    if not quotas:
        return {"limit_bytes": 0, "severity_level": None}

    # Currently only one quota per namespace is supported
    quota = quotas[0]
    limits = get_namespace_quota_limit_list(quota)
    limit_bytes = 0
    severity_level = None

    for limit in limits:
        bytes_allowed = int(limit.quota.limit_bytes * limit.percent_of_limit / 100)
        if size > bytes_allowed:
            if limit_bytes < bytes_allowed:
                limit_bytes = bytes_allowed
                severity_level = limit.quota_type.name

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


def get_repo_quota_for_view(namespace_name, repo_name):
    repository_ref = model.repository.get_repository(namespace_name, repo_name)
    if not repository_ref:
        return None

    quotas = get_namespace_quota_list(repository_ref.namespace_user.username)
    if not quotas:
        return {
            "quota_bytes": None,
            "configured_quota": None,
        }

    # Currently only one quota per namespace is supported
    quota = quotas[0]
    configured_namespace_quota = quota.limit_bytes

    repo_size = model.repository.get_repository_size_and_cache(repository_ref.id).get(
        "repository_size", 0
    )

    return {
        "quota_bytes": repo_size,
        "configured_quota": configured_namespace_quota,
    }


def get_org_quota_for_view(namespace_name):
    namespace_user = model.user.get_user_or_org(namespace_name)
    quotas = get_namespace_quota_list(namespace_user.username)
    if not quotas:
        return {
            "quota_bytes": None,
            "configured_quota": None,
        }

    # Currently only one quota per namespace is supported
    quota = quotas[0]
    configured_namespace_quota = quota.limit_bytes

    namespace_quota_consumed = get_namespace_size(namespace_name)
    namespace_quota_consumed = int(namespace_quota_consumed) if namespace_quota_consumed else 0

    return {
        "quota_bytes": namespace_quota_consumed,
        "configured_quota": configured_namespace_quota,
    }
