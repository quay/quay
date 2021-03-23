import uuid
import logging

from calendar import timegm
from peewee import fn

from data.database import (
    Tag,
    Manifest,
    ManifestLegacyImage,
    Image,
    ImageStorage,
    MediaType,
    RepositoryTag,
    RepositoryState,
    TagManifest,
    TagManifestToManifest,
    get_epoch_timestamp_ms,
    db_transaction,
    Repository,
    TagToRepositoryTag,
    Namespace,
    RepositoryNotification,
    ExternalNotificationEvent,
    db_random_func,
)
from data.model import config
from image.docker.schema1 import (
    DOCKER_SCHEMA1_CONTENT_TYPES,
    DockerSchema1Manifest,
    MalformedSchema1Manifest,
)
from util.bytes import Bytes
from util.timedeltastring import convert_to_timedelta

logger = logging.getLogger(__name__)

GC_CANDIDATE_COUNT = 500  # repositories


class RetargetTagException(Exception):
    """Exception raised when re-targetting a tag fails and explicit exception
    raising is requested."""


def get_tag_by_id(tag_id):
    """
    Returns the tag with the given ID, joined with its manifest or None if none.
    """
    try:
        return Tag.select(Tag, Manifest).join(Manifest).where(Tag.id == tag_id).get()
    except Tag.DoesNotExist:
        return None


def get_tag(repository_id, tag_name):
    """
    Returns the alive, non-hidden tag with the given name under the specified repository or None if
    none.

    The tag is returned joined with its manifest.
    """
    query = (
        Tag.select(Tag, Manifest)
        .join(Manifest)
        .where(Tag.repository == repository_id)
        .where(Tag.name == tag_name)
    )

    query = filter_to_alive_tags(query)

    try:
        found = query.get()
        assert not found.hidden
        return found
    except Tag.DoesNotExist:
        return None


def tag_names_for_manifest(manifest_id, limit=None):
    """
    Returns the names of the tags pointing to the given manifest.
    """

    query = Tag.select(Tag.id, Tag.name).where(Tag.manifest == manifest_id)

    if limit is not None:
        query = query.limit(limit)

    return [tag.name for tag in filter_to_alive_tags(query)]


def lookup_alive_tags_shallow(repository_id, start_pagination_id=None, limit=None):
    """
    Returns a list of the tags alive in the specified repository. Note that the tags returned.

    *only* contain their ID and name. Also note that the Tags are returned ordered by ID.
    """
    query = Tag.select(Tag.id, Tag.name).where(Tag.repository == repository_id).order_by(Tag.id)

    if start_pagination_id is not None:
        query = query.where(Tag.id >= start_pagination_id)

    if limit is not None:
        query = query.limit(limit)

    return filter_to_alive_tags(query)


def list_alive_tags(repository_id):
    """
    Returns a list of all the tags alive in the specified repository.

    Tag's returned are joined with their manifest.
    """
    query = Tag.select(Tag, Manifest).join(Manifest).where(Tag.repository == repository_id)

    return filter_to_alive_tags(query)


def list_repository_tag_history(
    repository_id,
    page,
    page_size,
    specific_tag_name=None,
    active_tags_only=False,
    since_time_ms=None,
):
    """
    Returns a tuple of the full set of tags found in the specified repository, including those that
    are no longer alive (unless active_tags_only is True), and whether additional tags exist. If
    specific_tag_name is given, the tags are further filtered by name. If since is given, tags are
    further filtered to newer than that date.

    Note that the returned Manifest will not contain the manifest contents.
    """
    query = (
        Tag.select(
            Tag,
            Manifest.id,
            Manifest.digest,
            Manifest.media_type,
            Manifest.layers_compressed_size,
            Manifest.config_media_type,
        )
        .join(Manifest)
        .where(Tag.repository == repository_id)
        .order_by(Tag.lifetime_start_ms.desc(), Tag.name)
        .limit(page_size + 1)
        .offset(page_size * (page - 1))
    )

    if specific_tag_name is not None:
        query = query.where(Tag.name == specific_tag_name)

    if since_time_ms is not None:
        query = query.where(
            (Tag.lifetime_start_ms > since_time_ms) | (Tag.lifetime_end_ms > since_time_ms)
        )

    if active_tags_only:
        query = filter_to_alive_tags(query)
    else:
        query = filter_to_visible_tags(query)

    results = list(query)

    return results[0:page_size], len(results) > page_size


