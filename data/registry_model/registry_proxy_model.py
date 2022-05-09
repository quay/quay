from __future__ import annotations

from typing import Callable

import features
from app import app, storage
from data.database import (
    get_epoch_timestamp_ms,
    db_disallow_replica_use,
    db_transaction,
    Manifest as ManifestTable,
    ImageStorage,
    ImageStoragePlacement,
    ManifestBlob,
    ManifestChild,
)
from data.model import (
    oci,
    namespacequota,
    repository,
    RepositoryDoesNotExist,
    ManifestDoesNotExist,
    TagDoesNotExist,
    QuotaExceededException,
)
from data.model.repository import get_repository, create_repository
from data.model.proxy_cache import get_proxy_cache_config_for_org
from data.registry_model.blobuploader import (
    create_blob_upload,
    complete_when_uploaded,
    BlobTooLargeException,
    BlobRangeMismatchException,
    BlobUploadException,
    BlobDigestMismatchException,
    BlobUploadSettings,
)
from data.registry_model.registry_oci_model import OCIModel
from data.registry_model.datatypes import Manifest, Tag, RepositoryReference
from image.oci import OCI_IMAGE_MANIFEST_CONTENT_TYPE, OCI_IMAGE_INDEX_CONTENT_TYPE
from image.shared import ManifestException
from image.shared.interfaces import ManifestInterface
from image.shared.schemas import parse_manifest_from_bytes
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.docker.schema1 import (
    DockerSchema1Manifest,
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
)
from proxy import Proxy, UpstreamRegistryError
from util.bytes import Bytes


ACCEPTED_MEDIA_TYPES = [
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
    OCI_IMAGE_INDEX_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA1_SIGNED_MANIFEST_CONTENT_TYPE,
]


