import logging

from calendar import timegm
from datetime import datetime
from uuid import uuid4

from peewee import IntegrityError, JOIN, fn
from data.model import (
    image,
    storage,
    db_transaction,
    DataModelException,
    _basequery,
    InvalidManifestException,
    TagAlreadyCreatedException,
    StaleTagException,
    config,
)
from data.database import (
    RepositoryTag,
    Repository,
    Image,
    ImageStorage,
    Namespace,
    TagManifest,
    RepositoryNotification,
    Label,
    TagManifestLabel,
    get_epoch_timestamp,
    db_for_update,
    Manifest,
    ManifestLabel,
    ManifestBlob,
    ManifestLegacyImage,
    TagManifestToManifest,
    TagManifestLabelMap,
    TagToRepositoryTag,
    Tag,
    get_epoch_timestamp_ms,
)
from util.timedeltastring import convert_to_timedelta


logger = logging.getLogger(__name__)


def get_max_id_for_sec_scan():
    """
    Gets the maximum id for security scanning.
    """
    return RepositoryTag.select(fn.Max(RepositoryTag.id)).scalar()


def get_min_id_for_sec_scan(version):
    """
    Gets the minimum id for a security scanning.
    """
    return _tag_alive(
        RepositoryTag.select(fn.Min(RepositoryTag.id))
        .join(Image)
        .where(Image.security_indexed_engine < version)
    ).scalar()


def get_tag_pk_field():
    """
    Returns the primary key for Image DB model.
    """
    return RepositoryTag.id


def get_tags_images_eligible_for_scan(clair_version):
    Parent = Image.alias()
    ParentImageStorage = ImageStorage.alias()

    return _tag_alive(
        RepositoryTag.select(Image, ImageStorage, Parent, ParentImageStorage, RepositoryTag)
        .join(Image, on=(RepositoryTag.image == Image.id))
        .join(ImageStorage, on=(Image.storage == ImageStorage.id))
        .switch(Image)
        .join(Parent, JOIN.LEFT_OUTER, on=(Image.parent == Parent.id))
        .join(ParentImageStorage, JOIN.LEFT_OUTER, on=(ParentImageStorage.id == Parent.storage))
        .where(RepositoryTag.hidden == False)
        .where(Image.security_indexed_engine < clair_version)
    )


def _tag_alive(query, now_ts=None):
    if now_ts is None:
        now_ts = get_epoch_timestamp()
    return query.where(
        (RepositoryTag.lifetime_end_ts >> None) | (RepositoryTag.lifetime_end_ts > now_ts)
    )


def filter_has_repository_event(query, event):
    """
    Filters the query by ensuring the repositories returned have the given event.
    """
    return (
        query.join(Repository)
        .join(RepositoryNotification)
        .where(RepositoryNotification.event == event)
    )


def filter_tags_have_repository_event(query, event):
    """
    Filters the query by ensuring the repository tags live in a repository that has the given event.

    Also returns the image storage for the tag's image and orders the results by lifetime_start_ts.
    """
    query = filter_has_repository_event(query, event)
    query = query.switch(RepositoryTag).join(Image).join(ImageStorage)
    query = query.switch(RepositoryTag).order_by(RepositoryTag.lifetime_start_ts.desc())
    return query


_MAX_SUB_QUERIES = 100
_MAX_IMAGE_LOOKUP_COUNT = 500


