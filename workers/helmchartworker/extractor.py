import base64
import io
import json
import logging
import os
import re
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone

import requests
import yaml

from app import app
from data.database import HelmChartMetadata, Manifest
from data.model.oci.blob import get_repository_blob_by_digest
from data.model.storage import get_layer_path
from util.bytes import Bytes
from util.metrics.prometheus import (
    helm_extraction_chart_size,
    helm_extraction_duration,
    helm_extraction_total,
)
from util.security.ssrf import SSRFBlockedError, validate_external_registry_url

logger = logging.getLogger(__name__)

HELM_CHART_CONFIG_TYPE = "application/vnd.cncf.helm.config.v1+json"
HELM_CHART_CONTENT_LAYER_TYPES = (
    "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
    "application/tar+gzip",
)
HELM_CHART_PROVENANCE_TYPE = "application/vnd.cncf.helm.chart.provenance.v1.prov"

PULLSPEC_RE = re.compile(
    r"^"
    r"(?:(?P<registry>"
    r"[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)+(?::\d+)?"  # multi-label (e.g. docker.io, my.reg:5000)
    r"|[a-zA-Z0-9_-]+:\d+"  # single-label with port (e.g. localhost:5000)
    r")/)"
    r"(?P<repo>[a-zA-Z0-9._/-]+)"
    r"(?::(?P<tag>[\w][\w.+-]{0,127})|@(?P<digest>sha256:[a-fA-F0-9]{64}))?$"
)

IMAGE_KEY_NAMES = frozenset(
    {
        "image",
        "images",
        "initimage",
        "sidecarimage",
        "proxyimage",
    }
)

ALLOWED_ICON_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/svg+xml",
        "image/webp",
    }
)


class HelmExtractionError(Exception):
    pass


def extract_helm_chart_metadata(manifest_id, repository_id, storage):
    """
    Extract metadata from a Helm chart OCI artifact and store it in the database.

    Always writes a HelmChartMetadata row, even on failure, to prevent the backfill
    worker from retrying permanently-broken manifests.
    """
    start_time = time.monotonic()
    status = "failed"

    try:
        _do_extract(manifest_id, repository_id, storage)
        status = "completed"
    except HelmExtractionError as exc:
        logger.warning(
            "Helm chart extraction failed for manifest %s: %s",
            manifest_id,
            exc,
        )
        _write_failed_row(manifest_id, repository_id, str(exc))
    except Exception as exc:
        logger.exception(
            "Unexpected error during Helm chart extraction for manifest %s",
            manifest_id,
        )
        _write_failed_row(manifest_id, repository_id, f"unexpected error: {exc}")
    finally:
        duration = time.monotonic() - start_time
        helm_extraction_duration.labels(status=status).observe(duration)
        helm_extraction_total.labels(status=status).inc()

        try:
            from data.model.oci.helmrepoindex import invalidate_helm_repo_index_cache

            invalidate_helm_repo_index_cache(repository_id)
        except Exception:
            logger.debug("Failed to invalidate helm repo index cache for repo %s", repository_id)


def _write_failed_row(manifest_id, repository_id, error_message):
    """Write or overwrite a HelmChartMetadata row as a failure tombstone."""
    tombstone_fields = {
        "repository": repository_id,
        "chart_name": "",
        "chart_version": "",
        "app_version": None,
        "api_version": "",
        "description": None,
        "kube_version": None,
        "chart_type": None,
        "home": None,
        "icon_url": None,
        "deprecated": False,
        "sources": [],
        "maintainers": [],
        "chart_dependencies": [],
        "keywords": [],
        "annotations": {},
        "chart_yaml": "",
        "readme": None,
        "values_yaml": None,
        "values_schema_json": None,
        "provenance": None,
        "provenance_key_id": None,
        "provenance_hash_algorithm": None,
        "provenance_signature_date": None,
        "icon_data": None,
        "icon_media_type": None,
        "file_tree": [],
        "image_references": [],
        "extraction_status": "failed",
        "extraction_error": error_message,
    }
    try:
        row, created = HelmChartMetadata.get_or_create(
            manifest=manifest_id,
            defaults=tombstone_fields,
        )
        if not created:
            for field, value in tombstone_fields.items():
                setattr(row, field, value)
            row.save()
    except Exception:
        logger.exception(
            "Failed to write failed HelmChartMetadata row for manifest %s",
            manifest_id,
        )


