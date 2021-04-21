from collections import namedtuple


class CacheKey(namedtuple("CacheKey", ["key", "expiration"])):
    """
    Defines a key into the data model cache.
    """

    pass


def for_repository_blob(namespace_name, repo_name, digest, version, cache_config):
    """
    Returns a cache key for a blob in a repository.
    """
    cache_ttl = cache_config.get("repository_blob_cache_ttl", "60s")
    return CacheKey(
        "repo_blob__%s_%s_%s_%s" % (namespace_name, repo_name, digest, version), cache_ttl
    )


def for_catalog_page(auth_context_key, start_id, limit, cache_config):
    """
    Returns a cache key for a single page of a catalog lookup for an authed context.
    """
    params = (auth_context_key or "(anon)", start_id or 0, limit or 0)
    cache_ttl = cache_config.get("catalog_page_cache_ttl", "60s")
    return CacheKey("catalog_page__%s_%s_%s" % params, cache_ttl)


def for_namespace_geo_restrictions(namespace_name, cache_config):
    """
    Returns a cache key for the geo restrictions for a namespace.
    """
    cache_ttl = cache_config.get("namespace_geo_restrictions_cache_ttl", "240s")
    return CacheKey("geo_restrictions__%s" % namespace_name, cache_ttl)


def for_active_repo_tags(repository_id, start_pagination_id, limit, cache_config):
    """
    Returns a cache key for the active tags in a repository.
    """

    cache_ttl = cache_config.get("active_repo_tags_cache_ttl", "120s")
    return CacheKey(
        "repo_active_tags__%s_%s_%s" % (repository_id, start_pagination_id, limit), cache_ttl
    )


def for_appr_applications_list(namespace, limit, cache_config):
    """
    Returns a cache key for listing applications under the App Registry.
    """
    cache_ttl = cache_config.get("appr_applications_list_cache_ttl", "3600s")
    return CacheKey("appr_applications_list_%s_%s" % (namespace, limit), cache_ttl)


def for_appr_show_package(namespace, package_name, release, media_type, cache_config):
    """
    Returns a cache key for showing a package under the App Registry.
    """
    cache_ttl = cache_config.get("appr_show_package_cache_ttl", "3600s")
    return CacheKey(
        "appr_show_package_%s_%s_%s-%s" % (namespace, package_name, release, media_type), cache_ttl
    )