def get_matching_tags_for_images(
    image_pairs, filter_images=None, filter_tags=None, selections=None
):
    """
    Returns all tags that contain the images with the given docker_image_id and storage_uuid, as
    specified as an iterable of pairs.
    """
    if not image_pairs:
        return []

    image_pairs_set = set(image_pairs)

    # Find all possible matching image+storages.
    images = []

    while image_pairs:
        image_pairs_slice = image_pairs[:_MAX_IMAGE_LOOKUP_COUNT]

        ids = [pair[0] for pair in image_pairs_slice]
        uuids = [pair[1] for pair in image_pairs_slice]

        images_query = (
            Image.select(Image.id, Image.docker_image_id, Image.ancestors, ImageStorage.uuid)
            .join(ImageStorage)
            .where(Image.docker_image_id << ids, ImageStorage.uuid << uuids)
            .switch(Image)
        )

        if filter_images is not None:
            images_query = filter_images(images_query)

        images.extend(list(images_query))
        image_pairs = image_pairs[_MAX_IMAGE_LOOKUP_COUNT:]

    # Filter down to those images actually in the pairs set and build the set of queries to run.
    individual_image_queries = []

    for img in images:
        # Make sure the image found is in the set of those requested, and that we haven't already
        # processed it. We need this check because the query above checks for images with matching
        # IDs OR storage UUIDs, rather than the expected ID+UUID pair. We do this for efficiency
        # reasons, and it is highly unlikely we'll find an image with a mismatch, but we need this
        # check to be absolutely sure.
        pair = (img.docker_image_id, img.storage.uuid)
        if pair not in image_pairs_set:
            continue

        # Remove the pair so we don't try it again.
        image_pairs_set.remove(pair)

        ancestors_str = "%s%s/%%" % (img.ancestors, img.id)
        query = Image.select(Image.id).where(
            (Image.id == img.id) | (Image.ancestors ** ancestors_str)
        )

        individual_image_queries.append(query)

    if not individual_image_queries:
        return []

    # Shard based on the max subquery count. This is used to prevent going over the DB's max query
    # size, as well as to prevent the DB from locking up on a massive query.
    sharded_queries = []
    while individual_image_queries:
        shard = individual_image_queries[:_MAX_SUB_QUERIES]
        sharded_queries.append(_basequery.reduce_as_tree(shard))
        individual_image_queries = individual_image_queries[_MAX_SUB_QUERIES:]

    # Collect IDs of the tags found for each query.
    tags = {}
    for query in sharded_queries:
        ImageAlias = Image.alias()
        tag_query = _tag_alive(
            RepositoryTag.select(*(selections or []))
            .distinct()
            .join(ImageAlias)
            .where(RepositoryTag.hidden == False)
            .where(ImageAlias.id << query)
            .switch(RepositoryTag)
        )

        if filter_tags is not None:
            tag_query = filter_tags(tag_query)

        for tag in tag_query:
            tags[tag.id] = tag

    return list(tags.values())


def get_matching_tags(docker_image_id, storage_uuid, *args):
    """
    Returns a query pointing to all tags that contain the image with the given docker_image_id and
    storage_uuid.
    """
    image_row = image.get_image_with_storage(docker_image_id, storage_uuid)
    if image_row is None:
        return RepositoryTag.select().where(RepositoryTag.id < 0)  # Empty query.

    ancestors_str = "%s%s/%%" % (image_row.ancestors, image_row.id)
    return _tag_alive(
        RepositoryTag.select(*args)
        .distinct()
        .join(Image)
        .join(ImageStorage)
        .where(RepositoryTag.hidden == False)
        .where((Image.id == image_row.id) | (Image.ancestors ** ancestors_str))
    )


def get_tags_for_image(image_id, *args):
    return _tag_alive(
        RepositoryTag.select(*args)
        .distinct()
        .where(RepositoryTag.image == image_id, RepositoryTag.hidden == False)
    )


def get_tag_manifest_digests(tags):
    """
    Returns a map from tag ID to its associated manifest digest, if any.
    """
    if not tags:
        return dict()

    manifests = TagManifest.select(TagManifest.tag, TagManifest.digest).where(
        TagManifest.tag << [t.id for t in tags]
    )

    return {manifest.tag_id: manifest.digest for manifest in manifests}


def list_active_repo_tags(repo, start_id=None, limit=None, include_images=True):
    """
    Returns all of the active, non-hidden tags in a repository, joined to they images and (if
    present), their manifest.
    """
    if include_images:
        query = _tag_alive(
            RepositoryTag.select(RepositoryTag, Image, ImageStorage, TagManifest.digest)
            .join(Image)
            .join(ImageStorage)
            .where(RepositoryTag.repository == repo, RepositoryTag.hidden == False)
            .switch(RepositoryTag)
            .join(TagManifest, JOIN.LEFT_OUTER)
            .order_by(RepositoryTag.id)
        )
    else:
        query = _tag_alive(
            RepositoryTag.select(RepositoryTag)
            .where(RepositoryTag.repository == repo, RepositoryTag.hidden == False)
            .order_by(RepositoryTag.id)
        )

    if start_id is not None:
        query = query.where(RepositoryTag.id >= start_id)

    if limit is not None:
        query = query.limit(limit)

    return query


