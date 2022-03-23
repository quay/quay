from data.database import ProxyCacheConfig, User, DEFAULT_PROXY_CACHE_EXPIRATION
from data.model import InvalidProxyCacheConfigException, InvalidOrganizationException
from data.model.organization import get_organization


def create_proxy_cache_config(
    org_name,
    upstream_registry,
    upstream_registry_username=None,
    upstream_registry_password=None,
    expiration_s=DEFAULT_PROXY_CACHE_EXPIRATION,
    insecure=False,
):
    """
    Creates proxy cache configuration for the given organization name
    """
    org = get_organization(org_name)

    new_entry = ProxyCacheConfig.create(
        organization=org,
        upstream_registry=upstream_registry,
        upstream_registry_username=upstream_registry_username,
        upstream_registry_password=upstream_registry_password,
        expiration_s=expiration_s,
        insecure=insecure,
    )

    return new_entry


def get_proxy_cache_config_for_org(org_name):
    """
    Return the Proxy-Cache-Config associated with the given organization name.
    Raises InvalidProxyCacheConfigException if org_name belongs to a user, or
    if org_name has no associated config.
    """
    try:
        return (
            ProxyCacheConfig.select()
            .join(User)
            .where((User.username == org_name) & (User.organization == True))
            .get()
        )
    except ProxyCacheConfig.DoesNotExist as e:
        raise InvalidProxyCacheConfigException(str(e))