def find_matching_tag(repository_id, tag_names, tag_kinds=None):
    """
    Finds an alive tag in the specified repository with one of the specified tag names and returns
    it or None if none.

    Tag's returned are joined with their manifest.
    """
    assert repository_id
    assert tag_names

    query = (
        Tag.select(Tag, Manifest)
        .join(Manifest)
        .where(Tag.repository == repository_id)
        .where(Tag.name << tag_names)
    )

    if tag_kinds:
        query = query.where(Tag.tag_kind << tag_kinds)

    try:
        found = filter_to_alive_tags(query).get()
        assert not found.hidden
        return found
    except Tag.DoesNotExist:
        return None


def get_most_recent_tag_lifetime_start(repository_ids):
    """
    Returns a map from repo ID to the timestamp of the most recently pushed alive tag for each
    specified repository or None if none.
    """
    if not repository_ids:
        return {}

    assert len(repository_ids) > 0 and None not in repository_ids
    assert len(repository_ids) <= 100

    query = (
        Tag.select(Tag.repository, fn.Max(Tag.lifetime_start_ms))
        .where(Tag.repository << [repo_id for repo_id in repository_ids])
        .group_by(Tag.repository)
    )
    tuples = filter_to_alive_tags(query).tuples()

    return {repo_id: timestamp for repo_id, timestamp in tuples}


def get_most_recent_tag(repository_id):
    """
    Returns the most recently pushed alive tag in the specified repository or None if none.

    The Tag returned is joined with its manifest.
    """
    assert repository_id

    query = (
        Tag.select(Tag, Manifest)
        .join(Manifest)
        .where(Tag.repository == repository_id)
        .order_by(Tag.lifetime_start_ms.desc())
    )

    try:
        found = filter_to_alive_tags(query).get()
        assert not found.hidden
        return found
    except Tag.DoesNotExist:
        return None


def get_expired_tag(repository_id, tag_name):
    """
    Returns a tag with the given name that is expired in the repository or None if none.
    """
    try:
        return (
            Tag.select()
            .where(Tag.name == tag_name, Tag.repository == repository_id)
            .where(~(Tag.lifetime_end_ms >> None))
            .where(Tag.lifetime_end_ms <= get_epoch_timestamp_ms())
            .get()
        )
    except Tag.DoesNotExist:
        return None


def create_temporary_tag_if_necessary(manifest, expiration_sec):
    """
    Creates a temporary tag pointing to the given manifest, with the given expiration in seconds,
    unless there is an existing tag that will keep the manifest around.
    """
    tag_name = "$temp-%s" % str(uuid.uuid4())
    now_ms = get_epoch_timestamp_ms()
    end_ms = now_ms + (expiration_sec * 1000)

    # Check if there is an existing tag on the manifest that won't expire within the
    # timeframe. If so, no need for a temporary tag.
    with db_transaction():
        try:
            (
                Tag.select()
                .where(
                    Tag.manifest == manifest,
                    (Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms >= end_ms),
                )
                .get()
            )
            return None
        except Tag.DoesNotExist:
            pass

        return Tag.create(
            name=tag_name,
            repository=manifest.repository_id,
            lifetime_start_ms=now_ms,
            lifetime_end_ms=end_ms,
            reversion=False,
            hidden=True,
            manifest=manifest,
            tag_kind=Tag.tag_kind.get_id("tag"),
        )


