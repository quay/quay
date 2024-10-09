from data.database import DEFAULT_PROXY_CACHE_EXPIRATION, ProxyCacheConfig, User
from data.model import InvalidProxyCacheConfigException, TagImmutableException
from data.model.organization import get_organization, has_immutable_tags


def has_proxy_cache_config(org_name):
    try:
        get_proxy_cache_config_for_org(org_name)
    except InvalidProxyCacheConfigException:
        return False
    return True


def create_proxy_cache_config(
    org_name,
    upstream_registry,
    upstream_registry_username=None,
    upstream_registry_password=None,
    expiration_s=DEFAULT_PROXY_CACHE_EXPIRATION,
    insecure=False,
    raise_on_error=False,
):
    """
    Creates proxy cache configuration for the given organization name
    """
    org = get_organization(org_name)

    if has_immutable_tags(org_name):
        if raise_on_error:
            raise TagImmutableException(
                "Cannot set proxy cache config for organization %s: it contains one or more repositories with immutable tags"
                % org_name
            )
        else:
            return None

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


def delete_proxy_cache_config(org_name):
    """
    Delete proxy cache configuration for the given organization name
    """
    org = get_organization(org_name)

    try:
        config = (ProxyCacheConfig.select().where(ProxyCacheConfig.organization == org.id)).get()
    except ProxyCacheConfig.DoesNotExist:
        return False

    if config is not None:
        ProxyCacheConfig.delete().where(ProxyCacheConfig.organization == org.id).execute()
        return True

    return False
