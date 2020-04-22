import logging
import json
import uuid

from collections import namedtuple

from flask import session

from data import model
from data.database import db_transaction, ImageStorage, ImageStoragePlacement
from data.registry_model import registry_model
from image.docker.schema1 import DockerSchema1ManifestBuilder

logger = logging.getLogger(__name__)

ManifestLayer = namedtuple("ManifestLayer", ["layer_id", "v1_metadata_string"])
_BuilderState = namedtuple(
    "_BuilderState", ["builder_id", "tags", "image_metadata", "image_blobs", "image_checksums"]
)

_SESSION_KEY = "__manifestbuilder"


def create_manifest_builder(repository_ref, storage, legacy_signing_key):
    """
    Creates a new manifest builder for populating manifests under the specified repository and
    returns it.

    Returns None if the builder could not be constructed.
    """
    builder_id = str(uuid.uuid4())
    builder = _ManifestBuilder(
        repository_ref, _BuilderState(builder_id, {}, {}, {}, {}), storage, legacy_signing_key
    )
    builder._save_to_session()
    return builder


def lookup_manifest_builder(repository_ref, builder_id, storage, legacy_signing_key):
    """
    Looks up the manifest builder with the given ID under the specified repository and returns it or
    None if none.
    """
    builder_state_json = session.get(_SESSION_KEY)
    if builder_state_json is None:
        return None

    try:
        builder_state_tuple = json.loads(builder_state_json)
    except ValueError:
        return None

    if builder_state_tuple is None:
        return None

    builder_state = _BuilderState(*builder_state_tuple)
    if builder_state.builder_id != builder_id:
        return None

    return _ManifestBuilder(repository_ref, builder_state, storage, legacy_signing_key)


class _ManifestBuilder(object):
    """
    Helper class which provides an interface for bookkeeping the layers and configuration of
    manifests being constructed.
    """

    def __init__(self, repository_ref, builder_state, storage, legacy_signing_key):
        self._repository_ref = repository_ref
        self._builder_state = builder_state
        self._storage = storage
        self._legacy_signing_key = legacy_signing_key

    @property
    def builder_id(self):
        """
        Returns the unique ID for this builder.
        """
        return self._builder_state.builder_id

    @property
    def committed_tags(self):
        """
        Returns the tags committed by this builder, if any.
        """
        return [
            registry_model.get_repo_tag(self._repository_ref, tag_name)
            for tag_name in self._builder_state.tags.keys()
        ]

    def start_layer(
        self, layer_id, v1_metadata_string, location_name, calling_user, temp_tag_expiration
    ):
        """
        Starts a new layer with the given ID to be placed into a manifest.

        Returns the layer started or None if an error occurred.
        """
        # Ensure the repository still exists.
        repository = model.repository.lookup_repository(self._repository_ref._db_id)
        if repository is None:
            return None

        namespace_name = repository.namespace_user.username
        repo_name = repository.name

        try:
            v1_metadata = json.loads(v1_metadata_string)
        except ValueError:
            logger.warning("Exception when trying to parse V1 metadata JSON for layer %s", layer_id)
            return None
        except TypeError:
            logger.warning("Exception when trying to parse V1 metadata JSON for layer %s", layer_id)
            return None

        # Sanity check that the ID matches the v1 metadata.
        if layer_id != v1_metadata["id"]:
            return None

        # Ensure the parent already exists in the builder.
        parent_id = v1_metadata.get("parent", None)
        parent_image = None

        if parent_id is not None:
            if parent_id not in self._builder_state.image_metadata:
                logger.warning("Missing parent %s for layer %s", parent_id, layer_id)
                return None

        # Add the image to the session.
        self._builder_state.image_metadata[layer_id] = v1_metadata_string
        self._save_to_session()

        return ManifestLayer(layer_id, v1_metadata_string)

    def lookup_layer(self, layer_id):
        """
        Returns a layer with the given ID under this builder.

        If none exists, returns None.
        """
        v1_metadata_string = self._builder_state.image_metadata.get(layer_id)
        if v1_metadata_string is None:
            return None

        return ManifestLayer(layer_id, v1_metadata_string)

    def assign_layer_blob(self, layer, blob, computed_checksums):
        """
        Assigns a blob to a layer.
        """
        assert blob
        assert not blob.uploading

        image_metadata = self._builder_state.image_metadata.get(layer.layer_id)
        if image_metadata is None:
            return None

        self._builder_state.image_checksums[layer.layer_id] = computed_checksums
        self._builder_state.image_blobs[layer.layer_id] = blob.digest
        self._save_to_session()
        return True

    def validate_layer_checksum(self, layer, checksum):
        """
        Returns whether the checksum for a layer matches that specified.
        """
        return checksum in self.get_layer_checksums(layer)

    def get_layer_checksums(self, layer):
        """
        Returns the registered defined for the layer, if any.
        """
        return self._builder_state.image_checksums.get(layer.layer_id) or []

    def save_precomputed_checksum(self, layer, checksum):
        """
        Saves a precomputed checksum for a layer.
        """
        checksums = self._builder_state.image_checksums.get(layer.layer_id) or []
        checksums.append(checksum)
        self._builder_state.image_checksums[layer.layer_id] = checksums
        self._save_to_session()

    def commit_tag_and_manifest(self, tag_name, layer):
        """
        Commits a new tag + manifest for that tag to the repository with the given name, pointing to
        the given layer.
        """
        # Lookup the top layer.
        image_metadata = self._builder_state.image_metadata.get(layer.layer_id)
        if image_metadata is None:
            return None

        # For each layer/image, add it to the manifest builder.
        builder = DockerSchema1ManifestBuilder(
            self._repository_ref.namespace_name, self._repository_ref.name, tag_name
        )

        current_layer_id = layer.layer_id
        while True:
            v1_metadata_string = self._builder_state.image_metadata.get(current_layer_id)
            if v1_metadata_string is None:
                logger.warning("Missing metadata for layer %s", current_layer_id)
                return None

            v1_metadata = json.loads(v1_metadata_string)
            parent_id = v1_metadata.get("parent", None)
            if parent_id is not None and parent_id not in self._builder_state.image_metadata:
                logger.warning("Missing parent for layer %s", current_layer_id)
                return None

            blob_digest = self._builder_state.image_blobs.get(current_layer_id)
            if blob_digest is None:
                logger.warning("Missing blob for layer %s", current_layer_id)
                return None

            builder.add_layer(blob_digest, v1_metadata_string)
            if not parent_id:
                break

            current_layer_id = parent_id

        # Build the manifest.
        manifest_instance = builder.build(self._legacy_signing_key)

        # Target the tag at the manifest.
        manifest, tag = registry_model.create_manifest_and_retarget_tag(
            self._repository_ref, manifest_instance, tag_name, self._storage
        )
        if tag is None:
            return None

        self._builder_state.tags[tag_name] = tag._db_id
        self._save_to_session()
        return tag

    def done(self):
        """
        Marks the manifest builder as complete and disposes of any state.

        This call is optional and it is expected manifest builders will eventually time out if
        unused for an extended period of time.
        """
        session.pop(_SESSION_KEY, None)

    def _save_to_session(self):
        session[_SESSION_KEY] = json.dumps(self._builder_state)
