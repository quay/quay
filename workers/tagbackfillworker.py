import logging
import logging.config

import time

from peewee import JOIN, fn, IntegrityError

from app import app
from data.database import (
    UseThenDisconnect,
    TagToRepositoryTag,
    RepositoryTag,
    TagManifestToManifest,
    Tag,
    TagManifest,
    TagManifestToManifest,
    Image,
    Manifest,
    TagManifestLabel,
    ManifestLabel,
    TagManifestLabelMap,
    Repository,
    db_transaction,
)
from data.model import DataModelException
from data.model.image import get_parent_images
from data.model.tag import populate_manifest
from data.model.blob import get_repo_blob_by_digest, BlobDoesNotExist
from data.model.user import get_namespace_user
from data.registry_model import pre_oci_model
from data.registry_model.datatypes import Tag as TagDataType
from image.docker.schema1 import (
    DockerSchema1Manifest,
    ManifestException,
    ManifestInterface,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
    MalformedSchema1Manifest,
)

from workers.worker import Worker
from util.bytes import Bytes
from util.log import logfile_path
from util.migrate.allocator import yield_random_entries


logger = logging.getLogger(__name__)


WORKER_TIMEOUT = app.config.get("BACKFILL_TAGS_TIMEOUT", 6000)


class BrokenManifest(ManifestInterface):
    """ Implementation of the ManifestInterface for "broken" manifests. This allows us to add the
      new manifest row while not adding any additional rows for it.
  """

    def __init__(self, digest, payload):
        self._digest = digest
        self._payload = Bytes.for_string_or_unicode(payload)

    @property
    def digest(self):
        return self._digest

    @property
    def media_type(self):
        return DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE

    @property
    def manifest_dict(self):
        return {}

    @property
    def bytes(self):
        return self._payload

    def get_layers(self, content_retriever):
        return None

    def get_legacy_image_ids(self, cr):
        return []

    def get_leaf_layer_v1_image_id(self, cr):
        return None

    @property
    def blob_digests(self):
        return []

    @property
    def local_blob_digests(self):
        return []

    def get_blob_digests_for_translation(self):
        return []

    def validate(self, content_retriever):
        pass

    def child_manifests(self, lookup_manifest_fn):
        return None

    def get_manifest_labels(self, lookup_config_fn):
        return {}

    def unsigned(self):
        return self

    def generate_legacy_layers(self, images_map, lookup_config_fn):
        return None

    def get_schema1_manifest(self, namespace_name, repo_name, tag_name, lookup_fn):
        return self

    @property
    def schema_version(self):
        return 1

    @property
    def layers_compressed_size(self):
        return None

    @property
    def is_manifest_list(self):
        return False

    @property
    def has_legacy_image(self):
        return False

    def get_requires_empty_layer_blob(self, content_retriever):
        return False

    def convert_manifest(
        self, allowed_mediatypes, namespace_name, repo_name, tag_name, content_retriever
    ):
        return None


class TagBackfillWorker(Worker):
    def __init__(self, namespace_filter=None):
        super(TagBackfillWorker, self).__init__()
        self._namespace_filter = namespace_filter

        self.add_operation(self._backfill_tags, WORKER_TIMEOUT)

    def _filter(self, query):
        if self._namespace_filter:
            logger.info("Filtering by namespace `%s`", self._namespace_filter)
            namespace_user = get_namespace_user(self._namespace_filter)
            query = query.join(Repository).where(Repository.namespace_user == namespace_user)

        return query

    def _candidates_to_backfill(self):
        def missing_tmt_query():
            return (
                self._filter(RepositoryTag.select())
                .join(TagToRepositoryTag, JOIN.LEFT_OUTER)
                .where(TagToRepositoryTag.id >> None, RepositoryTag.hidden == False)
            )

        min_id = self._filter(RepositoryTag.select(fn.Min(RepositoryTag.id))).scalar()
        max_id = self._filter(RepositoryTag.select(fn.Max(RepositoryTag.id))).scalar()

        logger.info("Found candidate range %s-%s", min_id, max_id)

        iterator = yield_random_entries(missing_tmt_query, RepositoryTag.id, 1000, max_id, min_id,)

        return iterator

    def _backfill_tags(self):
        with UseThenDisconnect(app.config):
            iterator = self._candidates_to_backfill()
            if iterator is None:
                logger.debug("Found no additional tags to backfill")
                time.sleep(10000)
                return None

            for candidate, abt, _ in iterator:
                if not backfill_tag(candidate):
                    logger.info("Another worker pre-empted us for tag: %s", candidate.id)
                    abt.set()