def list_repository_tags(
    namespace_name, repository_name, include_hidden=False, include_storage=False
):
    to_select = (RepositoryTag, Image)
    if include_storage:
        to_select = (RepositoryTag, Image, ImageStorage)

    query = _tag_alive(
        RepositoryTag.select(*to_select)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .switch(RepositoryTag)
        .join(Image)
        .where(Repository.name == repository_name, Namespace.username == namespace_name)
    )

    if not include_hidden:
        query = query.where(RepositoryTag.hidden == False)

    if include_storage:
        query = query.switch(Image).join(ImageStorage)

    return query


def create_or_update_tag(
    namespace_name, repository_name, tag_name, tag_docker_image_id, reversion=False, now_ms=None
):
    try:
        repo = _basequery.get_existing_repository(namespace_name, repository_name)
    except Repository.DoesNotExist:
        raise DataModelException("Invalid repository %s/%s" % (namespace_name, repository_name))

    return create_or_update_tag_for_repo(
        repo.id, tag_name, tag_docker_image_id, reversion=reversion, now_ms=now_ms
    )


def create_or_update_tag_for_repo(
    repository_id, tag_name, tag_docker_image_id, reversion=False, oci_manifest=None, now_ms=None
):
    now_ms = now_ms or get_epoch_timestamp_ms()
    now_ts = int(now_ms / 1000)

    with db_transaction():
        try:
            tag = db_for_update(
                _tag_alive(
                    RepositoryTag.select().where(
                        RepositoryTag.repository == repository_id, RepositoryTag.name == tag_name
                    ),
                    now_ts,
                )
            ).get()
            tag.lifetime_end_ts = now_ts
            tag.save()

            # Check for an OCI tag.
            try:
                oci_tag = db_for_update(
                    Tag.select()
                    .join(TagToRepositoryTag)
                    .where(TagToRepositoryTag.repository_tag == tag)
                ).get()
                oci_tag.lifetime_end_ms = now_ms
                oci_tag.save()
            except Tag.DoesNotExist:
                pass
        except RepositoryTag.DoesNotExist:
            pass
        except IntegrityError:
            msg = "Tag with name %s was stale when we tried to update it; Please retry the push"
            raise StaleTagException(msg % tag_name)

        try:
            image_obj = Image.get(
                Image.docker_image_id == tag_docker_image_id, Image.repository == repository_id
            )
        except Image.DoesNotExist:
            raise DataModelException("Invalid image with id: %s" % tag_docker_image_id)

        try:
            created = RepositoryTag.create(
                repository=repository_id,
                image=image_obj,
                name=tag_name,
                lifetime_start_ts=now_ts,
                reversion=reversion,
            )
            if oci_manifest:
                # Create the OCI tag as well.
                oci_tag = Tag.create(
                    repository=repository_id,
                    manifest=oci_manifest,
                    name=tag_name,
                    lifetime_start_ms=now_ms,
                    reversion=reversion,
                    tag_kind=Tag.tag_kind.get_id("tag"),
                )
                TagToRepositoryTag.create(
                    tag=oci_tag, repository_tag=created, repository=repository_id
                )

            return created
        except IntegrityError:
            msg = "Tag with name %s and lifetime start %s already exists"
            raise TagAlreadyCreatedException(msg % (tag_name, now_ts))


def create_temporary_hidden_tag(repo, image_obj, expiration_s):
    """
    Create a tag with a defined timeline, that will not appear in the UI or CLI.

    Returns the name of the temporary tag.
    """
    now_ts = get_epoch_timestamp()
    expire_ts = now_ts + expiration_s
    tag_name = str(uuid4())
    RepositoryTag.create(
        repository=repo,
        image=image_obj,
        name=tag_name,
        lifetime_start_ts=now_ts,
        lifetime_end_ts=expire_ts,
        hidden=True,
    )
    return tag_name


def lookup_unrecoverable_tags(repo):
    """
    Returns the tags  in a repository that are expired and past their time machine recovery period.
    """
    expired_clause = get_epoch_timestamp() - Namespace.removed_tag_expiration_s
    return (
        RepositoryTag.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(RepositoryTag.repository == repo)
        .where(
            ~(RepositoryTag.lifetime_end_ts >> None),
            RepositoryTag.lifetime_end_ts <= expired_clause,
        )
    )


