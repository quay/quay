from __future__ import annotations

import json
import logging
import os
import queue
import threading
from typing import Callable

import bitmath
from peewee import Select, fn

import features
from app import app, proxy_cache_blob_queue, storage
from data import database
from data.database import ImageStorage, ImageStoragePlacement
from data.database import Manifest as ManifestTable
from data.database import ManifestBlob, ManifestChild
from data.database import Tag as TagTable
from data.database import (
    db,
    db_disallow_replica_use,
    db_transaction,
    get_epoch_timestamp_ms,
)
from data.model import (
    ImmutableTagException,
    ManifestDoesNotExist,
    QuotaExceededException,
    RepositoryDoesNotExist,
    TagDoesNotExist,
    namespacequota,
    oci,
)
from data.model.oci.manifest import is_child_manifest
from data.model.proxy_cache import get_proxy_cache_config_for_org
from data.model.quota import (
    QuotaOperation,
    get_namespace_id_from_repository,
    is_blob_alive,
    update_quota,
)
from data.model.repository import create_repository, get_repository
from data.model.storage import (
    get_image_location_for_id,
    get_layer_path,
    get_or_create_blob_with_lock,
    with_blob_lock_or_fallback,
)
from data.registry_model.blobuploader import (
    BlobDigestMismatchException,
    BlobRangeMismatchException,
    BlobTooLargeException,
    BlobUploadException,
    BlobUploadSettings,
    complete_when_uploaded,
    create_blob_upload,
)
from data.registry_model.datatypes import Manifest, RepositoryReference, Tag
from data.registry_model.registry_oci_model import OCIModel
from image.docker.schema1 import (
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
    DockerSchema1Manifest,
)
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_MANIFEST_CONTENT_TYPE
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface
from image.shared.schemas import parse_manifest_from_bytes
from proxy import Proxy, UpstreamAuthError, UpstreamRegistryError
from util.bytes import Bytes

logger = logging.getLogger(__name__)

ACCEPTED_MEDIA_TYPES = [
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
    OCI_IMAGE_INDEX_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
]


class QueueReader:
    """A file-like object that pulls data from a thread-safe Queue."""

    def __init__(self, q, timeout=10):
        self.q = q
        self.buffer = b""
        self.timeout = timeout
        # track EOF state
        self._eof = False

    def read(self, size=-1):
        if self._eof:
            return b""

        if not self.buffer:
            try:
                # Wait for the generator to provide a chunk
                chunk = self.q.get(timeout=self.timeout)
                if chunk is None:  # None is our EOF signal
                    self._eof = True
                    return b""
                self.buffer = chunk
            except queue.Empty:
                raise IOError("Timeout waiting for chunk from stream")

        if size < 0 or size >= len(self.buffer):
            res = self.buffer
            self.buffer = b""
            return res

        res = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return res