def lookup_map_row(repositorytag):
    try:
        TagToRepositoryTag.get(repository_tag=repositorytag)
        return True
    except TagToRepositoryTag.DoesNotExist:
        return False


def backfill_tag(repositorytag):
    logger.info("Backfilling tag %s", repositorytag.id)

    # Ensure that a mapping row doesn't already exist. If it does, nothing more to do.
    if lookup_map_row(repositorytag):
        return False

    # Grab the manifest for the RepositoryTag, backfilling as necessary.
    manifest_id = _get_manifest_id(repositorytag)
    if manifest_id is None:
        return True

    lifetime_start_ms = (
        repositorytag.lifetime_start_ts * 1000
        if repositorytag.lifetime_start_ts is not None
        else None
    )
    lifetime_end_ms = (
        repositorytag.lifetime_end_ts * 1000 if repositorytag.lifetime_end_ts is not None else None
    )

    # Create the new Tag.
    with db_transaction():
        if lookup_map_row(repositorytag):
            return False

        try:
            created = Tag.create(
                name=repositorytag.name,
                repository=repositorytag.repository,
                lifetime_start_ms=lifetime_start_ms,
                lifetime_end_ms=lifetime_end_ms,
                reversion=repositorytag.reversion,
                manifest=manifest_id,
                tag_kind=Tag.tag_kind.get_id("tag"),
            )

            TagToRepositoryTag.create(
                tag=created, repository_tag=repositorytag, repository=repositorytag.repository
            )
        except IntegrityError:
            logger.exception("Could not create tag for repo tag `%s`", repositorytag.id)
            return False

    logger.info("Backfilled tag %s", repositorytag.id)
    return True


def lookup_manifest_map_row(tag_manifest):
    try:
        TagManifestToManifest.get(tag_manifest=tag_manifest)
        return True
    except TagManifestToManifest.DoesNotExist:
        return False


def _get_manifest_id(repositorytag):
    repository_tag_datatype = TagDataType.for_repository_tag(repositorytag)

    # Retrieve the TagManifest for the RepositoryTag, backfilling if necessary.
    with db_transaction():
        manifest_datatype = None

        try:
            manifest_datatype = pre_oci_model.get_manifest_for_tag(
                repository_tag_datatype, backfill_if_necessary=True
            )
        except MalformedSchema1Manifest:
            logger.exception("Error backfilling manifest for tag `%s`", repositorytag.id)

        if manifest_datatype is None:
            logger.error("Could not load or backfill manifest for tag `%s`", repositorytag.id)

            # Create a broken manifest for the tag.
            tag_manifest = TagManifest.create(
                tag=repositorytag, digest="BROKEN-%s" % repositorytag.id, json_data="{}"
            )
        else:
            # Retrieve the new-style Manifest for the TagManifest, if any.
            try:
                tag_manifest = TagManifest.get(id=manifest_datatype._db_id)
            except TagManifest.DoesNotExist:
                logger.exception("Could not find tag manifest")
                return None

    try:
        found = TagManifestToManifest.get(tag_manifest=tag_manifest).manifest

        # Verify that the new-style manifest has the same contents as the old-style manifest.
        # If not, update and then return. This is an extra check put in place to ensure unicode
        # manifests have been correctly copied.
        if found.manifest_bytes != tag_manifest.json_data:
            logger.warning("Fixing manifest `%s`", found.id)
            found.manifest_bytes = tag_manifest.json_data
            found.save()

        return found.id
    except TagManifestToManifest.DoesNotExist:
        # Could not find the new style manifest, so backfill.
        _backfill_manifest(tag_manifest)

    # Try to retrieve the manifest again, since we've performed a backfill.
    try:
        return TagManifestToManifest.get(tag_manifest=tag_manifest).manifest_id
    except TagManifestToManifest.DoesNotExist:
        return None