def delete_tag(namespace_name, repository_name, tag_name, now_ms=None):
    now_ms = now_ms or get_epoch_timestamp_ms()
    now_ts = int(now_ms / 1000)

    with db_transaction():
        try:
            query = _tag_alive(
                RepositoryTag.select(RepositoryTag, Repository)
                .join(Repository)
                .join(Namespace, on=(Repository.namespace_user == Namespace.id))
                .where(
                    Repository.name == repository_name,
                    Namespace.username == namespace_name,
                    RepositoryTag.name == tag_name,
                ),
                now_ts,
            )
            found = db_for_update(query).get()
        except RepositoryTag.DoesNotExist:
            msg = "Invalid repository tag '%s' on repository '%s/%s'" % (
                tag_name,
                namespace_name,
                repository_name,
            )
            raise DataModelException(msg)

        found.lifetime_end_ts = now_ts
        found.save()

        try:
            oci_tag_query = TagToRepositoryTag.select().where(
                TagToRepositoryTag.repository_tag == found
            )
            oci_tag = db_for_update(oci_tag_query).get().tag
            oci_tag.lifetime_end_ms = now_ms
            oci_tag.save()
        except TagToRepositoryTag.DoesNotExist:
            pass

        return found


def _get_repo_tag_image(tag_name, include_storage, modifier):
    query = Image.select().join(RepositoryTag)

    if include_storage:
        query = (
            Image.select(Image, ImageStorage).join(ImageStorage).switch(Image).join(RepositoryTag)
        )

    images = _tag_alive(modifier(query.where(RepositoryTag.name == tag_name)))
    if not images:
        raise DataModelException("Unable to find image for tag.")
    else:
        return images[0]


def get_repo_tag_image(repo, tag_name, include_storage=False):
    def modifier(query):
        return query.where(RepositoryTag.repository == repo)

    return _get_repo_tag_image(tag_name, include_storage, modifier)


def get_tag_image(namespace_name, repository_name, tag_name, include_storage=False):
    def modifier(query):
        return (
            query.switch(RepositoryTag)
            .join(Repository)
            .join(Namespace)
            .where(Namespace.username == namespace_name, Repository.name == repository_name)
        )

    return _get_repo_tag_image(tag_name, include_storage, modifier)


def list_repository_tag_history(
    repo_obj, page=1, size=100, specific_tag=None, active_tags_only=False, since_time=None
):
    # Only available on OCI model
    if since_time is not None:
        raise NotImplementedError

    query = (
        RepositoryTag.select(RepositoryTag, Image, ImageStorage)
        .join(Image)
        .join(ImageStorage)
        .switch(RepositoryTag)
        .where(RepositoryTag.repository == repo_obj)
        .where(RepositoryTag.hidden == False)
        .order_by(RepositoryTag.lifetime_start_ts.desc(), RepositoryTag.name)
        .limit(size + 1)
        .offset(size * (page - 1))
    )

    if active_tags_only:
        query = _tag_alive(query)

    if specific_tag:
        query = query.where(RepositoryTag.name == specific_tag)

    tags = list(query)
    if not tags:
        return [], {}, False

    manifest_map = get_tag_manifest_digests(tags)
    return tags[0:size], manifest_map, len(tags) > size


def restore_tag_to_manifest(repo_obj, tag_name, manifest_digest):
    """
    Restores a tag to a specific manifest digest.
    """
    with db_transaction():
        # Verify that the manifest digest already existed under this repository under the
        # tag.
        try:
            tag_manifest = (
                TagManifest.select(TagManifest, RepositoryTag, Image)
                .join(RepositoryTag)
                .join(Image)
                .where(RepositoryTag.repository == repo_obj)
                .where(RepositoryTag.name == tag_name)
                .where(TagManifest.digest == manifest_digest)
                .get()
            )
        except TagManifest.DoesNotExist:
            raise DataModelException("Cannot restore to unknown or invalid digest")

        # Lookup the existing image, if any.
        try:
            existing_image = get_repo_tag_image(repo_obj, tag_name)
        except DataModelException:
            existing_image = None

        docker_image_id = tag_manifest.tag.image.docker_image_id
        oci_manifest = None
        try:
            oci_manifest = Manifest.get(repository=repo_obj, digest=manifest_digest)
        except Manifest.DoesNotExist:
            pass

        # Change the tag and tag manifest to point to the updated image.
        updated_tag = create_or_update_tag_for_repo(
            repo_obj, tag_name, docker_image_id, reversion=True, oci_manifest=oci_manifest
        )
        tag_manifest.tag = updated_tag
        tag_manifest.save()
        return existing_image