class ProxyModel(OCIModel):
    def __init__(self, namespace_name, repo_name, user):
        super().__init__()
        self._config = get_proxy_cache_config_for_org(namespace_name)
        self._user = user
        self._namespace_name = namespace_name

        # when Quay is set up to proxy a whole upstream registry, the
        # upstream_registry_namespace for the proxy cache config will be empty.
        # the given repo then is expected to include both, the upstream namespace
        # and repo. Quay will treat it as a nested repo.
        target_ns = self._config.upstream_registry_namespace
        if target_ns != "" and target_ns is not None:
            repo_name = f"{target_ns}/{repo_name}"

        self._proxy = Proxy(self._config, repo_name)

    def lookup_repository(
        self,
        namespace_name,
        repo_name,
        kind_filter=None,
        raise_on_error=False,
        manifest_ref=None,
        model_cache=None,
    ):
        """
        Looks up and returns a reference to the repository with the given namespace and name, or
        None if none.

        If the repository does not exist and the given manifest_ref exists upstream,
        creates the repository.
        """
        repo = get_repository(namespace_name, repo_name)
        exists = repo is not None
        if exists:
            return RepositoryReference.for_repo_obj(
                repo,
                namespace_name,
                repo_name,
                repo.namespace_user.stripe_id is None if repo else None,
                state=repo.state if repo is not None else None,
            )

        # we only create a repository for images that exist upstream, and if
        # we're not given a manifest reference then we can't check whether the
        # image exists upstream or not, so we refuse to create the repo.
        if manifest_ref is None:
            return None

        try:
            self._proxy.manifest_exists(manifest_ref, ACCEPTED_MEDIA_TYPES)
        except UpstreamRegistryError as e:
            if raise_on_error:
                raise RepositoryDoesNotExist(str(e))
            return None

        visibility = "private" if app.config.get("CREATE_PRIVATE_REPO_ON_PUSH", True) else "public"

        repo = create_repository(
            namespace_name, repo_name, self._user, visibility=visibility, proxy_cache=True
        )
        return RepositoryReference.for_repo_obj(
            repo,
            namespace_name,
            repo_name,
            repo.namespace_user.stripe_id is None if repo else None,
            state=repo.state if repo is not None else None,
        )

    def _check_image_upload_possible_or_prune(
        self, repo_ref: RepositoryReference, upstream_manifest: ManifestInterface
    ) -> None:
        """
        Checks whether the given image fits within the quota size for the namespace
        the repository is part of. If it doesn't, it prunes older tags in the namespace
        by marking them expired which is eventually garbage collected by the gc worker.

        Raises QuotaExceededException if the given tag is larger than the max quota
        allotted for the namespace or if there are not enough tags to prune to free up space.
        """
        if upstream_manifest.is_manifest_list:
            return

        curr_ns_size = namespacequota.get_namespace_size(repo_ref.namespace_name)

        # if quota limit is not set for the namespace, skip auto pruning of images
        quotas = namespacequota.get_namespace_quota_list(repo_ref.namespace_name)
        if quotas:
            # currently only one quota per namespace is supported
            ns_quota_limit = quotas[0].limit_bytes
        else:
            logger.info("No quota configured")
            return

        image_size = upstream_manifest.layers_compressed_size
        if image_size > ns_quota_limit:
            raise QuotaExceededException

        if (curr_ns_size + image_size) <= ns_quota_limit:
            return

        reclaimable_size = 0
        namespace_id = get_namespace_id_from_repository(repo_ref.id)
        tags = oci.tag.get_tag_with_least_lifetime_end_for_ns(repo_ref.namespace_name)
        if tags is not None:
            for tag in tags:
                is_manifest_list = (
                    ManifestChild.select(1).where(ManifestChild.manifest == tag.manifest).exists()
                )

                # Get all the blobs under this manifest. If a manifest list get all the blobs
                # under the child manifests as well
                blobs = None
                if is_manifest_list:
                    blobs = (
                        ImageStorage.select(ImageStorage.id, ImageStorage.image_size)
                        .join(ManifestBlob, on=(ManifestBlob.blob == ImageStorage.id))
                        .join(
                            ManifestChild,
                            on=(ManifestChild.child_manifest == ManifestBlob.manifest),
                        )
                        .where(ManifestChild.manifest == tag.manifest)
                    )
                else:
                    blobs = (
                        ImageStorage.select(ImageStorage.id, ImageStorage.image_size)
                        .join(ManifestBlob, on=(ManifestBlob.blob == ImageStorage.id))
                        .where(ManifestBlob.manifest == tag.manifest)
                    )

                # We remove duplicates within the loop to prevent using "distinct" in the above query.
                # If the blob is not being referenced by an alive tag we'll get that size back
                # when it's GC'd, so add it to the reclaimable total.
                seen_blobs = []
                for blob in blobs:
                    if blob.id not in seen_blobs and not is_blob_alive(
                        namespace_id, tag.id, blob.id
                    ):
                        size = blob.image_size if blob.image_size is not None else 0
                        reclaimable_size = reclaimable_size + size
                    seen_blobs.append(blob.id)

                updated = oci.tag.remove_tag_from_timemachine(
                    tag.repository_id,
                    tag.name,
                    tag.manifest,
                    include_submanifests=is_manifest_list,
                    is_alive=True,
                )

                # If we get enough size back from deleting this tag, exit
                if updated and reclaimable_size > image_size:
                    return

        # if we got here, then there aren't enough tags in the namespace to expire, so we raise an exception
        raise QuotaExceededException

    def lookup_manifest_by_digest(
        self,
        repository_ref,
        manifest_digest,
        allow_dead=False,
        allow_hidden=False,
        require_available=False,
        raise_on_error=True,
    ):
        """
        Looks up the manifest with the given digest under the given repository and returns it or
        None if none.

        If a manifest with the digest does not exist, fetches the manifest upstream
        and creates it with a temp tag.

        Raises QuotaExceededException if the given tag is larger than the max quota
        allotted for the namespace or if there are not enough tags to prune.
        """

        wrapped_manifest = super().lookup_manifest_by_digest(
            repository_ref, manifest_digest, allow_dead=True, require_available=False
        )
        if wrapped_manifest is None:
            try:
                wrapped_manifest, _ = self._create_and_tag_manifest(
                    repository_ref, manifest_digest, self._create_manifest_with_temp_tag
                )
            except (UpstreamRegistryError, ManifestDoesNotExist) as e:
                raise ManifestDoesNotExist(str(e))
            return wrapped_manifest

        db_tag = oci.tag.get_tag_by_manifest_id(repository_ref.id, wrapped_manifest.id)
        if db_tag is None:
            oci.manifest.lookup_manifest(
                repository_ref.id, manifest_digest, allow_dead=True, require_available=True
            )
            db_tag = oci.tag.get_tag_by_manifest_id(repository_ref.id, wrapped_manifest.id)
        existing_tag = Tag.for_tag(
            db_tag, self._legacy_image_id_handler, manifest_row=db_tag.manifest
        )
        new_tag = False
        try:
            tag, new_tag = self._update_manifest_for_tag(
                repository_ref,
                existing_tag,
                existing_tag.manifest,
                manifest_digest,
                self._create_manifest_with_temp_tag,
            )
        except ManifestDoesNotExist:
            raise
        except UpstreamAuthError:
            raise ManifestDoesNotExist("upstream authentication failed")
        except UpstreamRegistryError:
            # when the upstream fetch fails, we only return the tag if
            # it isn't yet expired. note that we don't bump the tag's
            # expiration here either - we only do this when we can ensure
            # the tag exists upstream.
            isplaceholder = wrapped_manifest.internal_manifest_bytes.as_unicode() == ""
            return wrapped_manifest if not existing_tag.expired and not isplaceholder else None

        if tag.expired or not new_tag:
            with db_disallow_replica_use():
                new_expiration = (
                    get_epoch_timestamp_ms() + self._config.expiration_s * 1000
                    if self._config.expiration_s
                    else None
                )
                oci.tag.set_tag_end_ms(db_tag, new_expiration)
                # if the manifest is a child of a manifest list in this repo, renew
                # the parent(s) manifest list tag too.
                # select tag ids by most recent lifetime_end_ms uniquely by name,
                # based on the link between sub-manifest and parent manifest in the
                # manifest link.
                q = (
                    TagTable.select(fn.MAX(TagTable.id).alias("id"))
                    .join(ManifestChild, on=(TagTable.manifest_id == ManifestChild.manifest_id))
                    .where(
                        (ManifestChild.repository_id == repository_ref.id)
                        & (ManifestChild.child_manifest_id == wrapped_manifest.id)
                    )
                    .group_by(TagTable.name)
                )
                tag_ids = [item for item in q]
                TagTable.update(lifetime_end_ms=new_expiration).where(
                    TagTable.id.in_(tag_ids)
                ).execute()

        return super().lookup_manifest_by_digest(
            repository_ref,
            manifest_digest,
            allow_dead=True,
            allow_hidden=True,
            require_available=False,
            raise_on_error=True,
        )

    def get_repo_tag(self, repository_ref, tag_name, raise_on_error=True):
        """
        Returns the latest, *active* tag found in the repository, with the matching
        name or None if none.

        If both manifest and tag don't exist, fetches the manifest with the tag
        from upstream, and creates them both.
        If tag and manifest exists and the manifest is a placeholder, pull the
        upstream manifest and save it locally.

        Raises QuotaExceededException if the given tag is larger than the max quota
        allotted for the namespace or if there are not enough tags to prune.
        """
        db_tag = oci.tag.get_current_tag(repository_ref.id, tag_name)
        existing_tag = Tag.for_tag(db_tag, self._legacy_image_id_handler)
        if existing_tag is None:
            try:
                _, tag = self._create_and_tag_manifest(
                    repository_ref, tag_name, self._create_manifest_and_retarget_tag
                )
            except (UpstreamRegistryError, ManifestDoesNotExist) as e:
                raise TagDoesNotExist(str(e))
            return tag

        new_tag = False
        try:
            tag, new_tag = self._update_manifest_for_tag(
                repository_ref,
                existing_tag,
                existing_tag.manifest,
                tag_name,
                self._create_manifest_and_retarget_tag,
            )
        except ManifestDoesNotExist as e:
            raise TagDoesNotExist(str(e))
        except UpstreamAuthError as e:
            raise TagDoesNotExist(str(e))
        except UpstreamRegistryError:
            # when the upstream fetch fails, we only return the tag if
            # it isn't yet expired. note that we don't bump the tag's
            # expiration here either - we only do this when we can ensure
            # the tag exists upstream.
            isplaceholder = existing_tag.manifest.internal_manifest_bytes.as_unicode() == ""
            return existing_tag if not existing_tag.expired and not isplaceholder else None

        # always bump tag expiration when retrieving tags that both are cached
        # and exist upstream, as a means to auto-renew the cache.
        if tag.expired or not new_tag:
            with db_disallow_replica_use():
                new_expiration = (
                    get_epoch_timestamp_ms() + self._config.expiration_s * 1000
                    if self._config.expiration_s
                    else None
                )
                oci.tag.set_tag_end_ms(db_tag, new_expiration)
            return super().get_repo_tag(repository_ref, tag_name, raise_on_error=True)

        return tag

    def _create_and_tag_manifest(
        self,
        repo_ref: RepositoryReference,
        manifest_ref: str,
        create_manifest_fn: Callable[
            [RepositoryReference, ManifestInterface, str | None], tuple[Manifest | None, Tag | None]
        ],
    ) -> tuple[Manifest | None, Tag | None]:
        """
        Returns the newly created manifest and tag.

        Raises a UpstreamRegistryError exception when the upstream registry
        returns anything other than a 200 status code.
        Raises a ManifestDoesNotExist when the manifest pull from upstream errors,
        or the retrieved manifest is invalid (for docker manifest schema v1).
        """
        self._proxy.manifest_exists(manifest_ref, ACCEPTED_MEDIA_TYPES)
        upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)
        manifest, tag = create_manifest_fn(repo_ref, upstream_manifest, manifest_ref)
        return manifest, tag

    def _rollback_created_blobs_and_quota(self, repo_ref, manifest, created_blobs):
        """
        Rolls back the created blobs and quota for a specified manifest and repository
        in case an error occurs.
        """
        blob_ids = [blob_id for blob_id, _ in created_blobs]
        ManifestBlob.delete().where(
            ManifestBlob.manifest == manifest.id, ManifestBlob.blob << blob_ids
        ).execute()

        # Rollback quota for the blobs we added
        blob_sizes = {blob_id: size for blob_id, size in created_blobs}
        update_quota(repo_ref.id, manifest.id, blob_sizes, QuotaOperation.SUBTRACT)

    def _update_manifest_for_tag(
        self,
        repo_ref: RepositoryReference,
        tag: Tag,
        manifest: Manifest,
        manifest_ref: str,
        create_manifest_fn,
    ) -> tuple[Tag, bool]:
        """
        Updates a placeholder manifest with the given tag name.

        If the manifest is stale, downloads it from the upstream registry
        and creates a new manifest and retargets the tag.

        A manifest is considered stale when the manifest's digest changed in
        the upstream registry.
        A manifest is considered a placeholder when its db entry exists, but
        its manifest_bytes field is empty.

        Raises UpstreamRegistryError if the upstream registry returns anything
        other than 200.
        Raises ManifestDoesNotExist if the given manifest was not found in the
        database.

        Returns a new tag if one was created, or the existing one with a manifest
        freshly out of the database, and a boolean indicating whether the returned
        tag was newly created or not.
        """
        upstream_manifest = None
        upstream_digest = self._proxy.manifest_exists(manifest_ref, ACCEPTED_MEDIA_TYPES)

        # manifest_exists will return an empty/None digest when the upstream
        # registry omits the docker-content-digest header.
        if not upstream_digest:
            upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)
            upstream_digest = upstream_manifest.digest

        logger.debug(f"Found upstream manifest with digest {upstream_digest}, {manifest_ref=}")
        up_to_date = manifest.digest == upstream_digest

        placeholder = manifest.internal_manifest_bytes.as_unicode() == ""
        if up_to_date and not placeholder:
            if tag.expired:
                if upstream_manifest is None:
                    upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)
                self._check_image_upload_possible_or_prune(repo_ref, upstream_manifest)
            return tag, False

        if upstream_manifest is None:
            upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)

        created_blobs = []

        if up_to_date and placeholder:
            self._check_image_upload_possible_or_prune(repo_ref, upstream_manifest)
            # We try to create placeholder blobs and update the manifest
            try:
                created_blobs = self._create_placeholder_blobs(
                    upstream_manifest, manifest.id, repo_ref.id
                )
                with db_disallow_replica_use():
                    with db_transaction():
                        q = ManifestTable.update(
                            manifest_bytes=upstream_manifest.bytes.as_unicode(),
                            layers_compressed_size=upstream_manifest.layers_compressed_size,
                        ).where(ManifestTable.id == manifest.id)
                        q.execute()
                        db_tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest.id)
                        return Tag.for_tag(db_tag, self._legacy_image_id_handler), False

            # If manifest update fails, orphan the already created blobs so they can be picked up
            # by gc
            except Exception as e:
                logger.warning(
                    "Failed to update manifest %s, cleaning up blob references", manifest.id
                )
                # only delete newly created manifest blobs
                if created_blobs:
                    self._rollback_created_blobs_and_quota(repo_ref, manifest, created_blobs)
                raise

        # if we got here, the manifest is stale, so we both create a new manifest
        # entry in the db, and retarget the tag.
        _, tag = create_manifest_fn(repo_ref, upstream_manifest, manifest_ref)
        return tag, True

    def _create_manifest_and_retarget_tag(
        self, repository_ref: RepositoryReference, manifest: ManifestInterface, tag_name: str
    ) -> tuple[Manifest | None, Tag | None]:
        """
        Creates a manifest in the given repository.

        Also checks whether the given image size is within the quota limit
        of the namespace the repository is part of. If not, it prunes older tags.
        Raises QuotaExceededException if there are not enough tags to prune.

        Also creates placeholders for the objects referenced by the manifest.
        For manifest lists, creates placeholder sub-manifests. For regular
        manifests, creates placeholder blobs.

        Placeholder objects will be "filled" with the objects' contents on
        upcoming client requests, as part of the flow described in the OCI
        distribution specification.

        Returns a reference to the (created manifest, tag) or (None, None) on error.
        """
        self._check_image_upload_possible_or_prune(repository_ref, manifest)

        db_manifest = oci.manifest.lookup_manifest(
            repository_ref.id, manifest.digest, allow_dead=True
        )

        if db_manifest is None:
            with db_disallow_replica_use():
                with db_transaction():
                    db_manifest = oci.manifest.create_manifest(
                        repository_ref.id, manifest, raise_on_error=True
                    )
            if db_manifest is None:
                return None, None

        created_blobs = []  # Track ManifestBlob rows created in this attempt
        try:
            # Check if the tag is immutable and if it is, return it immediately
            existing_tag = oci.tag.get_tag(repository_ref.id, tag_name)
            if existing_tag and existing_tag.immutable:
                wrapped_manifest = Manifest.for_manifest(
                    existing_tag.manifest, self._legacy_image_id_handler
                )
                wrapped_tag = Tag.for_tag(
                    existing_tag,
                    self._legacy_image_id_handler,
                    manifest_row=existing_tag.manifest,
                )
                return wrapped_manifest, wrapped_tag

            if not manifest.is_manifest_list:
                created_blobs = self._create_placeholder_blobs(
                    manifest, db_manifest.id, repository_ref.id
                )

            with db_disallow_replica_use():
                with db_transaction():
                    # 0 means a tag never expires - if we get 0 as expiration,
                    # we set the tag expiration to None.
                    expiration = self._config.expiration_s or None
                    try:
                        tag = oci.tag.retarget_tag(
                            tag_name,
                            db_manifest,
                            raise_on_error=True,
                            expiration_seconds=expiration,
                        )
                    except ImmutableTagException:
                        raise
                    if tag is None:
                        return None, None

                    wrapped_manifest = Manifest.for_manifest(
                        db_manifest, self._legacy_image_id_handler
                    )
                    wrapped_tag = Tag.for_tag(
                        tag, self._legacy_image_id_handler, manifest_row=db_manifest
                    )

                    if not manifest.is_manifest_list:
                        return wrapped_manifest, wrapped_tag

                    manifests_to_connect = []
                    for child in manifest.child_manifests(content_retriever=None):
                        m = oci.manifest.lookup_manifest(
                            repository_ref.id, child.digest, allow_dead=True
                        )
                        if m is None:
                            m = oci.manifest.create_manifest(repository_ref.id, child)
                            oci.tag.create_temporary_tag_if_necessary(
                                m, self._config.expiration_s or None
                            )
                        try:
                            ManifestChild.get(manifest=db_manifest.id, child_manifest=m.id)
                        except ManifestChild.DoesNotExist:
                            manifests_to_connect.append(m)

                    oci.manifest.connect_manifests(
                        manifests_to_connect, db_manifest, repository_ref.id
                    )

                    return wrapped_manifest, wrapped_tag
        except Exception as e:
            logger.warning(
                "Failed to create blob/tag for manifest %s, cleaning up: %s", db_manifest.id, e
            )
            # Clean up only the ManifestBlob rows we created in this attempt
            if created_blobs:
                self._rollback_created_blobs_and_quota(repository_ref, db_manifest, created_blobs)
            raise

    def _create_manifest_with_temp_tag(
        self,
        repository_ref: RepositoryReference,
        manifest: ManifestInterface,
        manifest_ref: str | None = None,
    ) -> tuple[Manifest | None, Tag | None]:
        """
        Creates a manifest in the given repository. Also creates placeholders for the
        objects referenced by the manifest. For manifest lists, it creates
        sub manifests entries attached to the manifest list along with a temporary tag.

        Also checks whether the given image size is within the quota limit
        of the namespace the repository is part of. If not, it prunes older tags.
        Raises QuotaExceededException if there are not enough tags to prune.
        """
        self._check_image_upload_possible_or_prune(repository_ref, manifest)
        with db_disallow_replica_use():
            with db_transaction():
                db_manifest = oci.manifest.create_manifest(repository_ref.id, manifest)

        created_blobs = []  # Track ManifestBlob rows created in this attempt
        try:
            if not manifest.is_manifest_list:
                created_blobs = self._create_placeholder_blobs(
                    manifest, db_manifest.id, repository_ref.id
                )
            with db_disallow_replica_use():
                with db_transaction():
                    expiration = self._config.expiration_s or None
                    tag = Tag.for_tag(
                        oci.tag.create_temporary_tag_if_necessary(db_manifest, expiration),
                        self._legacy_image_id_handler,
                    )
                    wrapped_manifest = Manifest.for_manifest(
                        db_manifest, self._legacy_image_id_handler
                    )

                    if not manifest.is_manifest_list:
                        return wrapped_manifest, tag

                    manifests_to_connect = []
                    for child in manifest.child_manifests(content_retriever=None):
                        m = oci.manifest.lookup_manifest(
                            repository_ref.id, child.digest, allow_hidden=True, allow_dead=True
                        )
                        if m is None:
                            m = oci.manifest.create_manifest(repository_ref.id, child)
                        manifests_to_connect.append(m)

                    oci.manifest.connect_manifests(
                        manifests_to_connect, db_manifest, repository_ref.id
                    )
                    for child_manifest in manifests_to_connect:
                        oci.tag.create_temporary_tag_if_necessary(child_manifest, expiration)

                    return wrapped_manifest, tag
        except Exception as e:
            logger.warning(
                "Failed to create blob/tag for manifest %s, cleaning up: %s", db_manifest.id, e
            )
            # Clean up only the ManifestBlob rows we created in this attempt
            if created_blobs:
                self._rollback_created_blobs_and_quota(repository_ref, db_manifest, created_blobs)
            raise

    def _lookup_blob_by_digest(self, repository_ref, blob_digest):
        """
        Fetches the ImageStorage row for a specified blob digest or None if the row doesn't exist
        """
        blob = self._get_shared_storage(blob_digest)
        if blob is None:
            try:
                blob = (
                    ImageStorage.select()
                    .join(ManifestBlob)
                    .where(
                        ManifestBlob.repository_id == repository_ref.id,
                        ImageStorage.content_checksum == blob_digest,
                    )
                    .get()
                )
            except ImageStorage.DoesNotExist:
                return None
        return blob

    def _needs_download(self, repository_ref, blob):
        """
        Returns true if a provided blob needs downloading, or false otherwise.
        """
        try:
            placement = (
                ImageStoragePlacement.select().where(ImageStoragePlacement.storage == blob).get()
            )
        except ImageStoragePlacement.DoesNotExist:
            return True

        try:
            layer_path = get_layer_path(blob)
            location_name = get_image_location_for_id(placement.location_id).name
            if not storage.exists([location_name], layer_path):
                logger.warning(
                    "Blob %s has placements in DB but is missing from storage, re-fetching from upstream",
                    blob.content_checksum,
                )
                return True
        except (IOError, OSError):
            logger.exception(
                "Failed to verify blob %s existence in storage, re-fetching from upstream",
                blob.content_checksum,
            )
            return True

        return False

    def _queue_blob_for_download(self, repo_ref, blob_digest, available_after=5):
        """
        Enqueues the current blob for later download based on the available_after parameter
        if streaming of blob fails.
        """
        username = self._user.username if self._user else None
        try:
            queue_id = proxy_cache_blob_queue.put(
                [self._namespace_name, str(repo_ref.id), blob_digest],
                json.dumps(
                    {
                        "digest": blob_digest,
                        "repo_id": repo_ref.id,
                        "username": username,
                        "namespace": self._namespace_name,
                    }
                ),
                available_after=available_after,
            )
        except Exception as e:
            logger.error("Could not enqueue blob for download: %s", e)

    def get_streaming_proxy_blob(self, namespace_name, repo_name, blob_digest):
        """
        Returns a (generator, content_length) tuple for tee-streaming, or None.
        """

        repo_ref = self.lookup_repository(namespace_name, repo_name)
        if repo_ref is None:
            return None

        blob = self._lookup_blob_by_digest(repo_ref, blob_digest)
        if blob is None or not self._needs_download(repo_ref, blob):
            return None

        # initialize fetch of upstream blob
        try:
            resp = self._proxy.get_blob(blob_digest)
        except UpstreamRegistryError as e:
            logger.warning("Could not fetch blob %s from upstream: %s", blob_digest, e)
            return None

        try:
            content_length = int(resp.headers.get("content-length", -1))
        except (TypeError, ValueError) as e:
            logger.warning(
                "Upstream returned an invalid contentn length for blob %s, setting content-length to -1",
                blob_digest,
            )
            content_length = -1

        # set expiration
        expiration = (
            self._config.expiration_s
            if self._config.expiration_s
            else app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
        )

        # chunk size
        chunk_size = 64 * 1024

        # set blob upload settings
        settings = BlobUploadSettings(
            maximum_blob_size=app.config["MAXIMUM_LAYER_SIZE"],
            committed_blob_expiration=expiration,
        )

        # check if the blob content-length is larger than the max allowed layer size
        max_blob_size = bitmath.parse_string_unsafe(app.config["MAXIMUM_LAYER_SIZE"])
        if content_length != -1 and bitmath.Byte(content_length) > max_blob_size:
            resp.close()
            logger.warning("Blob %s too large, aborting tee stream upload", blob_digest)
            raise BlobTooLargeException(
                uploaded=content_length, max_allowed=int(max_blob_size.bytes)
            )

        def _stop_upload_thread(q: queue.Queue, upload_thread: threading.Thread):
            """
            Helper function that sends an EOF signal for the upload forcing the
            upload thread to exit.
            """
            try:
                q.put(None, timeout=2)
            except queue.Full:
                logger.warning(
                    "Storage queue full for upload thread %s, continuing...", upload_thread.name
                )
                pass
            upload_thread.join(timeout=5)

        def generate():
            """
            Chunks upstream blobs into 64 KiB chunks to be streamed directly to the client and initializes
            a thread to stream data to backend storage simultaneously. If streaming to storage fails, then
            depending on the failure, blob will either be discarded or queued for later pull.

            If upstream blob is avilable, the generator should **always** yield chunks of the upstream blob
            to the requester.
            """
            # buffer up to 16 chunks in memory
            q = queue.Queue(maxsize=16)
            read_fp = QueueReader(q)

            # upload exception list
            upload_exception = []

            # track errors during upload
            upstream_complete = threading.Event()

            # track stream outcomes
            # can be 'complete', 'queue_full' or 'upstream_error'
            stream_outcome = None

            def do_upload():
                """
                Streams the content from upstream to Quay's local storage.
                """
                uploader = None
                try:
                    uploader = create_blob_upload(repo_ref, storage, settings)

                    if uploader is None:
                        upload_exception.append(BlobUploadException("Could not create blob upload"))
                        return

                    uploader.upload_chunk(app.config, read_fp, 0, content_length)

                    if upstream_complete.is_set():
                        uploader.commit_to_blob(app.config, blob_digest)
                    else:
                        uploader.cancel_upload()
                except Exception as e:
                    upload_exception.append(e)
                    if uploader is not None and uploader.committed_blob is None:
                        uploader.cancel_upload()
                finally:
                    database.close_db_filter(None)

            upload_thread = threading.Thread(target=do_upload)
            upload_thread.start()
            logger.debug(
                "Started upload thread %s for blob upload %s", upload_thread.name, blob_digest
            )

            try:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    try:
                        q.put(chunk, timeout=2.0)
                    except queue.Full:
                        stream_outcome = "queue_full"

                    # always yield the chunk
                    yield chunk
                else:
                    if stream_outcome != "queue_full":
                        stream_outcome = "complete"
                        upstream_complete.set()
            except Exception:
                stream_outcome = "upstream_error"
            finally:
                _stop_upload_thread(q, upload_thread)
                resp.close()

                if upload_thread.is_alive():
                    logger.warning(
                        "Upload thread did not finish in time for blob %s, queueing for re-download",
                        blob_digest,
                    )
                    self._queue_blob_for_download(repo_ref, blob_digest, available_after=30)

                elif stream_outcome == "queue_full":
                    logger.warning(
                        "Backend storage too slow, aborting tee-stream upload for %s",
                        blob_digest,
                    )
                    self._queue_blob_for_download(repo_ref, blob_digest)
                elif upload_exception:
                    if stream_outcome == "complete":
                        self._queue_blob_for_download(repo_ref, blob_digest)
                        logger.warning(
                            "Tee-stream failed for blob %s, queueing for later download",
                            blob_digest,
                        )
                    else:
                        logger.warning(
                            "Connection error raised during blob download, aborting tee stream upload for blob %s",
                            blob_digest,
                        )

        return generate(), content_length

    def get_repo_blob_by_digest(self, repository_ref, blob_digest, include_placements=False):
        """
        Returns the blob in the repository with the given digest.

        Returns None for missing blobs and placeholder blobs for the blobs to be streamed directly
        from upstream. Callers should call get_streaming_proxy_blob if blob placement is missing.
        """
        blob = self._lookup_blob_by_digest(repository_ref, blob_digest)
        if blob is None:
            return None

        if self._needs_download(repository_ref, blob):
            return None

        return super().get_repo_blob_by_digest(repository_ref, blob_digest, include_placements)

    def _download_blob(self, repo_ref: RepositoryReference, digest: str) -> None:
        """
        Download blob from upstream registry and perform a monolitic upload to
        Quay's own storage.
        """
        expiration = (
            self._config.expiration_s
            if self._config.expiration_s
            else app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
        )
        settings = BlobUploadSettings(
            maximum_blob_size=app.config["MAXIMUM_LAYER_SIZE"],
            committed_blob_expiration=expiration,
        )
        uploader = create_blob_upload(repo_ref, storage, settings)
        with self._proxy.get_blob(digest) as resp:
            start_offset = 0
            length = int(resp.headers.get("content-length", -1))
            with complete_when_uploaded(uploader):
                uploader.upload_chunk(app.config, resp.raw, start_offset, length)
                uploader.commit_to_blob(app.config, digest)

    def convert_manifest(
        self,
        manifest,
        namespace_name,
        repo_name,
        tag_name,
        allowed_mediatypes,
        storage,
    ):
        return None

    def get_schema1_parsed_manifest(
        self, manifest, namespace_name, repo_name, tag_name, storage, raise_on_error=False
    ):
        if raise_on_error:
            raise ManifestException("manifest is not acceptable by the client")
        return None

    def _create_blob_in_storage(
        self, digest: str, size: int, manifest_id: int, repo_id: int, skip_lock: bool
    ):
        blob = get_or_create_blob_with_lock(digest=digest, image_size=size, skip_lock=skip_lock)
        newly_created = False
        try:
            ManifestBlob.get(manifest_id=manifest_id, blob=blob, repository_id=repo_id)
        except ManifestBlob.DoesNotExist:
            ManifestBlob.create(manifest_id=manifest_id, blob=blob, repository_id=repo_id)
            newly_created = True

            # Add blob sizes if quota management is enabled
            update_quota(repo_id, manifest_id, {blob.id: blob.image_size}, QuotaOperation.ADD)
        return blob, newly_created

    def _create_blob(self, digest: str, size: int, manifest_id: int, repo_id: int):
        return with_blob_lock_or_fallback(
            digest,
            self._create_blob_in_storage,
            digest,
            size,
            manifest_id,
            repo_id,
        )

    def _create_placeholder_blobs(
        self, manifest: ManifestInterface, manifest_id: int, repo_id: int
    ):
        """
        Creates placeholder blobs for the manifest and returns a list of newly created blob IDs with sizes.

        Returns:
            List of tuples (blob_id, size) for ManifestBlob rows created in this call.
        """
        if manifest.is_manifest_list:
            return []

        created_blobs = []  # Track (blob_id, size) for newly created ManifestBlob rows

        if manifest.schema_version == 2:
            blob, newly_created = self._create_blob(
                manifest.config.digest,
                manifest.config.size,
                manifest_id,
                repo_id,
            )
            if newly_created:
                created_blobs.append((blob.id, blob.image_size))

        for layer in manifest.filesystem_layers:
            blob, newly_created = self._create_blob(
                layer.digest, layer.compressed_size, manifest_id, repo_id
            )
            if newly_created:
                created_blobs.append((blob.id, blob.image_size))

            username = self._user.username if self._user else None
            queue_id = proxy_cache_blob_queue.put(
                [self._namespace_name, str(repo_id), str(layer.digest)],
                json.dumps(
                    {
                        "digest": str(layer.digest),
                        "repo_id": repo_id,
                        "username": username,
                        "namespace": self._namespace_name,
                    }
                ),
                available_after=5,
            )

        return created_blobs

    def _upstream_namespace(self, repo: str) -> str:
        upstream_namespace = self._config.upstream_registry_namespace
        if upstream_namespace is None:
            parts = repo.split("/")
            upstream_namespace = parts[0]
        return upstream_namespace

    def _upstream_repo(self, repo: str) -> str:
        upstream_repo_name = repo
        if self._config.upstream_registry_namespace is None:
            parts = repo.split("/")
            if len(parts) == 1:
                return repo
            upstream_repo_name = parts[1]
        return upstream_repo_name

    def _pull_upstream_manifest(self, repo: str, manifest_ref: str) -> ManifestInterface:
        try:
            raw_manifest, content_type = self._proxy.get_manifest(
                manifest_ref, ACCEPTED_MEDIA_TYPES
            )
        except UpstreamAuthError:
            raise
        except UpstreamRegistryError as e:
            if e.status_code == 404:
                raise ManifestDoesNotExist(str(e))
            raise

        upstream_repo_name = self._upstream_repo(repo)
        upstream_namespace = self._upstream_namespace(repo)

        # TODO: do we need the compatibility check from v2._parse_manifest?
        mbytes = Bytes.for_string_or_unicode(raw_manifest)
        manifest = parse_manifest_from_bytes(mbytes, content_type, sparse_manifest_support=True)
        valid = self._validate_schema1_manifest(upstream_namespace, upstream_repo_name, manifest)
        if not valid:
            raise ManifestDoesNotExist("invalid schema 1 manifest")
        return manifest

    def _validate_schema1_manifest(
        self, namespace: str, repo: str, manifest: DockerSchema1Manifest
    ) -> bool:
        if manifest.schema_version != 1:
            return True

        if (
            manifest.namespace == ""
            and features.LIBRARY_SUPPORT
            and namespace == app.config["LIBRARY_NAMESPACE"]
        ):
            pass
        elif manifest.namespace != namespace:
            return False

        if manifest.repo_name != repo:
            return False

        return True
