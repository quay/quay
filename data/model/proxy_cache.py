from data.database import (
    ProxyCacheConfig,
    User
)
from data.model import DataModelException


def create_proxy_cache_config(
    org_name,
    upstream_registry,
    upstream_registry_namespace,
    upstream_registry_repository,
    upstream_registry_username,
    upstream_registry_password,
    staleness_period_s
):
    """
        Creates proxy cache configuration for the given organization name
    """
    try:
        org = User.get_organization_from_name(org_name)
        if not org:
            return None

        new_entry = ProxyCacheConfig.create(
            user_id=org.id,
            upstream_registry=upstream_registry,
            upstream_registry_namespace=upstream_registry_namespace,
            upstream_registry_repository=upstream_registry_repository,
            upstream_registry_username=upstream_registry_username,
            upstream_registry_password=upstream_registry_password,
            staleness_period_s=staleness_period_s
        )
        return new_entry

    except Exception as ex:
        raise DataModelException(ex)


def get_proxy_cache_config_for_org(org_name):
    """
        Return the Proxy-Cache-Config associated with the given organization name, or None if it doesn't exist.
    """
    try:
        org = User.get_organization_from_name(org_name)
        if not org:
            return None
        return ProxyCacheConfig.get(ProxyCacheConfig.user_id == org.id)
    except ProxyCacheConfig.DoesNotExist:
        return None