def restore_tag_to_image(repo_obj, tag_name, docker_image_id):
    """
    Restores a tag to a specific image ID.
    """
    with db_transaction():
        # Verify that the image ID already existed under this repository under the
        # tag.
        try:
            (
                RepositoryTag.select()
                .join(Image)
                .where(RepositoryTag.repository == repo_obj)
                .where(RepositoryTag.name == tag_name)
                .where(Image.docker_image_id == docker_image_id)
                .get()
            )
        except RepositoryTag.DoesNotExist:
            raise DataModelException("Cannot restore to unknown or invalid image")

        # Lookup the existing image, if any.
        try:
            existing_image = get_repo_tag_image(repo_obj, tag_name)
        except DataModelException:
            existing_image = None

        create_or_update_tag_for_repo(repo_obj, tag_name, docker_image_id, reversion=True)
        return existing_image


def store_tag_manifest_for_testing(
    namespace_name, repository_name, tag_name, manifest, leaf_layer_id, storage_id_map
):
    """
    Stores a tag manifest for a specific tag name in the database.

    Returns the TagManifest object, as well as a boolean indicating whether the TagManifest was
    created.
    """
    try:
        repo = _basequery.get_existing_repository(namespace_name, repository_name)
    except Repository.DoesNotExist:
        raise DataModelException("Invalid repository %s/%s" % (namespace_name, repository_name))

    return store_tag_manifest_for_repo(repo.id, tag_name, manifest, leaf_layer_id, storage_id_map)


def store_tag_manifest_for_repo(
    repository_id, tag_name, manifest, leaf_layer_id, storage_id_map, reversion=False
):
    """
    Stores a tag manifest for a specific tag name in the database.

    Returns the TagManifest object, as well as a boolean indicating whether the TagManifest was
    created.
    """
    # Create the new-style OCI manifest and its blobs.
    oci_manifest = _populate_manifest_and_blobs(
        repository_id, manifest, storage_id_map, leaf_layer_id=leaf_layer_id
    )

    # Create the tag for the tag manifest.
    tag = create_or_update_tag_for_repo(
        repository_id, tag_name, leaf_layer_id, reversion=reversion, oci_manifest=oci_manifest
    )

    # Add a tag manifest pointing to that tag.
    try:
        manifest = TagManifest.get(digest=manifest.digest)
        manifest.tag = tag
        manifest.save()
        return manifest, False
    except TagManifest.DoesNotExist:
        created = _associate_manifest(tag, oci_manifest)
        return created, True


def get_active_tag(namespace, repo_name, tag_name):
    return _tag_alive(
        RepositoryTag.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(
            RepositoryTag.name == tag_name,
            Repository.name == repo_name,
            Namespace.username == namespace,
        )
    ).get()


def get_active_tag_for_repo(repo, tag_name):
    try:
        return _tag_alive(
            RepositoryTag.select(RepositoryTag, Image, ImageStorage)
            .join(Image)
            .join(ImageStorage)
            .where(
                RepositoryTag.name == tag_name,
                RepositoryTag.repository == repo,
                RepositoryTag.hidden == False,
            )
        ).get()
    except RepositoryTag.DoesNotExist:
        return None


def get_expired_tag_in_repo(repo, tag_name):
    return (
        RepositoryTag.select()
        .where(RepositoryTag.name == tag_name, RepositoryTag.repository == repo)
        .where(~(RepositoryTag.lifetime_end_ts >> None))
        .where(RepositoryTag.lifetime_end_ts <= get_epoch_timestamp())
        .get()
    )


def get_possibly_expired_tag(namespace, repo_name, tag_name):
    return (
        RepositoryTag.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(
            RepositoryTag.name == tag_name,
            Repository.name == repo_name,
            Namespace.username == namespace,
        )
    ).get()


def associate_generated_tag_manifest_with_tag(tag, manifest, storage_id_map):
    oci_manifest = _populate_manifest_and_blobs(tag.repository, manifest, storage_id_map)

    with db_transaction():
        try:
            (
                Tag.select()
                .join(TagToRepositoryTag)
                .where(TagToRepositoryTag.repository_tag == tag)
            ).get()
        except Tag.DoesNotExist:
            oci_tag = Tag.create(
                repository=tag.repository,
                manifest=oci_manifest,
                name=tag.name,
                reversion=tag.reversion,
                lifetime_start_ms=tag.lifetime_start_ts * 1000,
                lifetime_end_ms=(tag.lifetime_end_ts * 1000 if tag.lifetime_end_ts else None),
                tag_kind=Tag.tag_kind.get_id("tag"),
            )
            TagToRepositoryTag.create(tag=oci_tag, repository_tag=tag, repository=tag.repository)

        return _associate_manifest(tag, oci_manifest)


