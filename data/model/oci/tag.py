import datetime
import logging
import uuid
from calendar import timegm

from peewee import fn

from data.database import (
    Manifest,
    ManifestChild,
    MediaType,
    Namespace,
    Repository,
    RepositoryState,
    Tag,
    User,
    db_random_func,
    db_regex_search,
    db_transaction,
    get_epoch_timestamp_ms,
)
from data.model import config, user
from data.model.notification import delete_tag_notifications_for_tag
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


def get_tag_by_manifest_id(repository_id, manifest_id):
    """
    Gets the tag with greatest lifetime_end_ms for the manifest with the given id,
    regardless if the tag is alive or dead.

    Retuns the tag joined with its manifest if one exists, or None otherwise.
    """
    try:
        return (
            Tag.select(Tag, Manifest)
            .join(Manifest)
            .where((Tag.repository_id == repository_id) & (Tag.manifest_id == manifest_id))
            .order_by(-Tag.lifetime_end_ms)
            .get()
        )
    except Tag.DoesNotExist:
        return None


def get_tag(repository_id, tag_name):
    """
    Returns the alive, non-hidden tag with the given name under the specified repository or None if
    none.

    The tag is returned joined with its manifest.
    """
    query = (
        Tag.select(Tag, Manifest, can_use_read_replica=True)
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


def get_current_tag(repository_id, tag_name):
    """
    Returns the current tag with the given name for the given repository.

    The current tag is the tag with the highest lifetime_end_ms, regardless of
    the tag being expired or hidden.
    """
    try:
        return (
            Tag.select(Tag, Manifest)
            .join(Manifest)
            .where(Tag.repository == repository_id)
            .where(Tag.name == tag_name)
            .order_by(-Tag.lifetime_end_ms)
            .get()
        )
    except Tag.DoesNotExist:
        return None


def get_child_manifests(repo_id: int, manifest_id: int):
    return ManifestChild.select(ManifestChild.child_manifest).where(
        ManifestChild.repository == repo_id,
        ManifestChild.manifest == manifest_id,
    )


def tag_names_for_manifest(manifest_id, limit=None):
    """
    Returns the names of the tags pointing to the given manifest.
    """

    query = Tag.select(Tag.id, Tag.name).where(Tag.manifest == manifest_id)

    if limit is not None:
        query = query.limit(limit)

    return [tag.name for tag in filter_to_alive_tags(query)]


def lookup_alive_tags_shallow(repository_id, last_pagination_tag_name=None, limit=None):
    """
    Returns a list of the tags alive in the specified repository and
    has_more to indicate whethere further pagination is required.
    Note that the tags returned *only* contain their ID and name.
    The tags are returned ordered by tag name to comply with OCI spec.
    """
    query = Tag.select(Tag.id, Tag.name).where(Tag.repository == repository_id).order_by(Tag.name)

    if last_pagination_tag_name is not None:
        query = query.where(Tag.name > last_pagination_tag_name)

    if limit is not None:
        query = query.limit(limit + 1)

    tags = filter_to_alive_tags(query)

    has_more = len(tags) > limit if limit is not None else False

    # If there are more tags, remove the extra one and return the rest
    if has_more:
        tags = tags[:-1]

    return tags, has_more


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
    filter_tag_name=None,
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
    try:
        if filter_tag_name is not None:
            operation, value = filter_tag_name.split(":", 1)
            if operation == "like":
                query = query.where(Tag.name.contains(value))
            elif operation == "eq":
                query = query.where(Tag.name == value)
    except ValueError:
        raise ValueError(
            "Unsupported syntax for filter_tag_name. Expected <operation>:<tag_name> where <operation>"
            "can be 'like' or 'eq'."
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


def get_tag_with_least_lifetime_end_for_ns(namespace_name):
    """
    Returns tags that have the least lifetime end in the specified namespace or None if none.
    """
    namespace = user.get_user_or_org(namespace_name)
    try:
        return (
            Tag.select()
            .join(Repository)
            .where(Tag.hidden == False)
            .where(Repository.namespace_user == namespace.id)
            .where(Tag.lifetime_end_ms > get_epoch_timestamp_ms())
            .order_by(Tag.lifetime_end_ms)
        )
    except Tag.DoesNotExist:
        return None


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


def create_temporary_tag_if_necessary(manifest, expiration_sec, skip_expiration=False):
    """
    Creates a temporary tag pointing to the given manifest, with the given expiration in seconds,
    unless there is an existing tag that will keep the manifest around.
    """
    tag_name = "$temp-%s" % str(uuid.uuid4())
    now_ms = get_epoch_timestamp_ms()
    if skip_expiration:
        # Skip expiration for hidden tags used for OCI artifacts referring to a subject manifest
        end_ms = None
    else:
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


def create_temporary_tag_outside_timemachine(manifest):
    """
    Creates a temporary tag that is outside the time machine window.
    Tag is immediately available for garbage collection.
    """
    tag_name = "$temp-%s" % str(uuid.uuid4())
    now_ms = get_epoch_timestamp_ms()

    return Tag.create(
        name=tag_name,
        repository=manifest.repository_id,
        lifetime_start_ms=now_ms,
        lifetime_end_ms=0,  # Start of unix epoch time
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
    with db_transaction():
        # clean notifications for tag expiry
        delete_tag_notifications_for_tag(tag)

        updated = (
            Tag.update(lifetime_end_ms=now_ms)
            .where(Tag.id == tag.id, Tag.lifetime_end_ms == tag.lifetime_end_ms)
            .execute()
        )
        if updated != 1:
            return None

        reset_child_manifest_expiration(tag.repository, tag.manifest)
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


def filter_to_alive_tags(query, now_ms=None, model=Tag, allow_hidden=False):
    """
    Adjusts the specified Tag query to only return those tags alive.

    If now_ms is specified, the given timestamp (in MS) is used in place of the current timestamp
    for determining wherther a tag is alive.
    """
    if now_ms is None:
        now_ms = get_epoch_timestamp_ms()

    query = query.where((model.lifetime_end_ms >> None) | (model.lifetime_end_ms > now_ms))

    if allow_hidden:
        return query
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
        # clean notifications for tag expiry
        delete_tag_notifications_for_tag(tag)

        updated = (
            Tag.update(lifetime_end_ms=end_ms)
            .where(Tag.id == tag)
            .where(Tag.lifetime_end_ms == tag.lifetime_end_ms)
            .execute()
        )
        if updated != 1:
            return (None, False)

        return (tag.lifetime_end_ms, True)


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


def get_tags_within_timemachine_window(repo_id, tag_name, manifest_id, timemaching_window_ms):
    if timemaching_window_ms == 0:
        return []

    now_ms = get_epoch_timestamp_ms()
    return (
        Tag.select(Tag.id)
        .where(Tag.name == tag_name)
        .where(Tag.repository == repo_id)
        .where(Tag.manifest == manifest_id)
        .where(Tag.lifetime_end_ms <= now_ms)
        .where(Tag.lifetime_end_ms > now_ms - timemaching_window_ms)
    )


def remove_tag_from_timemachine(
    repo_id, tag_name, manifest_id, include_submanifests=False, is_alive=False
):
    try:
        namespace = (
            User.select(User.removed_tag_expiration_s)
            .join(Repository, on=(Repository.namespace_user == User.id))
            .where(Repository.id == repo_id)
            .get()
        )
    except User.DoesNotExist:
        return False

    time_machine_ms = namespace.removed_tag_expiration_s * 1000
    now_ms = get_epoch_timestamp_ms()

    # Increment used to create unique lifetime_end_ms entries because of
    # tag_repository_id_name_lifetime_end_ms index
    increment = 1
    updated = False
    if is_alive:

        # Ensure the tag is actually alive
        alive_tag = get_tag(repo_id, tag_name)
        if alive_tag is None:
            return False

        # Expire the tag past the time machine window and set hidden=true to
        # prevent it from appearing in tag history
        updated = (
            Tag.update(lifetime_end_ms=now_ms - time_machine_ms)
            .where(Tag.id == alive_tag)
            .where(Tag.lifetime_end_ms == alive_tag.lifetime_end_ms)
            .execute()
        )
        if updated != 1:
            return False
        else:
            updated = True
    else:
        # Update all tags with matching name and manifest with a expiry outside the time machine
        # window
        with db_transaction():
            for tag in get_tags_within_timemachine_window(
                repo_id, tag_name, manifest_id, time_machine_ms
            ):
                Tag.update(lifetime_end_ms=now_ms - time_machine_ms - increment).where(
                    Tag.id == tag
                ).execute()
                updated = True
                increment = increment + 1

    if updated and include_submanifests:
        reset_child_manifest_expiration(repo_id, manifest_id, now_ms - time_machine_ms)

    return updated


def reset_child_manifest_expiration(repository_id, manifest, expiration=None):
    """
    Resets the expirations of temporary tags targeting the child manifests.
    """
    if not config.app_config.get("RESET_CHILD_MANIFEST_EXPIRATION", True):
        return

    with db_transaction():
        # pylint: disable-next=not-an-iterable
        for child_manifest in get_child_manifests(repository_id, manifest):
            expiry_ms = get_epoch_timestamp_ms() if expiration is None else expiration
            Tag.update(lifetime_end_ms=expiry_ms).where(
                Tag.repository == repository_id,
                Tag.manifest == child_manifest.child_manifest,
                Tag.lifetime_end_ms > expiry_ms,
                Tag.name.startswith("$temp-"),
                Tag.hidden == True,
            ).execute()


def fetch_paginated_autoprune_repo_tags_by_number(
    repo_id,
    max_tags_allowed: int,
    items_per_page,
    page,
    tag_pattern=None,
    tag_pattern_matches=True,
    exclude_tags=None,
):
    """
    Fetch repository's active tags sorted by creation date & are more than max_tags_allowed
    """
    try:
        tags_offset = max_tags_allowed + ((page - 1) * items_per_page)
        now_ms = get_epoch_timestamp_ms()
        query = (
            Tag.select(Tag.id, Tag.name).where(
                Tag.repository_id == repo_id,
                (Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms > now_ms),
                Tag.hidden == False,
            )
            # TODO: Ignoring type error for now, but it seems order_by doesn't
            # return anything to be modified by offset. Need to investigate
            .order_by(Tag.lifetime_start_ms.desc())  # type: ignore[func-returns-value]
        )

        if exclude_tags and len(exclude_tags) > 0:
            query.where(Tag.name.not_in([tag.name for tag in exclude_tags]))

        if tag_pattern is not None:
            query = db_regex_search(
                Tag.select(query.c.name).from_(query),
                query.c.name,
                tag_pattern,
                tags_offset,
                items_per_page,
                matches=tag_pattern_matches,
            )
        else:
            query = query.offset(tags_offset).limit(items_per_page)
        return list(query)
    except Exception as err:
        raise Exception(
            f"Error fetching repository tags by number for repository id: {repo_id} with error as: {str(err)}"
        )


def fetch_paginated_autoprune_repo_tags_older_than_ms(
    repo_id,
    tag_lifetime_ms: int,
    items_per_page=100,
    page: int = 1,
    tag_pattern=None,
    tag_pattern_matches=True,
):
    """
    Return repository's active tags older than tag_lifetime_ms
    """
    try:
        tags_offset = items_per_page * (page - 1)
        now_ms = get_epoch_timestamp_ms()
        query = Tag.select(Tag.id, Tag.name).where(
            Tag.repository_id == repo_id,
            (Tag.lifetime_end_ms >> None) | (Tag.lifetime_end_ms > now_ms),
            (now_ms - Tag.lifetime_start_ms) > tag_lifetime_ms,
            Tag.hidden == False,
        )
        if tag_pattern is not None:
            query = db_regex_search(
                query,
                Tag.name,
                tag_pattern,
                tags_offset,
                items_per_page,
                matches=tag_pattern_matches,
            )
        else:
            query = query.offset(tags_offset).limit(items_per_page)  # type: ignore[func-returns-value]
        return list(query)
    except Exception as err:
        raise Exception(
            f"Error fetching repository tags by creation date for repository id: {repo_id} with error as: {str(err)}"
        )


def fetch_repo_tags_for_image_expiry_expiry_event(repo_id, days, notified_tags):
    """
    notified_tags refer to the tags that were already notified for the event
    Return query to fetch repository's distinct active tags that are expiring in x number days
    """
    try:
        future_ms = (datetime.datetime.now() + datetime.timedelta(days=days)).timestamp() * 1000
        now_ms = get_epoch_timestamp_ms()
        query = (
            Tag.select(Tag.id, Tag.name)
            .where(
                Tag.repository_id == repo_id,
                (~(Tag.lifetime_end_ms >> None)),  # filter for tags where expiry is set
                Tag.lifetime_end_ms > now_ms,  # filter expired tags
                Tag.lifetime_end_ms <= future_ms,
                Tag.hidden == False,
                Tag.id.not_in(notified_tags),
            )
            .distinct()
        )
        return list(query)
    except Exception as err:
        raise Exception(
            f"Error fetching repository tags repository id: {repo_id} with error as: {str(err)}"
        )
