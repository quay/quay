import logging
from collections import namedtuple

logger = logging.getLogger(__name__)


class CacheKey(namedtuple("CacheKey", ["key", "expiration"])):
    """
    Defines a key into the data model cache.
    """

    pass


def for_upstream_registry_token(org_name, upstream_registry, repo_name, expires_in):
    """
    Returns a cache key for an upstream registry auth token.
    """
    # use / to separate input values because org names cannot contain /, meaning
    # that the token cannot be spoofed by a malicious actor.
    key = f"upstream_token__{org_name}/{upstream_registry}/{repo_name}"
    return CacheKey(key, expires_in)


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


def for_active_repo_tags(repository_id, last_pagination_tag_name, limit, cache_config):
    """
    Returns a cache key for the active tags in a repository.
    """

    cache_ttl = cache_config.get("active_repo_tags_cache_ttl", "120s")
    return CacheKey(
        "repo_active_tags__%s_%s_%s" % (repository_id, last_pagination_tag_name, limit), cache_ttl
    )


def for_security_report(digest, cache_config):
    """
    Returns a cache key for showing a security report.
    """

    # Security reports don't change often so a longer TTL can be justified.
    cache_ttl = cache_config.get("security_report_cache_ttl", "300s")
    return CacheKey(f"security_report__{digest}", cache_ttl)


def for_repository_lookup(namespace_name, repo_name, manifest_ref, kind_filter, cache_config):
    """
    Returns a cache key for repository lookup.
    """

    cache_ttl = cache_config.get("repository_lookup_cache_ttl", "120s")
    cache_key = f"repository_lookup_{namespace_name}_{repo_name}"

    if manifest_ref is not None:
        cache_key = f"{cache_key}_{manifest_ref}"
    if kind_filter is not None:
        cache_key = f"{cache_key}_{kind_filter}"

    logger.debug(f"Loading repository lookup from cache_key: {cache_key}")
    return CacheKey(cache_key, cache_ttl)


def for_repository_manifest(repository_id, digest, cache_config):
    """
    Returns a cache key for the manifest of a repository.
    """
    cache_ttl = cache_config.get("repository_manifest_cache_ttl", "300s")
    return CacheKey("repository_manifest__%s_%s" % (repository_id, digest), cache_ttl)


def for_manifest_referrers(repository_id, manifest_digest, cache_config):
    """
    Returns a cache key for listing a manifest's referrers
    """
    cache_ttl = cache_config.get("manifest_referrers_cache_ttl", "60s")
    return CacheKey(f"manifest_referrers__{repository_id}_{manifest_digest}", cache_ttl)
