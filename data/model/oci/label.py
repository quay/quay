import logging

from data import model
from data.database import (
    Label,
    LabelSourceType,
    Manifest,
    ManifestLabel,
    MediaType,
    Repository,
    db_transaction,
)
from data.model import (
    DataModelException,
    InvalidLabelKeyException,
    InvalidMediaTypeException,
)
from data.model.oci.tag import has_immutable_tags_for_manifest
from data.text import prefix_search
from util.validation import is_json, validate_label_key

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


def create_manifest_label(manifest_id, key, value, source_type_name, media_type_name=None, raise_on_error=False):
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
        if raise_on_error:
            raise model.ManifestDoesNotExist("Cannot create label '%s=%s', requested manifest does not exist" % (key, value))
        return None
    
    # raise TagImmutableException() if manifest has immutable tags
    if has_immutable_tags_for_manifest(manifest.id):
        if raise_on_error:
            raise model.TagImmutableException("Cannot add label to manifest %s which has immutable tags" % manifest.digest)
        else:
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


def delete_manifest_label(label_uuid, manifest, raise_on_error=False):
    """
    Deletes the manifest label on the tag manifest with the given ID.

    Returns the label deleted or None if none.
    """
    # Find the label itself.
    label = get_manifest_label(label_uuid, manifest)
    if label is None:
        return None
    
    if has_immutable_tags_for_manifest(manifest):
        if raise_on_error:
            raise model.TagImmutableException("Cannot delete label from manifest which has immutable tags")
        else:
            return None

    if not label.source_type.mutable:
        if raise_on_error:
            raise DataModelException("Cannot delete immutable label")
        else:
            return None

    # Delete the mapping records and label.
    with db_transaction():
        deleted_count = ManifestLabel.delete().where(ManifestLabel.label == label).execute()
        if deleted_count != 1:
            logger.warning("More than a single label deleted for matching label %s", label_uuid)

        label.delete_instance(recursive=False)
        return label