def _do_extract(manifest_id, repository_id, storage):
    max_layer_size = app.config.get("HELM_CHART_MAX_LAYER_SIZE", 20 * 1024 * 1024)
    max_file_size = app.config.get("HELM_CHART_MAX_EXTRACTED_FILE_SIZE", 1 * 1024 * 1024)
    max_icon_size = app.config.get("HELM_CHART_MAX_ICON_SIZE", 512 * 1024)
    icon_timeout = app.config.get("HELM_CHART_ICON_DOWNLOAD_TIMEOUT", 5)

    try:
        manifest_row = Manifest.get(Manifest.id == manifest_id)
    except Manifest.DoesNotExist as exc:
        raise HelmExtractionError(f"manifest {manifest_id} not found") from exc

    manifest_data = json.loads(
        Bytes.for_string_or_unicode(manifest_row.manifest_bytes).as_unicode()
    )

    layers = manifest_data.get("layers", [])
    chart_layer_digest = None
    provenance_layer_digest = None

    for layer in layers:
        media_type = layer.get("mediaType", "")
        if media_type in HELM_CHART_CONTENT_LAYER_TYPES and chart_layer_digest is None:
            chart_layer_digest = layer.get("digest")
        elif media_type == HELM_CHART_PROVENANCE_TYPE and provenance_layer_digest is None:
            provenance_layer_digest = layer.get("digest")

    if chart_layer_digest is None:
        raise HelmExtractionError("no Helm chart content layer found in manifest")

    blob_record = get_repository_blob_by_digest(repository_id, chart_layer_digest)
    if blob_record is None:
        raise HelmExtractionError(f"chart content blob {chart_layer_digest} not found in storage")

    if blob_record.image_size is None:
        raise HelmExtractionError(
            f"chart content blob {chart_layer_digest} has unknown size; refusing to download"
        )

    if blob_record.image_size > max_layer_size:
        raise HelmExtractionError(
            f"chart layer size {blob_record.image_size} exceeds limit {max_layer_size}"
        )

    chart_blob = storage.get_content(blob_record.locations, get_layer_path(blob_record))
    if chart_blob is None:
        raise HelmExtractionError(f"chart content blob {chart_layer_digest} not readable")

    blob_size = len(chart_blob)
    helm_extraction_chart_size.observe(blob_size)

    try:
        tar = tarfile.open(fileobj=io.BytesIO(chart_blob), mode="r:gz")
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise HelmExtractionError(f"corrupt or invalid tar+gzip archive: {exc}") from exc

    chart_yaml_content = None
    readme_content = None
    values_yaml_content = None
    values_schema_content = None
    file_tree = []

    max_members = 10000
    member_count = 0

    try:
        member = tar.next()
        while member is not None:
            member_count += 1
            if member_count > max_members:
                raise HelmExtractionError(f"archive exceeds max member count ({max_members})")

            if member.issym() or member.islnk():
                member = tar.next()
                continue

            normalized = _normalize_path(member.name)
            if normalized is None:
                raise HelmExtractionError(f"tar contains path traversal: {member.name}")

            if member.isfile():
                file_tree.append({"path": normalized, "size": member.size})

            parts = normalized.split("/")
            basename = parts[-1].lower() if parts else ""
            depth = len(parts)

            if not member.isfile():
                member = tar.next()
                continue

            if basename == "chart.yaml" and depth <= 2:
                chart_yaml_content = _safe_read_member(tar, member, max_file_size, required=True)
            elif basename == "readme.md" and depth <= 2:
                readme_content = _safe_read_member(tar, member, max_file_size, required=False)
            elif basename == "values.yaml" and depth <= 2:
                values_yaml_content = _safe_read_member(tar, member, max_file_size, required=False)
            elif basename == "values.schema.json" and depth <= 2:
                values_schema_content = _safe_read_member(
                    tar, member, max_file_size, required=False
                )

            member = tar.next()
    finally:
        tar.close()

    if chart_yaml_content is None:
        raise HelmExtractionError("Chart.yaml not found in archive")

    try:
        chart_data = yaml.safe_load(chart_yaml_content)
    except yaml.YAMLError as exc:
        raise HelmExtractionError(f"Chart.yaml is not valid YAML: {exc}") from exc

    if not isinstance(chart_data, dict):
        raise HelmExtractionError("Chart.yaml root is not a mapping")

    for required_field in ("name", "version", "apiVersion"):
        if required_field not in chart_data:
            raise HelmExtractionError(f"Chart.yaml missing mandatory field: {required_field}")
        value = chart_data[required_field]
        if not isinstance(value, str) or not value.strip():
            raise HelmExtractionError(
                f"Chart.yaml field '{required_field}' must be a non-empty string, got: {value!r}"
            )

    icon_url = chart_data.get("icon")
    icon_data = None
    icon_media_type = None

    if isinstance(icon_url, str) and icon_url.strip():
        icon_data, icon_media_type = _download_icon(icon_url, max_icon_size, icon_timeout)

    provenance_content = None
    if provenance_layer_digest:
        try:
            prov_record = get_repository_blob_by_digest(repository_id, provenance_layer_digest)
            if prov_record is not None:
                if prov_record.image_size is None:
                    logger.warning(
                        "Provenance layer has unknown size for manifest %s, skipping",
                        manifest_id,
                    )
                elif prov_record.image_size > max_file_size:
                    logger.warning(
                        "Provenance layer oversized for manifest %s, skipping",
                        manifest_id,
                    )
                else:
                    prov_blob = storage.get_content(
                        prov_record.locations, get_layer_path(prov_record)
                    )
                    if prov_blob is not None:
                        if len(prov_blob) <= max_file_size:
                            provenance_content = prov_blob.decode("utf-8", errors="replace")
                        else:
                            logger.warning(
                                "Provenance layer oversized for manifest %s, skipping",
                                manifest_id,
                            )
        except Exception:
            logger.warning(
                "Failed to read provenance layer for manifest %s, skipping",
                manifest_id,
                exc_info=True,
            )

    image_refs = _extract_images_from_values(values_yaml_content)
    prov_meta = _extract_provenance_metadata(provenance_content)

    metadata_fields = {
        "repository": repository_id,
        "chart_name": chart_data["name"],
        "chart_version": chart_data["version"],
        "app_version": chart_data.get("appVersion"),
        "api_version": chart_data["apiVersion"],
        "description": chart_data.get("description"),
        "kube_version": chart_data.get("kubeVersion"),
        "chart_type": chart_data.get("type"),
        "home": chart_data.get("home"),
        "icon_url": icon_url,
        "deprecated": chart_data.get("deprecated", False),
        "sources": chart_data.get("sources", []),
        "maintainers": chart_data.get("maintainers", []),
        "chart_dependencies": chart_data.get("dependencies", []),
        "keywords": chart_data.get("keywords", []),
        "annotations": chart_data.get("annotations", {}),
        "chart_yaml": chart_yaml_content,
        "readme": readme_content,
        "values_yaml": values_yaml_content,
        "values_schema_json": values_schema_content,
        "provenance": provenance_content,
        "provenance_key_id": prov_meta["key_id"],
        "provenance_hash_algorithm": prov_meta["hash_algorithm"],
        "provenance_signature_date": prov_meta["signature_date"],
        "icon_data": icon_data,
        "icon_media_type": icon_media_type,
        "file_tree": file_tree,
        "image_references": image_refs,
        "extraction_status": "completed",
        "extraction_error": None,
    }

    row, created = HelmChartMetadata.get_or_create(
        manifest=manifest_id,
        defaults=metadata_fields,
    )

    if not created:
        for key, value in metadata_fields.items():
            setattr(row, key, value)
        row.save()

    logger.info(
        "Helm chart metadata extracted for manifest %s: %s %s",
        manifest_id,
        chart_data["name"],
        chart_data["version"],
    )


