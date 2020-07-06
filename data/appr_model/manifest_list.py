import logging
import hashlib
import json

from data.database import db_transaction


logger = logging.getLogger(__name__)


def _ensure_sha256_header(digest):
    if digest.startswith("sha256:"):
        return digest
    return "sha256:" + digest


def _digest(manifestjson):
    return _ensure_sha256_header(
        hashlib.sha256(json.dumps(manifestjson, sort_keys=True).encode("utf-8")).hexdigest()
    )


def get_manifest_list(digest, models_ref):
    ManifestList = models_ref.ManifestList
    return ManifestList.select().where(ManifestList.digest == _ensure_sha256_header(digest)).get()


def get_or_create_manifest_list(manifest_list_json, media_type_name, schema_version, models_ref):
    ManifestList = models_ref.ManifestList

    digest = _digest(manifest_list_json)
    media_type_id = ManifestList.media_type.get_id(media_type_name)

    try:
        return get_manifest_list(digest, models_ref)
    except ManifestList.DoesNotExist:
        with db_transaction():
            manifestlist = ManifestList.create(
                digest=digest,
                manifest_list_json=manifest_list_json,
                schema_version=schema_version,
                media_type=media_type_id,
            )
    return manifestlist


def create_manifestlistmanifest(manifestlist, manifest_ids, manifest_list_json, models_ref):
    """
    From a manifestlist, manifests, and the manifest list blob, create if doesn't exist the
    manfiestlistmanifest for each manifest.
    """
    for pos in range(len(manifest_ids)):
        manifest_id = manifest_ids[pos]
        manifest_json = manifest_list_json[pos]
        get_or_create_manifestlistmanifest(
            manifest=manifest_id,
            manifestlist=manifestlist,
            media_type_name=manifest_json["mediaType"],
            models_ref=models_ref,
        )


def get_or_create_manifestlistmanifest(manifest, manifestlist, media_type_name, models_ref):
    ManifestListManifest = models_ref.ManifestListManifest

    media_type_id = ManifestListManifest.media_type.get_id(media_type_name)
    try:
        ml = (
            ManifestListManifest.select().where(
                ManifestListManifest.manifest == manifest,
                ManifestListManifest.media_type == media_type_id,
                ManifestListManifest.manifest_list == manifestlist,
            )
        ).get()

    except ManifestListManifest.DoesNotExist:
        ml = ManifestListManifest.create(
            manifest_list=manifestlist, media_type=media_type_id, manifest=manifest
        )
        return ml
