from collections import namedtuple


class CacheKey(namedtuple("CacheKey", ["key", "expiration"])):
    """
    Defines a key into the data model cache.
    """

    pass


def for_repository_blob(namespace_name, repo_name, digest, version):
    """
    Returns a cache key for a blob in a repository.
    """
    return CacheKey("repo_blob__%s_%s_%s_%s" % (namespace_name, repo_name, digest, version), "60s")


def for_catalog_page(auth_context_key, start_id, limit):
    """
    Returns a cache key for a single page of a catalog lookup for an authed context.
    """
    params = (auth_context_key or "(anon)", start_id or 0, limit or 0)
    return CacheKey("catalog_page__%s_%s_%s" % params, "60s")


def for_namespace_geo_restrictions(namespace_name):
    """
    Returns a cache key for the geo restrictions for a namespace.
    """
    return CacheKey("geo_restrictions__%s" % (namespace_name), "240s")


def for_active_repo_tags(repository_id, start_pagination_id, limit):
    """
    Returns a cache key for the active tags in a repository.
    """
    return CacheKey(
        "repo_active_tags__%s_%s_%s" % (repository_id, start_pagination_id, limit), "120s"
    )


def for_appr_applications_list(namespace, limit):
    """
    Returns a cache key for listing applications under the App Registry.
    """
    return CacheKey("appr_applications_list_%s_%s" % (namespace, limit), "3600s")


def for_appr_show_package(namespace, package_name, release, media_type):
    """
    Returns a cache key for showing a package under the App Registry.
    """
    return CacheKey(
        "appr_show_package_%s_%s_%s-%s" % (namespace, package_name, release, media_type), "3600s"
    )