def _normalize_path(name):
    """Normalize a tar member path and reject traversal attempts."""
    import posixpath

    cleaned = posixpath.normpath(name)
    if cleaned.startswith("/") or cleaned.startswith(".."):
        return None
    return cleaned


def _safe_read_member(tar, member, max_size, required=False):
    """Read a tar member's contents, enforcing size limits."""
    if member.size > max_size:
        if required:
            raise HelmExtractionError(
                f"required file {member.name} exceeds size limit " f"({member.size} > {max_size})"
            )
        logger.warning(
            "Skipping oversized file %s (%d bytes, limit %d)",
            member.name,
            member.size,
            max_size,
        )
        return None

    f = tar.extractfile(member)
    if f is None:
        return None
    try:
        data = f.read(max_size + 1)
        if len(data) > max_size:
            if required:
                raise HelmExtractionError(f"required file {member.name} exceeds size limit")
            return None
        return data.decode("utf-8", errors="replace")
    finally:
        f.close()


def _download_icon(url, max_size, timeout):
    """
    Download a chart icon. Returns (base64_data, media_type) or (None, None) on any failure.
    This is a soft failure -- icon download problems never fail the extraction.

    ``timeout`` is used both as a per-socket-operation timeout (connect + read)
    and as the total wall-clock deadline for the entire download.
    """
    try:
        validate_external_registry_url(url)
    except (SSRFBlockedError, ValueError) as exc:
        logger.warning("Icon URL %s blocked by SSRF protection: %s", url, exc)
        return None, None

    resp = None
    try:
        deadline = time.monotonic() + timeout
        resp = requests.get(url, timeout=timeout, stream=True, allow_redirects=False)

        if resp.is_redirect or resp.is_permanent_redirect:
            logger.warning("Icon at %s returned a redirect; rejecting", url)
            return None, None

        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_ICON_CONTENT_TYPES:
            logger.warning("Icon at %s has unsupported content-type: %s", url, content_type)
            return None, None

        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > max_size:
                logger.warning("Icon at %s exceeds size limit %d", url, max_size)
                return None, None
            if time.monotonic() > deadline:
                logger.warning("Icon download from %s exceeded total timeout %ds", url, timeout)
                return None, None
            chunks.append(chunk)

        raw = b"".join(chunks)
        return base64.b64encode(raw).decode("ascii"), content_type
    except Exception:
        logger.warning("Failed to download icon from %s", url, exc_info=True)
        return None, None
    finally:
        if resp is not None:
            resp.close()


