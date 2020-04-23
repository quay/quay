import logging
import hashlib
import json

from cnr.models.package_base import get_media_type

from data.database import db_transaction, MediaType
from data.appr_model import tag as tag_model


logger = logging.getLogger(__name__)


def _ensure_sha256_header(digest):
    if digest.startswith("sha256:"):
        return digest
    return "sha256:" + digest


def _digest(manifestjson):
    return _ensure_sha256_header(
        hashlib.sha256(json.dumps(manifestjson, sort_keys=True).encode("utf-8")).hexdigest()
    )


def get_manifest_query(digest, media_type, models_ref):
    Manifest = models_ref.Manifest
    return Manifest.select().where(
        Manifest.digest == _ensure_sha256_header(digest),
        Manifest.media_type == Manifest.media_type.get_id(media_type),
    )


def get_manifest_with_blob(digest, media_type, models_ref):
    Blob = models_ref.Blob
    query = get_manifest_query(digest, media_type, models_ref)
    return query.join(Blob).get()


def get_or_create_manifest(manifest_json, media_type_name, models_ref):
    Manifest = models_ref.Manifest
    digest = _digest(manifest_json)
    try:
        manifest = get_manifest_query(digest, media_type_name, models_ref).get()
    except Manifest.DoesNotExist:
        with db_transaction():
            manifest = Manifest.create(
                digest=digest,
                manifest_json=manifest_json,
                media_type=Manifest.media_type.get_id(media_type_name),
            )
    return manifest


def get_manifest_types(repo, models_ref, release=None):
    """
    Returns an array of MediaTypes.name for a repo, can filter by tag.
    """
    Tag = models_ref.Tag
    ManifestListManifest = models_ref.ManifestListManifest

    query = tag_model.tag_is_alive(
        Tag.select(MediaType.name)
        .join(ManifestListManifest, on=(ManifestListManifest.manifest_list == Tag.manifest_list))
        .join(MediaType, on=(ManifestListManifest.media_type == MediaType.id))
        .where(Tag.repository == repo, Tag.tag_kind == Tag.tag_kind.get_id("release")),
        Tag,
    )
    if release:
        query = query.where(Tag.name == release)

    manifests = set()
    for m in query.distinct().tuples():
        manifests.add(get_media_type(m[0]))
    return manifests