def _associate_manifest(tag, oci_manifest):
    with db_transaction():
        tag_manifest = TagManifest.create(
            tag=tag, digest=oci_manifest.digest, json_data=oci_manifest.manifest_bytes
        )
        TagManifestToManifest.create(tag_manifest=tag_manifest, manifest=oci_manifest)
        return tag_manifest


def _populate_manifest_and_blobs(repository, manifest, storage_id_map, leaf_layer_id=None):
    leaf_layer_id = leaf_layer_id or manifest.leaf_layer_v1_image_id
    try:
        legacy_image = Image.get(
            Image.docker_image_id == leaf_layer_id, Image.repository == repository
        )
    except Image.DoesNotExist:
        raise DataModelException("Invalid image with id: %s" % leaf_layer_id)

    storage_ids = set()
    for blob_digest in manifest.local_blob_digests:
        image_storage_id = storage_id_map.get(blob_digest)
        if image_storage_id is None:
            logger.error("Missing blob for manifest `%s` in: %s", blob_digest, storage_id_map)
            raise DataModelException("Missing blob for manifest `%s`" % blob_digest)

        if image_storage_id in storage_ids:
            continue

        storage_ids.add(image_storage_id)

    return populate_manifest(repository, manifest, legacy_image, storage_ids)


def populate_manifest(repository, manifest, legacy_image, storage_ids):
    """
    Populates the rows for the manifest, including its blobs and legacy image.
    """
    media_type = Manifest.media_type.get_id(manifest.media_type)

    # Check for an existing manifest. If present, return it.
    try:
        return Manifest.get(repository=repository, digest=manifest.digest)
    except Manifest.DoesNotExist:
        pass

    with db_transaction():
        try:
            manifest_row = Manifest.create(
                digest=manifest.digest,
                repository=repository,
                manifest_bytes=manifest.bytes.as_encoded_str(),
                media_type=media_type,
            )
        except IntegrityError as ie:
            logger.debug("Got integrity error when trying to write manifest: %s", ie)
            return Manifest.get(repository=repository, digest=manifest.digest)

        ManifestLegacyImage.create(manifest=manifest_row, repository=repository, image=legacy_image)

        blobs_to_insert = [
            dict(manifest=manifest_row, repository=repository, blob=storage_id)
            for storage_id in storage_ids
        ]
        if blobs_to_insert:
            ManifestBlob.insert_many(blobs_to_insert).execute()

        return manifest_row


def get_tag_manifest(tag):
    try:
        return TagManifest.get(tag=tag)
    except TagManifest.DoesNotExist:
        return None


def load_tag_manifest(namespace, repo_name, tag_name):
    try:
        return (
            _load_repo_manifests(namespace, repo_name).where(RepositoryTag.name == tag_name).get()
        )
    except TagManifest.DoesNotExist:
        msg = "Manifest not found for tag {0} in repo {1}/{2}".format(
            tag_name, namespace, repo_name
        )
        raise InvalidManifestException(msg)


def delete_manifest_by_digest(namespace, repo_name, digest):
    tag_manifests = list(
        _load_repo_manifests(namespace, repo_name).where(TagManifest.digest == digest)
    )

    now_ms = get_epoch_timestamp_ms()
    for tag_manifest in tag_manifests:
        try:
            tag = _tag_alive(
                RepositoryTag.select().where(RepositoryTag.id == tag_manifest.tag_id)
            ).get()
            delete_tag(namespace, repo_name, tag_manifest.tag.name, now_ms)
        except RepositoryTag.DoesNotExist:
            pass

    return [tag_manifest.tag for tag_manifest in tag_manifests]


def load_manifest_by_digest(namespace, repo_name, digest, allow_dead=False):
    try:
        return (
            _load_repo_manifests(namespace, repo_name, allow_dead=allow_dead)
            .where(TagManifest.digest == digest)
            .get()
        )
    except TagManifest.DoesNotExist:
        msg = "Manifest not found with digest {0} in repo {1}/{2}".format(
            digest, namespace, repo_name
        )
        raise InvalidManifestException(msg)


