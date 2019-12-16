import logging
import json
import uuid

from collections import namedtuple

from flask import session

from data import model
from data.database import db_transaction, ImageStorage, ImageStoragePlacement
from data.registry_model import registry_model
from image.docker.schema2 import EMPTY_LAYER_BLOB_DIGEST

logger = logging.getLogger(__name__)

ManifestLayer = namedtuple("ManifestLayer", ["layer_id", "v1_metadata_string", "db_id"])
_BuilderState = namedtuple(
    "_BuilderState", ["builder_id", "images", "tags", "checksums", "temp_storages"]
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
        repository_ref, _BuilderState(builder_id, {}, {}, {}, []), storage, legacy_signing_key
    )
    builder._save_to_session()
    return builder


def lookup_manifest_builder(repository_ref, builder_id, storage, legacy_signing_key):
    """
    Looks up the manifest builder with the given ID under the specified repository and returns it or
    None if none.
    """
    builder_state_tuple = session.get(_SESSION_KEY)
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
            registry_model.get_repo_tag(self._repository_ref, tag_name, include_legacy_image=True)
            for tag_name in list(self._builder_state.tags.keys())
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
            logger.exception(
                "Exception when trying to parse V1 metadata JSON for layer %s", layer_id
            )
            return None
        except TypeError:
            logger.exception(
                "Exception when trying to parse V1 metadata JSON for layer %s", layer_id
            )
            return None

        # Sanity check that the ID matches the v1 metadata.
        if layer_id != v1_metadata["id"]:
            return None

        # Ensure the parent already exists in the repository.
        parent_id = v1_metadata.get("parent", None)
        parent_image = None

        if parent_id is not None:
            parent_image = model.image.get_repo_image(namespace_name, repo_name, parent_id)
            if parent_image is None:
                return None

        # Check to see if this layer already exists in the repository. If so, we can skip the creation.
        existing_image = registry_model.get_legacy_image(self._repository_ref, layer_id)
        if existing_image is not None:
            self._builder_state.images[layer_id] = existing_image.id
            self._save_to_session()
            return ManifestLayer(layer_id, v1_metadata_string, existing_image.id)

        with db_transaction():
            # Otherwise, create a new legacy image and point a temporary tag at it.
            created = model.image.find_create_or_link_image(
                layer_id, repository, calling_user, {}, location_name
            )
            model.tag.create_temporary_hidden_tag(repository, created, temp_tag_expiration)

            # Save its V1 metadata.
            command_list = v1_metadata.get("container_config", {}).get("Cmd", None)
            command = json.dumps(command_list) if command_list else None

            model.image.set_image_metadata(
                layer_id,
                namespace_name,
                repo_name,
                v1_metadata.get("created"),
                v1_metadata.get("comment"),
                command,
                v1_metadata_string,
                parent=parent_image,
            )

        # Save the changes to the builder.
        self._builder_state.images[layer_id] = created.id
        self._save_to_session()

        return ManifestLayer(layer_id, v1_metadata_string, created.id)

    def lookup_layer(self, layer_id):
        """
        Returns a layer with the given ID under this builder.

        If none exists, returns None.
        """
        if layer_id not in self._builder_state.images:
            return None

        image = model.image.get_image_by_db_id(self._builder_state.images[layer_id])
        if image is None:
            return None

        return ManifestLayer(layer_id, image.v1_json_metadata, image.id)

    def assign_layer_blob(self, layer, blob, computed_checksums):
        """
        Assigns a blob to a layer.
        """
        assert blob
        assert not blob.uploading

        repo_image = model.image.get_image_by_db_id(layer.db_id)
        if repo_image is None:
            return None

        with db_transaction():
            existing_storage = repo_image.storage
            repo_image.storage = blob._db_id
            repo_image.save()

            if existing_storage.uploading:
                self._builder_state.temp_storages.append(existing_storage.id)

        self._builder_state.checksums[layer.layer_id] = computed_checksums
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
        return self._builder_state.checksums.get(layer.layer_id) or []

    def save_precomputed_checksum(self, layer, checksum):
        """
        Saves a precomputed checksum for a layer.
        """
        checksums = self._builder_state.checksums.get(layer.layer_id) or []
        checksums.append(checksum)
        self._builder_state.checksums[layer.layer_id] = checksums
        self._save_to_session()

    def commit_tag_and_manifest(self, tag_name, layer):
        """
        Commits a new tag + manifest for that tag to the repository with the given name, pointing to
        the given layer.
        """
        legacy_image = registry_model.get_legacy_image(self._repository_ref, layer.layer_id)
        if legacy_image is None:
            return None

        tag = registry_model.retarget_tag(
            self._repository_ref, tag_name, legacy_image, self._storage, self._legacy_signing_key
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
        temp_storages = self._builder_state.temp_storages
        for storage_id in temp_storages:
            try:
                storage = ImageStorage.get(id=storage_id)
                if storage.uploading and storage.content_checksum != EMPTY_LAYER_BLOB_DIGEST:
                    # Delete all the placements pointing to the storage.
                    ImageStoragePlacement.delete().where(
                        ImageStoragePlacement.storage == storage
                    ).execute()

                    # Delete the storage.
                    storage.delete_instance()
            except ImageStorage.DoesNotExist:
                pass

        session.pop(_SESSION_KEY, None)

    def _save_to_session(self):
        session[_SESSION_KEY] = self._builder_state
