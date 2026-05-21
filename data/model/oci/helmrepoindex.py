"""
Generates a Helm repository index (index.yaml) from HelmChartMetadata rows.
"""

import logging
from datetime import datetime, timezone

import regex
from packaging.version import InvalidVersion, Version

from data.database import HelmChartMetadata, Manifest, Tag

logger = logging.getLogger(__name__)


def invalidate_helm_repo_index_cache(repository_id):
    """
    Invalidates the cached Helm repository index for the given repository.

    No-ops when FEATURE_HELM_REPO_INDEX is disabled, avoiding unnecessary
    imports and cache operations. Uses lazy imports to avoid circular
    dependencies. Failures are logged at debug level and silently ignored —
    a stale cache will expire via TTL.
    """
    try:
        import features

        if not features.HELM_REPO_INDEX:
            return

        from app import model_cache
        from data.cache import cache_key

        index_key = cache_key.for_helm_repo_index(repository_id, model_cache.cache_config)
        model_cache.invalidate(index_key)
    except Exception:
        logger.debug("Failed to invalidate helm repo index cache for repo %s", repository_id)


def generate_helm_repo_index(
    repository_id, server_hostname, namespace, repo_name, tag_pattern=None
):
    """
    Build a Helm index.yaml dict for the repository.

    Only includes tags pointing to Helm OCI manifests with completed extraction.
    If tag_pattern is set, only tags whose name matches the regex are included.
    """
    compiled_pattern = None
    if tag_pattern:
        try:
            compiled_pattern = regex.compile(tag_pattern)
        except regex.error:
            logger.warning(
                "Invalid tag pattern %r for repo %s, ignoring filter", tag_pattern, repository_id
            )

    query = (
        HelmChartMetadata.select(
            HelmChartMetadata.id,
            HelmChartMetadata.manifest,
            HelmChartMetadata.chart_name,
            HelmChartMetadata.chart_version,
            HelmChartMetadata.app_version,
            HelmChartMetadata.api_version,
            HelmChartMetadata.description,
            HelmChartMetadata.chart_type,
            HelmChartMetadata.home,
            HelmChartMetadata.icon_url,
            HelmChartMetadata.deprecated,
            HelmChartMetadata.kube_version,
            HelmChartMetadata.sources,
            HelmChartMetadata.maintainers,
            HelmChartMetadata.keywords,
            HelmChartMetadata.chart_dependencies,
            Manifest.id,
            Manifest.digest,
        )
        .join(Manifest, on=(HelmChartMetadata.manifest == Manifest.id))
        .where(
            HelmChartMetadata.repository == repository_id,
            HelmChartMetadata.extraction_status == "completed",
        )
    )

    tags = Tag.select(Tag.manifest, Tag.name).where(
        Tag.repository == repository_id,
        Tag.hidden == False,
        Tag.lifetime_end_ms >> None,
    )

    manifest_to_tags = {}
    for tag in tags:
        manifest_to_tags.setdefault(tag.manifest_id, []).append(tag)

    entries = {}

    for hcm in query:
        manifest_id = hcm.manifest.id
        tag_list = manifest_to_tags.get(manifest_id, [])
        if not tag_list:
            continue

        normalized_version = hcm.chart_version.replace("+", "_")
        version_tag = None
        for tag in tag_list:
            if tag.name == normalized_version:
                version_tag = tag
                break
        if version_tag is None:
            continue

        if compiled_pattern:
            try:
                if not compiled_pattern.fullmatch(version_tag.name, timeout=1.0):
                    continue
            except (TimeoutError, regex.error):
                continue

        chart_name = hcm.chart_name
        entry = {
            "apiVersion": hcm.api_version or "v2",
            "name": chart_name,
            "version": hcm.chart_version,
            "description": hcm.description or "",
            "type": hcm.chart_type or "application",
            "urls": [f"oci://{server_hostname}/{namespace}/{repo_name}:{normalized_version}"],
            "digest": hcm.manifest.digest if hcm.manifest else "",
        }

        if hcm.app_version:
            entry["appVersion"] = hcm.app_version
        if hcm.home:
            entry["home"] = hcm.home
        if hcm.icon_url:
            entry["icon"] = hcm.icon_url
        if hcm.deprecated:
            entry["deprecated"] = True
        if hcm.kube_version:
            entry["kubeVersion"] = hcm.kube_version

        sources = _parse_json_field(hcm.sources)
        if sources:
            entry["sources"] = sources

        maintainers = _parse_json_field(hcm.maintainers)
        if maintainers:
            entry["maintainers"] = maintainers

        keywords = _parse_json_field(hcm.keywords)
        if keywords:
            entry["keywords"] = keywords

        deps = _parse_json_field(hcm.chart_dependencies)
        if deps:
            entry["dependencies"] = deps

        entries.setdefault(chart_name, []).append(entry)

    for chart_entries in entries.values():
        chart_entries.sort(key=_version_sort_key, reverse=True)

    return {
        "apiVersion": "v1",
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "entries": entries,
    }


def _version_sort_key(entry):
    """Return a Version for sorting; unparseable versions sort before all valid ones."""
    try:
        return (True, Version(entry["version"]))
    except InvalidVersion:
        return (False, entry["version"])


def _parse_json_field(value):
    """Safely parse a JSON field that might be a string or already a list/dict."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        import json

        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return None
    return None
