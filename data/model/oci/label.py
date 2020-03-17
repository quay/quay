import logging


from data.model import InvalidLabelKeyException, InvalidMediaTypeException, DataModelException
from data.database import (
    Label,
    Manifest,
    TagManifestLabel,
    MediaType,
    LabelSourceType,
    db_transaction,
    ManifestLabel,
    TagManifestLabelMap,
    TagManifestToManifest,
    Repository,
    TagManifest,
)
from data.text import prefix_search
from util.validation import validate_label_key
from util.validation import is_json

logger = logging.getLogger(__name__)


def list_manifest_labels(manifest_id, prefix_filter=None):
    """
    Lists all labels found on the given manifest, with an optional filter by key prefix.
    """
    query = (
        Label.select(Label, MediaType)
        .join(MediaType)
        .switch(Label)
        .join(LabelSourceType)
        .switch(Label)
        .join(ManifestLabel)
        .where(ManifestLabel.manifest == manifest_id)
    )

    if prefix_filter is not None:
        query = query.where(prefix_search(Label.key, prefix_filter))

    return query


def get_manifest_label(label_uuid, manifest):
    """
    Retrieves the manifest label on the manifest with the given UUID or None if none.
    """
    try:
        return (
            Label.select(Label, LabelSourceType)
            .join(LabelSourceType)
            .where(Label.uuid == label_uuid)
            .switch(Label)
            .join(ManifestLabel)
            .where(ManifestLabel.manifest == manifest)
            .get()
        )
    except Label.DoesNotExist:
        return None


def create_manifest_label(manifest_id, key, value, source_type_name, media_type_name=None):
    """
    Creates a new manifest label on a specific tag manifest.
    """
    if not key:
        raise InvalidLabelKeyException("Missing key on label")

    # Note that we don't prevent invalid label names coming from the manifest to be stored, as Docker
    # does not currently prevent them from being put into said manifests.
    if source_type_name != "manifest" and not validate_label_key(key):
        raise InvalidLabelKeyException("Key `%s` is invalid or reserved" % key)

    # Find the matching media type. If none specified, we infer.
    if media_type_name is None:
        media_type_name = "text/plain"
        if is_json(value):
            media_type_name = "application/json"

    try:
        media_type_id = Label.media_type.get_id(media_type_name)
    except MediaType.DoesNotExist:
        raise InvalidMediaTypeException()

    source_type_id = Label.source_type.get_id(source_type_name)

    # Ensure the manifest exists.
    try:
        manifest = (
            Manifest.select(Manifest, Repository)
            .join(Repository)
            .where(Manifest.id == manifest_id)
            .get()
        )
    except Manifest.DoesNotExist:
        return None

    repository = manifest.repository

    with db_transaction():
        label = Label.create(
            key=key, value=value, source_type=source_type_id, media_type=media_type_id
        )
        manifest_label = ManifestLabel.create(
            manifest=manifest_id, label=label, repository=repository
        )

    return label


def delete_manifest_label(label_uuid, manifest):
    """
    Deletes the manifest label on the tag manifest with the given ID.

    Returns the label deleted or None if none.
    """
    # Find the label itself.
    label = get_manifest_label(label_uuid, manifest)
    if label is None:
        return None

    if not label.source_type.mutable:
        raise DataModelException("Cannot delete immutable label")

    # Delete the mapping records and label.
    # TODO: Remove this code once the TagManifest table is gone.
    with db_transaction():
        (TagManifestLabelMap.delete().where(TagManifestLabelMap.label == label).execute())

        deleted_count = TagManifestLabel.delete().where(TagManifestLabel.label == label).execute()
        if deleted_count != 1:
            logger.warning("More than a single label deleted for matching label %s", label_uuid)

        deleted_count = ManifestLabel.delete().where(ManifestLabel.label == label).execute()
        if deleted_count != 1:
            logger.warning("More than a single label deleted for matching label %s", label_uuid)

        label.delete_instance(recursive=False)
        return label