class ProxyModel(OCIModel):
    def __init__(self, namespace_name, repo_name, user):
        super().__init__()
        self._config = get_proxy_cache_config_for_org(namespace_name)
        self._user = user

        # when Quay is set up to proxy a whole upstream registry, the
        # upstream_registry_namespace for the proxy cache config will be empty.
        # the given repo then is expected to include both, the upstream namespace
        # and repo. Quay will treat it as a nested repo.
        target_ns = self._config.upstream_registry_namespace
        if target_ns != "" and target_ns is not None:
            repo_name = f"{target_ns}/{repo_name}"

        self._proxy = Proxy(self._config, repo_name)

    def lookup_repository(
        self, namespace_name, repo_name, kind_filter=None, raise_on_error=False, manifest_ref=None
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

        repo = create_repository(namespace_name, repo_name, self._user)
        return RepositoryReference.for_repo_obj(
            repo,
            namespace_name,
            repo_name,
            repo.namespace_user.stripe_id is None if repo else None,
            state=repo.state if repo is not None else None,
        )

    def lookup_manifest_by_digest(
        self,
        repository_ref,
        manifest_digest,
        allow_dead=False,
        require_available=False,
        raise_on_error=True,
    ):
        """
        Looks up the manifest with the given digest under the given repository and returns it or
        None if none.

        If a manifest with the digest does not exist, fetches the manifest upstream
        and creates it with a temp tag.
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
        except ManifestDoesNotExist as e:
            raise e
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
                # the parent manifest list tag too.
                parent = ManifestChild.select(ManifestChild.manifest_id).where(
                    (ManifestChild.repository_id == repository_ref.id)
                    & (ManifestChild.child_manifest_id == wrapped_manifest.id)
                )
                parent_tag = oci.tag.get_tag_by_manifest_id(repository_ref.id, parent)
                if parent_tag is not None:
                    oci.tag.set_tag_end_ms(parent_tag, new_expiration)

        return super().lookup_manifest_by_digest(
            repository_ref,
            manifest_digest,
            allow_dead=True,
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

    def _recalculate_repository_size(self, repo_ref: RepositoryReference) -> None:
        if features.QUOTA_MANAGEMENT:
            repository.force_cache_repo_size(repo_ref.id)

    def _enforce_repository_quota(self, repo_ref: RepositoryReference) -> None:
        if features.QUOTA_MANAGEMENT:
            quota = namespacequota.verify_namespace_quota(repo_ref)
            if quota["severity_level"] == "Warning":
                namespacequota.notify_organization_admins(repo_ref, "quota_warning")
            elif quota["severity_level"] == "Reject":
                namespacequota.notify_organization_admins(repo_ref, "quota_error")
                raise QuotaExceededException

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
        self._enforce_repository_quota(repo_ref)
        upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)
        manifest, tag = create_manifest_fn(repo_ref, upstream_manifest, manifest_ref)
        return manifest, tag

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
        upstream_digest = self._proxy.manifest_exists(manifest_ref, ACCEPTED_MEDIA_TYPES)
        up_to_date = manifest.digest == upstream_digest
        placeholder = manifest.internal_manifest_bytes.as_unicode() == ""
        if up_to_date and not placeholder:
            return tag, False

        self._enforce_repository_quota(repo_ref)
        upstream_manifest = self._pull_upstream_manifest(repo_ref.name, manifest_ref)
        if up_to_date and placeholder:
            with db_disallow_replica_use():
                with db_transaction():
                    q = ManifestTable.update(
                        manifest_bytes=upstream_manifest.bytes.as_unicode(),
                        layers_compressed_size=upstream_manifest.layers_compressed_size,
                    ).where(ManifestTable.id == manifest.id)
                    q.execute()
                    self._create_placeholder_blobs(upstream_manifest, manifest.id, repo_ref.id)
                    db_tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest.id)
                    self._recalculate_repository_size(repo_ref)
                    return Tag.for_tag(db_tag, self._legacy_image_id_handler), False

        # if we got here, the manifest is stale, so we both create a new manifest
        # entry in the db, and retarget the tag.
        _, tag = create_manifest_fn(repo_ref, upstream_manifest, manifest_ref)
        return tag, True

    def _create_manifest_and_retarget_tag(
        self, repository_ref: RepositoryReference, manifest: ManifestInterface, tag_name: str
    ) -> tuple[Manifest | None, Tag | None]:
        """
        Creates a manifest in the given repository.

        Also creates placeholders for the objects referenced by the manifest.
        For manifest lists, creates placeholder sub-manifests. For regular
        manifests, creates placeholder blobs.

        Placeholder objects will be "filled" with the objects' contents on
        upcoming client requests, as part of the flow described in the OCI
        distribution specification.

        Returns a reference to the (created manifest, tag) or (None, None) on error.
        """
        with db_disallow_replica_use():
            with db_transaction():
                db_manifest = oci.manifest.lookup_manifest(
                    repository_ref.id, manifest.digest, allow_dead=True
                )
                if db_manifest is None:
                    db_manifest = oci.manifest.create_manifest(
                        repository_ref.id, manifest, raise_on_error=True
                    )
                    self._recalculate_repository_size(repository_ref)
                    if db_manifest is None:
                        return None, None

                # 0 means a tag never expires - if we get 0 as expiration,
                # we set the tag expiration to None.
                expiration = self._config.expiration_s or None
                tag = oci.tag.retarget_tag(
                    tag_name,
                    db_manifest,
                    raise_on_error=True,
                    expiration_seconds=expiration,
                )
                if tag is None:
                    return None, None

                wrapped_manifest = Manifest.for_manifest(db_manifest, self._legacy_image_id_handler)
                wrapped_tag = Tag.for_tag(
                    tag, self._legacy_image_id_handler, manifest_row=db_manifest
                )

                if not manifest.is_manifest_list:
                    self._create_placeholder_blobs(manifest, db_manifest.id, repository_ref.id)
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

                oci.manifest.connect_manifests(manifests_to_connect, db_manifest, repository_ref.id)

                return wrapped_manifest, wrapped_tag

    def _create_manifest_with_temp_tag(
        self,
        repository_ref: RepositoryReference,
        manifest: ManifestInterface,
        manifest_ref: str | None = None,
    ) -> tuple[Manifest | None, Tag | None]:
        with db_disallow_replica_use():
            with db_transaction():
                db_manifest = oci.manifest.create_manifest(repository_ref.id, manifest)
                self._recalculate_repository_size(repository_ref)
                expiration = self._config.expiration_s or None
                tag = Tag.for_tag(
                    oci.tag.create_temporary_tag_if_necessary(db_manifest, expiration),
                    self._legacy_image_id_handler,
                )
                wrapped_manifest = Manifest.for_manifest(db_manifest, self._legacy_image_id_handler)

                if not manifest.is_manifest_list:
                    self._create_placeholder_blobs(manifest, db_manifest.id, repository_ref.id)
                    return wrapped_manifest, tag

                manifests_to_connect = []
                for child in manifest.child_manifests(content_retriever=None):
                    m = oci.manifest.lookup_manifest(repository_ref.id, child.digest)
                    if m is None:
                        m = oci.manifest.create_manifest(repository_ref.id, child)
                    manifests_to_connect.append(m)

                oci.manifest.connect_manifests(manifests_to_connect, db_manifest, repository_ref.id)
                for db_manifest in manifests_to_connect:
                    oci.tag.create_temporary_tag_if_necessary(db_manifest, expiration)

                return wrapped_manifest, tag

    def get_repo_blob_by_digest(self, repository_ref, blob_digest, include_placements=False):
        """
        Returns the blob in the repository with the given digest.

        If the blob is a placeholder, downloads it from the upstream registry.
        Placeholder blobs are blobs that don't yet have a ImageStoragePlacement
        associated with it.

        Note that there may be multiple records in the same repository for the same blob digest, so
        the return value of this function may change.
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

        try:
            ImageStoragePlacement.select().where(ImageStoragePlacement.storage == blob).get()
        except ImageStoragePlacement.DoesNotExist:
            try:
                self._download_blob(repository_ref, blob_digest)
            except BlobDigestMismatchException:
                raise UpstreamRegistryError("blob digest mismatch")
            except BlobTooLargeException as e:
                raise UpstreamRegistryError(f"blob too large, max allowed is {e.max_allowed}")
            except BlobRangeMismatchException:
                raise UpstreamRegistryError("range mismatch")
            except BlobUploadException:
                raise UpstreamRegistryError("invalid blob upload")

        return super().get_repo_blob_by_digest(repository_ref, blob_digest, include_placements)

    def _download_blob(self, repo_ref: RepositoryReference, digest: str) -> int:
        """
        Download blob from upstream registry and perform a monolitic upload to
        Quay's own storage.
        """
        self._enforce_repository_quota(repo_ref)
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
        self._recalculate_repository_size(repo_ref)

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

    def _create_blob(self, digest: str, size: int, manifest_id: int, repo_id: int):
        try:
            blob = ImageStorage.get(content_checksum=digest)
        except ImageStorage.DoesNotExist:
            # TODO: which size should we really be setting here?
            blob = ImageStorage.create(
                content_checksum=digest, image_size=size, compressed_size=size
            )
        try:
            ManifestBlob.get(manifest_id=manifest_id, blob=blob, repository_id=repo_id)
        except ManifestBlob.DoesNotExist:
            ManifestBlob.create(manifest_id=manifest_id, blob=blob, repository_id=repo_id)
        return blob

    def _create_placeholder_blobs(
        self, manifest: ManifestInterface, manifest_id: int, repo_id: int
    ):
        if manifest.is_manifest_list:
            return

        if manifest.schema_version == 2:
            self._create_blob(
                manifest.config.digest,
                manifest.config.size,
                manifest_id,
                repo_id,
            )

        for layer in manifest.filesystem_layers:
            self._create_blob(layer.digest, layer.compressed_size, manifest_id, repo_id)

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
        except UpstreamRegistryError as e:
            raise ManifestDoesNotExist(str(e))

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
