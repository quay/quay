import bisect

from cnr.exception import PackageAlreadyExists
from cnr.models.package_base import manifest_media_type

from data.database import db_transaction, get_epoch_timestamp
from data.appr_model import (
    blob as blob_model,
    manifest as manifest_model,
    manifest_list as manifest_list_model,
    tag as tag_model,
)


LIST_MEDIA_TYPE = "application/vnd.cnr.manifest.list.v0.json"
SCHEMA_VERSION = "v0"


def _ensure_sha256_header(digest):
    if digest.startswith("sha256:"):
        return digest
    return "sha256:" + digest


def get_app_release(repo, tag_name, media_type, models_ref):
    """
    Returns (tag, manifest, blob) given a repo object, tag_name, and media_type).
    """
    ManifestListManifest = models_ref.ManifestListManifest
    Manifest = models_ref.Manifest
    Blob = models_ref.Blob
    ManifestBlob = models_ref.ManifestBlob
    manifestlistmanifest_set_name = models_ref.manifestlistmanifest_set_name

    tag = tag_model.get_tag(repo, tag_name, models_ref, tag_kind="release")
    media_type_id = ManifestListManifest.media_type.get_id(manifest_media_type(media_type))
    manifestlistmanifest = (
        getattr(tag.manifest_list, manifestlistmanifest_set_name)
        .join(Manifest)
        .where(ManifestListManifest.media_type == media_type_id)
        .get()
    )
    manifest = manifestlistmanifest.manifest
    blob = Blob.select().join(ManifestBlob).where(ManifestBlob.manifest == manifest).get()
    return (tag, manifest, blob)


def delete_app_release(repo, tag_name, media_type, models_ref):
    """Terminate a Tag/media-type couple
    It find the corresponding tag/manifest and remove from the manifestlistmanifest the manifest
    1. it terminates the current tag (in all-cases)
    2. if the new manifestlist is not empty, it creates a new tag for it
    """
    ManifestListManifest = models_ref.ManifestListManifest
    manifestlistmanifest_set_name = models_ref.manifestlistmanifest_set_name

    media_type_id = ManifestListManifest.media_type.get_id(manifest_media_type(media_type))

    with db_transaction():
        tag = tag_model.get_tag(repo, tag_name, models_ref)
        manifest_list = tag.manifest_list
        list_json = manifest_list.manifest_list_json
        mlm_query = ManifestListManifest.select().where(
            ManifestListManifest.manifest_list == tag.manifest_list
        )
        list_manifest_ids = sorted([mlm.manifest_id for mlm in mlm_query])
        manifestlistmanifest = (
            getattr(tag.manifest_list, manifestlistmanifest_set_name)
            .where(ManifestListManifest.media_type == media_type_id)
            .get()
        )
        index = list_manifest_ids.index(manifestlistmanifest.manifest_id)
        list_manifest_ids.pop(index)
        list_json.pop(index)

        if not list_json:
            tag.lifetime_end = get_epoch_timestamp()
            tag.save()
        else:
            manifestlist = manifest_list_model.get_or_create_manifest_list(
                list_json, LIST_MEDIA_TYPE, SCHEMA_VERSION, models_ref
            )
            manifest_list_model.create_manifestlistmanifest(
                manifestlist, list_manifest_ids, list_json, models_ref
            )
            tag = tag_model.create_or_update_tag(
                repo, tag_name, models_ref, manifest_list=manifestlist, tag_kind="release"
            )
        return tag


def create_app_release(repo, tag_name, manifest_data, digest, models_ref, force=False):
    """
    Create a new application release, it includes creating a new Tag, ManifestList,
    ManifestListManifests, Manifest, ManifestBlob.

    To deduplicate the ManifestList, the manifestlist_json is kept ordered by the manifest.id. To
    find the insert point in the ManifestList it uses bisect on the manifest-ids list.
    """
    ManifestList = models_ref.ManifestList
    ManifestListManifest = models_ref.ManifestListManifest
    Blob = models_ref.Blob
    ManifestBlob = models_ref.ManifestBlob

    with db_transaction():
        # Create/get the package manifest
        manifest = manifest_model.get_or_create_manifest(
            manifest_data, manifest_data["mediaType"], models_ref
        )
        # get the tag
        tag = tag_model.get_or_initialize_tag(repo, tag_name, models_ref)

        if tag.manifest_list is None:
            tag.manifest_list = ManifestList(
                media_type=ManifestList.media_type.get_id(LIST_MEDIA_TYPE),
                schema_version=SCHEMA_VERSION,
                manifest_list_json=[],
            )

        elif tag_model.tag_media_type_exists(tag, manifest.media_type, models_ref):
            if force:
                delete_app_release(repo, tag_name, manifest.media_type.name, models_ref)
                return create_app_release(
                    repo, tag_name, manifest_data, digest, models_ref, force=False
                )
            else:
                raise PackageAlreadyExists("package exists already")

        list_json = tag.manifest_list.manifest_list_json
        mlm_query = ManifestListManifest.select().where(
            ManifestListManifest.manifest_list == tag.manifest_list
        )
        list_manifest_ids = sorted([mlm.manifest_id for mlm in mlm_query])
        insert_point = bisect.bisect_left(list_manifest_ids, manifest.id)
        list_json.insert(insert_point, manifest.manifest_json)
        list_manifest_ids.insert(insert_point, manifest.id)
        manifestlist = manifest_list_model.get_or_create_manifest_list(
            list_json, LIST_MEDIA_TYPE, SCHEMA_VERSION, models_ref
        )
        manifest_list_model.create_manifestlistmanifest(
            manifestlist, list_manifest_ids, list_json, models_ref
        )

        tag = tag_model.create_or_update_tag(
            repo, tag_name, models_ref, manifest_list=manifestlist, tag_kind="release"
        )
        blob_digest = digest

        try:
            (
                ManifestBlob.select()
                .join(Blob)
                .where(
                    ManifestBlob.manifest == manifest,
                    Blob.digest == _ensure_sha256_header(blob_digest),
                )
                .get()
            )
        except ManifestBlob.DoesNotExist:
            blob = blob_model.get_blob(blob_digest, models_ref)
            ManifestBlob.create(manifest=manifest, blob=blob)
        return tag


def get_release_objs(repo, models_ref, media_type=None):
    """
    Returns an array of Tag for a repo, with optional filtering by media_type.
    """
    Tag = models_ref.Tag

    release_query = Tag.select().where(
        Tag.repository == repo, Tag.tag_kind == Tag.tag_kind.get_id("release")
    )
    if media_type:
        release_query = tag_model.filter_tags_by_media_type(release_query, media_type, models_ref)

    return tag_model.tag_is_alive(release_query, Tag)


def get_releases(repo, model_refs, media_type=None):
    """
    Returns an array of Tag.name for a repo, can filter by media_type.
    """
    return [t.name for t in get_release_objs(repo, model_refs, media_type)]