def retarget_tag(
    tag_name,
    manifest_id,
    is_reversion=False,
    now_ms=None,
    raise_on_error=False,
    expiration_seconds=None,
):
    """
    Creates or updates a tag with the specified name to point to the given manifest under its
    repository.

    If this action is a reversion to a previous manifest, is_reversion should be set to True.
    Returns the newly created tag row or None on error.
    """
    try:
        manifest = (
            Manifest.select(Manifest, MediaType)
            .join(MediaType)
            .where(Manifest.id == manifest_id)
            .get()
        )
    except Manifest.DoesNotExist:
        if raise_on_error:
            raise RetargetTagException("Manifest requested no longer exists")

        return None

    # CHECK: Make sure that we are not mistargeting a schema 1 manifest to a tag with a different
    # name.
    if manifest.media_type.name in DOCKER_SCHEMA1_CONTENT_TYPES:
        try:
            parsed = DockerSchema1Manifest(
                Bytes.for_string_or_unicode(manifest.manifest_bytes), validate=False
            )
            if parsed.tag != tag_name:
                logger.error(
                    "Tried to re-target schema1 manifest with tag `%s` to tag `%s",
                    parsed.tag,
                    tag_name,
                )
                return None
        except MalformedSchema1Manifest as msme:
            logger.exception("Could not parse schema1 manifest")
            if raise_on_error:
                raise RetargetTagException(msme)

            return None

    now_ms = now_ms or get_epoch_timestamp_ms()
    now_ts = int(now_ms // 1000)

    with db_transaction():
        # Lookup an existing tag in the repository with the same name and, if present, mark it
        # as expired.
        existing_tag = get_tag(manifest.repository_id, tag_name)
        if existing_tag is not None:
            _, okay = set_tag_end_ms(existing_tag, now_ms)

            # TODO: should we retry here and/or use a for-update?
            if not okay:
                return None

        # Create a new tag pointing to the manifest with a lifetime start of now.
        created = Tag.create(
            name=tag_name,
            repository=manifest.repository_id,
            lifetime_start_ms=now_ms,
            lifetime_end_ms=(now_ms + expiration_seconds * 1000) if expiration_seconds else None,
            reversion=is_reversion,
            manifest=manifest,
            tag_kind=Tag.tag_kind.get_id("tag"),
        )

        return created


def delete_tag(repository_id, tag_name):
    """
    Deletes the alive tag with the given name in the specified repository and returns the deleted
    tag.

    If the tag did not exist, returns None.
    """
    tag = get_tag(repository_id, tag_name)
    if tag is None:
        return None

    return _delete_tag(tag, get_epoch_timestamp_ms())


def _delete_tag(tag, now_ms):
    """
    Deletes the given tag by marking it as expired.
    """
    now_ts = int(now_ms // 1000)

    with db_transaction():
        updated = (
            Tag.update(lifetime_end_ms=now_ms)
            .where(Tag.id == tag.id, Tag.lifetime_end_ms == tag.lifetime_end_ms)
            .execute()
        )
        if updated != 1:
            return None

        # TODO: Remove the linkage code once RepositoryTag is gone.
        try:
            old_style_tag = (
                TagToRepositoryTag.select(TagToRepositoryTag, RepositoryTag)
                .join(RepositoryTag)
                .where(TagToRepositoryTag.tag == tag)
                .get()
            ).repository_tag

            old_style_tag.lifetime_end_ts = now_ts
            old_style_tag.save()
        except TagToRepositoryTag.DoesNotExist:
            pass

        return tag


def delete_tags_for_manifest(manifest):
    """
    Deletes all tags pointing to the given manifest.

    Returns the list of tags deleted.
    """
    query = Tag.select().where(Tag.manifest == manifest)
    query = filter_to_alive_tags(query)

    tags = list(query)
    now_ms = get_epoch_timestamp_ms()

    with db_transaction():
        for tag in tags:
            _delete_tag(tag, now_ms)

    return tags


def filter_to_visible_tags(query):
    """
    Adjusts the specified Tag query to only return those tags that are visible.
    """
    return query.where(Tag.hidden == False)


def filter_to_alive_tags(query, now_ms=None, model=Tag):
    """
    Adjusts the specified Tag query to only return those tags alive.

    If now_ms is specified, the given timestamp (in MS) is used in place of the current timestamp
    for determining wherther a tag is alive.
    """
    if now_ms is None:
        now_ms = get_epoch_timestamp_ms()

    query = query.where((model.lifetime_end_ms >> None) | (model.lifetime_end_ms > now_ms))
    return filter_to_visible_tags(query)


def set_tag_expiration_sec_for_manifest(manifest_id, expiration_seconds):
    """
    Sets the tag expiration for any tags that point to the given manifest ID.
    """
    query = Tag.select().where(Tag.manifest == manifest_id)
    query = filter_to_alive_tags(query)
    tags = list(query)
    for tag in tags:
        assert not tag.hidden
        set_tag_end_ms(tag, tag.lifetime_start_ms + (expiration_seconds * 1000))

    return tags


def set_tag_expiration_for_manifest(manifest_id, expiration_datetime):
    """
    Sets the tag expiration for any tags that point to the given manifest ID.
    """
    query = Tag.select().where(Tag.manifest == manifest_id)
    query = filter_to_alive_tags(query)
    tags = list(query)
    for tag in tags:
        assert not tag.hidden
        change_tag_expiration(tag, expiration_datetime)

    return tags


def change_tag_expiration(tag_id, expiration_datetime):
    """
    Changes the expiration of the specified tag to the given expiration datetime.

    If the expiration datetime is None, then the tag is marked as not expiring. Returns a tuple of
    the previous expiration timestamp in seconds (if any), and whether the operation succeeded.
    """
    try:
        tag = Tag.get(id=tag_id)
    except Tag.DoesNotExist:
        return (None, False)

    new_end_ms = None
    min_expire_sec = convert_to_timedelta(config.app_config.get("LABELED_EXPIRATION_MINIMUM", "1h"))
    max_expire_sec = convert_to_timedelta(
        config.app_config.get("LABELED_EXPIRATION_MAXIMUM", "104w")
    )

    if expiration_datetime is not None:
        lifetime_start_ts = int(tag.lifetime_start_ms // 1000)

        offset = timegm(expiration_datetime.utctimetuple()) - lifetime_start_ts
        offset = min(max(offset, min_expire_sec.total_seconds()), max_expire_sec.total_seconds())
        new_end_ms = tag.lifetime_start_ms + (offset * 1000)

    if new_end_ms == tag.lifetime_end_ms:
        return (None, True)

    return set_tag_end_ms(tag, new_end_ms)


def lookup_unrecoverable_tags(repo):
    """
    Returns the tags in a repository that are expired and past their time machine recovery period.
    """
    expired_clause = get_epoch_timestamp_ms() - (Namespace.removed_tag_expiration_s * 1000)
    return (
        Tag.select()
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Tag.repository == repo)
        .where(~(Tag.lifetime_end_ms >> None), Tag.lifetime_end_ms <= expired_clause)
    )


def set_tag_end_ms(tag, end_ms):
    """
    Sets the end timestamp for a tag.

    Should only be called by change_tag_expiration or tests.
    """

    with db_transaction():
        updated = (
            Tag.update(lifetime_end_ms=end_ms)
            .where(Tag.id == tag)
            .where(Tag.lifetime_end_ms == tag.lifetime_end_ms)
            .execute()
        )
        if updated != 1:
            return (None, False)

        # TODO: Remove the linkage code once RepositoryTag is gone.
        try:
            old_style_tag = (
                TagToRepositoryTag.select(TagToRepositoryTag, RepositoryTag)
                .join(RepositoryTag)
                .where(TagToRepositoryTag.tag == tag)
                .get()
            ).repository_tag

            old_style_tag.lifetime_end_ts = end_ms // 1000 if end_ms is not None else None
            old_style_tag.save()
        except TagToRepositoryTag.DoesNotExist:
            pass

        return (tag.lifetime_end_ms, True)


def tags_containing_legacy_image(image):
    """
    Yields all alive Tags containing the given image as a legacy image, somewhere in its legacy
    image hierarchy.
    """
    ancestors_str = "%s%s/%%" % (image.ancestors, image.id)
    tags = (
        Tag.select()
        .join(Repository)
        .switch(Tag)
        .join(Manifest)
        .join(ManifestLegacyImage)
        .join(Image)
        .where(Tag.repository == image.repository_id)
        .where(Image.repository == image.repository_id)
        .where((Image.id == image.id) | (Image.ancestors ** ancestors_str))
    )
    return filter_to_alive_tags(tags)


def find_repository_with_garbage(limit_to_gc_policy_s):
    """Returns a repository that has garbage (defined as an expired Tag that is past
    the repo's namespace's expiration window) or None if none.
    """
    expiration_timestamp = get_epoch_timestamp_ms() - (limit_to_gc_policy_s * 1000)

    try:
        candidates = (
            Tag.select(Tag.repository)
            .join(Repository)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .where(
                ~(Tag.lifetime_end_ms >> None),
                (Tag.lifetime_end_ms <= expiration_timestamp),
                (Namespace.removed_tag_expiration_s == limit_to_gc_policy_s),
                (Namespace.enabled == True),
                (Repository.state != RepositoryState.MARKED_FOR_DELETION),
            )
            .limit(GC_CANDIDATE_COUNT)
            .distinct()
            .alias("candidates")
        )

        found = (
            Tag.select(candidates.c.repository_id)
            .from_(candidates)
            .order_by(db_random_func())
            .get()
        )

        if found is None:
            return

        return Repository.get(Repository.id == found.repository_id)
    except Tag.DoesNotExist:
        return None
    except Repository.DoesNotExist:
        return None


def get_legacy_images_for_tags(tags):
    """
    Returns a map from tag ID to the legacy image for the tag.
    """
    if not tags:
        return {}

    query = (
        ManifestLegacyImage.select(ManifestLegacyImage, Image)
        .join(Image)
        .where(ManifestLegacyImage.manifest << [tag.manifest_id for tag in tags])
    )

    by_manifest = {mli.manifest_id: mli.image for mli in query}
    return {tag.id: by_manifest[tag.manifest_id] for tag in tags if tag.manifest_id in by_manifest}