def _extract_images_from_values(values_yaml_content):
    """
    Extract container image references from a parsed values.yaml.

    Uses two strategies:
    1. Structured detection: finds dicts with a ``repository`` key (optionally
       accompanied by ``registry``, ``tag``, ``digest``) under keys whose name
       contains "image".
    2. Pull-spec detection: finds string values under image-related keys that
       look like full pull specs (e.g. ``quay.io/org/repo:tag``).

    Returns a deduplicated list of ``{"image": "<pullspec>", "source": "<dotted.path>"}``.
    """
    if not values_yaml_content:
        return []

    try:
        values = yaml.safe_load(values_yaml_content)
    except yaml.YAMLError:
        return []

    if not isinstance(values, dict):
        return []

    refs = []
    seen = set()

    def _add(pullspec, source):
        if pullspec and pullspec not in seen:
            seen.add(pullspec)
            refs.append({"image": pullspec, "source": source})

    _walk_values(values, "", _add)
    return refs


def _walk_values(node, path, add_fn):
    """Recursively walk a YAML tree looking for image references."""
    if isinstance(node, dict):
        for key, value in node.items():
            key_str = key if isinstance(key, str) else str(key)
            child_path = f"{path}.{key_str}" if path else key_str
            key_lower = key_str.lower()

            if isinstance(value, dict) and "repository" in value:
                has_image_field = "tag" in value or "digest" in value or "registry" in value
                if has_image_field or _is_image_key(key_lower):
                    pullspec = _assemble_pullspec(value)
                    if pullspec:
                        add_fn(pullspec, child_path)
                        continue

            if _is_image_key(key_lower) and isinstance(value, str):
                if PULLSPEC_RE.match(value):
                    add_fn(value, child_path)
                    continue

            if _is_image_key(key_lower) and isinstance(value, list):
                for i, item in enumerate(value):
                    item_path = f"{child_path}[{i}]"
                    if isinstance(item, str) and PULLSPEC_RE.match(item):
                        add_fn(item, item_path)
                    elif isinstance(item, dict):
                        pullspec = _assemble_pullspec(item)
                        if pullspec:
                            add_fn(pullspec, item_path)
                        else:
                            _walk_values(item, item_path, add_fn)
                    else:
                        _walk_values(item, item_path, add_fn)
                continue

            _walk_values(value, child_path, add_fn)

    elif isinstance(node, list):
        for i, item in enumerate(node):
            _walk_values(item, f"{path}[{i}]", add_fn)