def _backfill_manifest(tag_manifest):
    logger.info("Backfilling manifest for tag manifest %s", tag_manifest.id)

    # Ensure that a mapping row doesn't already exist. If it does, we've been preempted.
    if lookup_manifest_map_row(tag_manifest):
        return False

    # Parse the manifest. If we cannot parse, then we treat the manifest as broken and just emit it
    # without additional rows or data, as it will eventually not be useful.
    is_broken = False
    try:
        manifest = DockerSchema1Manifest(
            Bytes.for_string_or_unicode(tag_manifest.json_data), validate=False
        )
    except ManifestException:
        logger.exception("Exception when trying to parse manifest %s", tag_manifest.id)
        manifest = BrokenManifest(tag_manifest.digest, tag_manifest.json_data)
        is_broken = True

    # Lookup the storages for the digests.
    root_image = tag_manifest.tag.image
    repository = tag_manifest.tag.repository

    image_storage_id_map = {root_image.storage.content_checksum: root_image.storage.id}

    try:
        parent_images = get_parent_images(
            repository.namespace_user.username, repository.name, root_image
        )
    except DataModelException:
        logger.exception(
            "Exception when trying to load parent images for manifest `%s`", tag_manifest.id
        )
        parent_images = {}
        is_broken = True

    for parent_image in parent_images:
        image_storage_id_map[parent_image.storage.content_checksum] = parent_image.storage.id

    # Ensure that all the expected blobs have been found. If not, we lookup the blob under the repo
    # and add its storage ID. If the blob is not found, we mark the manifest as broken.
    storage_ids = set()
    try:
        for blob_digest in manifest.get_blob_digests_for_translation():
            if blob_digest in image_storage_id_map:
                storage_ids.add(image_storage_id_map[blob_digest])
            else:
                logger.debug(
                    "Blob `%s` not found in images for manifest `%s`; checking repo",
                    blob_digest,
                    tag_manifest.id,
                )
                try:
                    blob_storage = get_repo_blob_by_digest(
                        repository.namespace_user.username, repository.name, blob_digest
                    )
                    storage_ids.add(blob_storage.id)
                except BlobDoesNotExist:
                    logger.debug(
                        "Blob `%s` not found in repo for manifest `%s`",
                        blob_digest,
                        tag_manifest.id,
                    )
                    is_broken = True
    except MalformedSchema1Manifest:
        logger.warning("Found malformed schema 1 manifest during blob backfill")
        is_broken = True

    with db_transaction():
        # Re-retrieve the tag manifest to ensure it still exists and we're pointing at the correct tag.
        try:
            tag_manifest = TagManifest.get(id=tag_manifest.id)
        except TagManifest.DoesNotExist:
            return True

        # Ensure it wasn't already created.
        if lookup_manifest_map_row(tag_manifest):
            return False

        # Check for a pre-existing manifest matching the digest in the repository. This can happen
        # if we've already created the manifest row (typically for tag reverision).
        try:
            manifest_row = Manifest.get(
                digest=manifest.digest, repository=tag_manifest.tag.repository
            )
        except Manifest.DoesNotExist:
            # Create the new-style rows for the manifest.
            try:
                manifest_row = populate_manifest(
                    tag_manifest.tag.repository, manifest, tag_manifest.tag.image, storage_ids
                )
            except IntegrityError:
                # Pre-empted.
                return False

        # Create the mapping row. If we find another was created for this tag manifest in the
        # meantime, then we've been preempted.
        try:
            TagManifestToManifest.create(
                tag_manifest=tag_manifest, manifest=manifest_row, broken=is_broken
            )
        except IntegrityError:
            return False

    # Backfill any labels on the manifest.
    _backfill_labels(tag_manifest, manifest_row, repository)
    return True


def _backfill_labels(tag_manifest, manifest, repository):
    tmls = list(TagManifestLabel.select().where(TagManifestLabel.annotated == tag_manifest))
    if not tmls:
        return

    for tag_manifest_label in tmls:
        label = tag_manifest_label.label
        try:
            TagManifestLabelMap.get(tag_manifest_label=tag_manifest_label)
            continue
        except TagManifestLabelMap.DoesNotExist:
            pass

        try:
            manifest_label = ManifestLabel.create(
                manifest=manifest, label=label, repository=repository
            )
            TagManifestLabelMap.create(
                manifest_label=manifest_label,
                tag_manifest_label=tag_manifest_label,
                label=label,
                manifest=manifest,
                tag_manifest=tag_manifest_label.annotated,
            )
        except IntegrityError:
            continue


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    if (
        not app.config.get("BACKFILL_TAGS", False)
        and app.config.get("V3_UPGRADE_MODE") != "background"
    ):
        logger.debug("Tag backfill disabled; skipping")
        while True:
            time.sleep(100000)

    worker = TagBackfillWorker(app.config.get("BACKFILL_TAGS_NAMESPACE"))
    worker.start()
