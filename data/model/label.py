import logging

from cachetools.func import lru_cache

from data.database import (
    Label,
    TagManifestLabel,
    MediaType,
    LabelSourceType,
    db_transaction,
    ManifestLabel,
    TagManifestLabelMap,
    TagManifestToManifest,
)
from data.model import InvalidLabelKeyException, InvalidMediaTypeException, DataModelException
from data.text import prefix_search
from util.validation import validate_label_key
from util.validation import is_json

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_label_source_types():
    source_type_map = {}
    for kind in LabelSourceType.select():
        source_type_map[kind.id] = kind.name
        source_type_map[kind.name] = kind.id

    return source_type_map


@lru_cache(maxsize=1)
def get_media_types():
    media_type_map = {}
    for kind in MediaType.select():
        media_type_map[kind.id] = kind.name
        media_type_map[kind.name] = kind.id

    return media_type_map


def _get_label_source_type_id(name):
    kinds = get_label_source_types()
    return kinds[name]


def _get_media_type_id(name):
    kinds = get_media_types()
    return kinds[name]


def create_manifest_label(tag_manifest, key, value, source_type_name, media_type_name=None):
    """ Creates a new manifest label on a specific tag manifest. """
    if not key:
        raise InvalidLabelKeyException()

    # Note that we don't prevent invalid label names coming from the manifest to be stored, as Docker
    # does not currently prevent them from being put into said manifests.
    if not validate_label_key(key) and source_type_name != "manifest":
        raise InvalidLabelKeyException()

    # Find the matching media type. If none specified, we infer.
    if media_type_name is None:
        media_type_name = "text/plain"
        if is_json(value):
            media_type_name = "application/json"

    media_type_id = _get_media_type_id(media_type_name)
    if media_type_id is None:
        raise InvalidMediaTypeException()

    source_type_id = _get_label_source_type_id(source_type_name)

    with db_transaction():
        label = Label.create(
            key=key, value=value, source_type=source_type_id, media_type=media_type_id
        )
        tag_manifest_label = TagManifestLabel.create(
            annotated=tag_manifest, label=label, repository=tag_manifest.tag.repository
        )
        try:
            mapping_row = TagManifestToManifest.get(tag_manifest=tag_manifest)
            if mapping_row.manifest:
                manifest_label = ManifestLabel.create(
                    manifest=mapping_row.manifest,
                    label=label,
                    repository=tag_manifest.tag.repository,
                )
                TagManifestLabelMap.create(
                    manifest_label=manifest_label,
                    tag_manifest_label=tag_manifest_label,
                    label=label,
                    manifest=mapping_row.manifest,
                    tag_manifest=tag_manifest,
                )
        except TagManifestToManifest.DoesNotExist:
            pass

    return label


def list_manifest_labels(tag_manifest, prefix_filter=None):
    """ Lists all labels found on the given tag manifest. """
    query = (
        Label.select(Label, MediaType)
        .join(MediaType)
        .switch(Label)
        .join(LabelSourceType)
        .switch(Label)
        .join(TagManifestLabel)
        .where(TagManifestLabel.annotated == tag_manifest)
    )

    if prefix_filter is not None:
        query = query.where(prefix_search(Label.key, prefix_filter))

    return query


def get_manifest_label(label_uuid, tag_manifest):
    """ Retrieves the manifest label on the tag manifest with the given ID. """
    try:
        return (
            Label.select(Label, LabelSourceType)
            .join(LabelSourceType)
            .where(Label.uuid == label_uuid)
            .switch(Label)
            .join(TagManifestLabel)
            .where(TagManifestLabel.annotated == tag_manifest)
            .get()
        )
    except Label.DoesNotExist:
        return None


def delete_manifest_label(label_uuid, tag_manifest):
    """ Deletes the manifest label on the tag manifest with the given ID. """

    # Find the label itself.
    label = get_manifest_label(label_uuid, tag_manifest)
    if label is None:
        return None

    if not label.source_type.mutable:
        raise DataModelException("Cannot delete immutable label")

    # Delete the mapping records and label.
    (TagManifestLabelMap.delete().where(TagManifestLabelMap.label == label).execute())

    deleted_count = TagManifestLabel.delete().where(TagManifestLabel.label == label).execute()
    if deleted_count != 1:
        logger.warning("More than a single label deleted for matching label %s", label_uuid)

    deleted_count = ManifestLabel.delete().where(ManifestLabel.label == label).execute()
    if deleted_count != 1:
        logger.warning("More than a single label deleted for matching label %s", label_uuid)

    label.delete_instance(recursive=False)
    return label