def _is_image_key(key):
    """Check whether a YAML key name suggests it holds an image reference."""
    normalized = key.replace("_", "").replace("-", "")
    if normalized in IMAGE_KEY_NAMES:
        return True
    if normalized.endswith("image") or normalized.endswith("imageref"):
        return True
    return False


def _assemble_pullspec(image_dict):
    """
    Build a pull spec string from a structured image dict.

    Handles the common conventions:
      - {repository: "nginx", tag: "1.25"}
      - {registry: "docker.io", repository: "library/nginx", tag: "1.25"}
      - {repository: "nginx", digest: "sha256:abc..."}
      - {registry: "quay.io", repository: "org/repo/sub", tag: "v1"}
    """
    repository = image_dict.get("repository")
    if not repository or not isinstance(repository, str):
        return None

    registry = image_dict.get("registry", "")
    tag = image_dict.get("tag", "")
    digest = image_dict.get("digest", "")

    if isinstance(registry, str) and registry:
        pullspec = f"{registry}/{repository}"
    else:
        pullspec = repository

    if isinstance(digest, str) and digest:
        if not digest.startswith("sha256:"):
            digest = f"sha256:{digest}"
        pullspec = f"{pullspec}@{digest}"
    elif isinstance(tag, (str, int, float)) and not isinstance(tag, bool) and str(tag):
        pullspec = f"{pullspec}:{tag}"

    return pullspec


def _extract_provenance_metadata(prov_content):
    """
    Extract signature metadata from a Helm .prov file (PGP cleartext-signed message).

    Uses the gpg CLI with --status-fd for machine-readable output, which avoids
    depending on Python-version-specific GPGME bindings.

    Returns a dict with keys: key_id, hash_algorithm, signature_date.
    Each value is a string or None if extraction fails.
    """
    result = {
        "key_id": None,
        "hash_algorithm": None,
        "signature_date": None,
    }

    if not prov_content:
        return result

    hash_match = re.search(r"^Hash:\s*([A-Za-z0-9-]+)", prov_content, re.MULTILINE | re.IGNORECASE)
    if hash_match:
        result["hash_algorithm"] = hash_match.group(1)

    try:
        with tempfile.TemporaryDirectory() as gpg_home:
            prov_path = os.path.join(gpg_home, "chart.prov")
            with open(prov_path, "w") as f:
                f.write(prov_content)

            proc = subprocess.run(
                [
                    "gpg",
                    "--homedir",
                    gpg_home,
                    "--status-fd",
                    "1",
                    "--verify",
                    prov_path,
                ],
                capture_output=True,
                timeout=30,
            )
            status = proc.stdout.decode("utf-8", errors="replace")

            # ERRSIG is emitted when the signing key is not in our keyring
            # (which is always the case since we use a throwaway homedir).
            # Format: [GNUPG:] ERRSIG <keyid> <pkalgo> <hashalgo> <class> <time> <rc>
            errsig = re.search(r"\[GNUPG:\] ERRSIG (\S+) \S+ \S+ \S+ (\S+)", status)
            if errsig:
                result["key_id"] = errsig.group(1)
                try:
                    ts = int(errsig.group(2))
                    if ts > 0:
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        result["signature_date"] = dt.isoformat()
                except (ValueError, OSError):
                    pass

            # VALIDSIG is emitted when the key is known (unlikely in our
            # throwaway homedir, but handle it for completeness).
            # Format: [GNUPG:] VALIDSIG <fpr> <created> <sigtime> ...
            validsig = re.search(r"\[GNUPG:\] VALIDSIG (\S+) \S+ (\S+)", status)
            if validsig:
                result["key_id"] = validsig.group(1)[-16:]
                try:
                    ts = int(validsig.group(2))
                    if ts > 0:
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        result["signature_date"] = dt.isoformat()
                except (ValueError, OSError):
                    pass

    except FileNotFoundError:
        logger.debug("gpg binary not found, skipping provenance signature parsing")
    except subprocess.TimeoutExpired:
        logger.debug("gpg timed out during provenance parsing")
    except Exception:
        logger.debug("Failed to parse provenance signature metadata", exc_info=True)

    return result
