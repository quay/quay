import json

from peewee import JOIN, DataError, fn

from data import model
from data.database import (
    ImageStorage,
    Manifest,
    ManifestBlob,
    QuotaLimits,
    QuotaNamespaceSize,
    QuotaType,
    QuotaTypes,
    Repository,
    Tag,
    User,
    UserOrganizationQuota,
    get_epoch_timestamp_ms,
)
from data.model import (
    InvalidNamespaceQuota,
    InvalidNamespaceQuotaLimit,
    InvalidNamespaceQuotaType,
    InvalidOrganizationException,
    InvalidSystemQuotaConfig,
    InvalidUsernameException,
    UnsupportedQuotaSize,
    config,
    db_transaction,
    notification,
    organization,
    quota,
    repository,
    user,
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
        except DataError:
            raise UnsupportedQuotaSize("Unsupported quota size limit.")
        except model.DataModelException as ex:
            return None
    else:
        raise InvalidNamespaceQuota("Invalid quota size limit value: '%s'" % limit_bytes)


def get_system_default_quota(namespace=None):
    return UserOrganizationQuota(
        namespace=namespace, limit_bytes=config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES")
    )


def update_namespace_quota_size(quota, limit_bytes):
    if limit_bytes > 0:
        try:
            quota.limit_bytes = limit_bytes
            quota.save()
        except DataError:
            raise UnsupportedQuotaSize("Unsupported quota size limit.")
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
    if not quota:
        return []

    if percent_of_limit and (not percent_of_limit > 0 or not percent_of_limit <= 100):
        raise InvalidNamespaceQuotaLimit("Quota limit threshold must be between 1 and 100")

    query = QuotaLimits.select().join(QuotaType).where(QuotaLimits.quota == quota)

    if quota_type:
        quota_type_name = _quota_type(quota_type)
        query = query.where(QuotaType.name == quota_type_name)

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
    namespace_size = get_namespace_size(repository_ref.namespace_name)
    return check_limits(repository_ref.namespace_name, namespace_size)


def verify_namespace_quota_during_upload(repository_ref):
    size = model.repository.get_size_during_upload(repository_ref._db_id)
    namespace_size = get_namespace_size(repository_ref.namespace_name)
    return check_limits(repository_ref.namespace_name, size + namespace_size)


def check_limits(namespace_name, size):
    namespace_user = model.user.get_user_or_org(namespace_name)
    quotas = get_namespace_quota_list(namespace_user.username)
    if not quotas:
        default_size = config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES", 0)
        return {
            "limit_bytes": default_size,
            "severity_level": None
            if (default_size == 0 or size < default_size)
            else QuotaTypes.REJECT,
        }

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
    namespace_user = model.user.get_namespace_user(repository_ref.namespace_name)
    if namespace_user is None:
        raise InvalidUsernameException(
            "Namespace '%s' does not exist" % repository_ref.namespace_name
        )

    metadata.update({"namespace": repository_ref.namespace_name})

    if namespace_user.organization:
        admins = organization.get_admin_users(namespace_user)

        for admin in admins:
            notification.create_notification(
                notification_kind,
                admin,
                metadata,
            )
    else:
        notification.create_notification(
            notification_kind,
            namespace_user,
            metadata,
        )


def get_namespace_size(namespace_name):
    namespace = user.get_user_or_org(namespace_name)
    try:
        namespace_size_row = (
            QuotaNamespaceSize.select().where(QuotaNamespaceSize.namespace_user == namespace).get()
        )
        return namespace_size_row.size_bytes if namespace_size_row.size_bytes is not None else 0
    except QuotaNamespaceSize.DoesNotExist:
        return 0


def fetch_system_default(quotas):
    if not quotas and config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES") != 0:
        return config.app_config.get("DEFAULT_SYSTEM_REJECT_QUOTA_BYTES")

    return None


def get_repo_quota_for_view(namespace_name, repo_name):
    repository_ref = model.repository.get_repository(namespace_name, repo_name)
    if not repository_ref:
        return None

    quotas = get_namespace_quota_list(repository_ref.namespace_user.username)

    # Currently only one quota per namespace is supported
    configured_namespace_quota = quotas[0].limit_bytes if quotas else fetch_system_default(quotas)

    repo_size = model.repository.get_repository_size(repository_ref.id)

    # If FEATURE_QUOTA_MANAGEMENT is enabled & quota is not set for an org,
    # we still want to report repo's storage consumption
    return {
        "quota_bytes": repo_size,
        "configured_quota": configured_namespace_quota,
    }


def get_quota_for_view(namespace_name):

    namespace_user = model.user.get_user_or_org(namespace_name)
    quotas = get_namespace_quota_list(namespace_user.username)

    # Currently only one quota per namespace is supported
    configured_namespace_quota = quotas[0].limit_bytes if quotas else fetch_system_default(quotas)

    namespace_size = quota.get_namespace_size(namespace_user.id)
    namespace_size_exists = namespace_size is not None
    backfill_started = namespace_size_exists and namespace_size.backfill_start_ms is not None

    namespace_quota_consumed = (
        namespace_size.size_bytes
        if namespace_size_exists and namespace_size.size_bytes is not None
        else 0
    )

    backfill_status = ""
    if not namespace_size_exists or (not backfill_started and not namespace_size.backfill_complete):
        backfill_status = "waiting"
    elif backfill_started and not namespace_size.backfill_complete:
        backfill_status = "running"
    elif backfill_started and namespace_size.backfill_complete:
        backfill_status = "complete"

    # If FEATURE_QUOTA_MANAGEMENT is enabled & quota is not set for an org,
    # we still want to report org's storage consumption.
    # TODO: Remove running_backfill when changing API fields is permitted,
    # backfill_status should be used in favor of running_backfill
    return {
        "quota_bytes": namespace_quota_consumed,
        "configured_quota": configured_namespace_quota,
        "running_backfill": backfill_status,
        "backfill_status": backfill_status,
    }