def _load_repo_manifests(namespace, repo_name, allow_dead=False):
    query = (
        TagManifest.select(TagManifest, RepositoryTag)
        .join(RepositoryTag)
        .join(Image)
        .join(Repository)
        .join(Namespace, on=(Namespace.id == Repository.namespace_user))
        .where(Repository.name == repo_name, Namespace.username == namespace)
    )

    if not allow_dead:
        query = _tag_alive(query)

    return query


def change_repository_tag_expiration(namespace_name, repo_name, tag_name, expiration_date):
    """
    Changes the expiration of the tag with the given name to the given expiration datetime.

    If the expiration datetime is None, then the tag is marked as not expiring.
    """
    try:
        tag = get_active_tag(namespace_name, repo_name, tag_name)
        return change_tag_expiration(tag, expiration_date)
    except RepositoryTag.DoesNotExist:
        return (None, False)


def set_tag_expiration_for_manifest(tag_manifest, expiration_sec):
    """
    Changes the expiration of the tag that points to the given manifest to be its lifetime start +
    the expiration seconds.
    """
    expiration_time_ts = tag_manifest.tag.lifetime_start_ts + expiration_sec
    expiration_date = datetime.utcfromtimestamp(expiration_time_ts)
    return change_tag_expiration(tag_manifest.tag, expiration_date)


def change_tag_expiration(tag, expiration_date):
    """
    Changes the expiration of the given tag to the given expiration datetime.

    If the expiration datetime is None, then the tag is marked as not expiring.
    """
    end_ts = None
    min_expire_sec = convert_to_timedelta(config.app_config.get("LABELED_EXPIRATION_MINIMUM", "1h"))
    max_expire_sec = convert_to_timedelta(
        config.app_config.get("LABELED_EXPIRATION_MAXIMUM", "104w")
    )

    if expiration_date is not None:
        offset = timegm(expiration_date.utctimetuple()) - tag.lifetime_start_ts
        offset = min(max(offset, min_expire_sec.total_seconds()), max_expire_sec.total_seconds())
        end_ts = tag.lifetime_start_ts + offset

    if end_ts == tag.lifetime_end_ts:
        return (None, True)

    return set_tag_end_ts(tag, end_ts)


def set_tag_end_ts(tag, end_ts):
    """
    Sets the end timestamp for a tag.

    Should only be called by change_tag_expiration or tests.
    """
    end_ms = end_ts * 1000 if end_ts is not None else None

    with db_transaction():
        # Note: We check not just the ID of the tag but also its lifetime_end_ts, to ensure that it has
        # not changed while we were updating it expiration.
        result = (
            RepositoryTag.update(lifetime_end_ts=end_ts)
            .where(RepositoryTag.id == tag.id, RepositoryTag.lifetime_end_ts == tag.lifetime_end_ts)
            .execute()
        )

        # Check for a mapping to an OCI tag.
        try:
            oci_tag = (
                Tag.select()
                .join(TagToRepositoryTag)
                .where(TagToRepositoryTag.repository_tag == tag)
                .get()
            )

            (
                Tag.update(lifetime_end_ms=end_ms)
                .where(Tag.id == oci_tag.id, Tag.lifetime_end_ms == oci_tag.lifetime_end_ms)
                .execute()
            )
        except Tag.DoesNotExist:
            pass

        return (tag.lifetime_end_ts, result > 0)


def find_matching_tag(repo_id, tag_names):
    """
    Finds the most recently pushed alive tag in the repository with one of the given names, if any.
    """
    try:
        return _tag_alive(
            RepositoryTag.select()
            .where(RepositoryTag.repository == repo_id, RepositoryTag.name << list(tag_names))
            .order_by(RepositoryTag.lifetime_start_ts.desc())
        ).get()
    except RepositoryTag.DoesNotExist:
        return None


def get_most_recent_tag(repo_id):
    """
    Returns the most recently pushed alive tag in the repository, or None if none.
    """
    try:
        return _tag_alive(
            RepositoryTag.select()
            .where(RepositoryTag.repository == repo_id, RepositoryTag.hidden == False)
            .order_by(RepositoryTag.lifetime_start_ts.desc())
        ).get()
    except RepositoryTag.DoesNotExist:
        return None
