import logging

from cnr.models.package_base import manifest_media_type
from peewee import IntegrityError

from data.model import db_transaction, TagAlreadyCreatedException
from data.database import get_epoch_timestamp_ms, db_for_update


logger = logging.getLogger(__name__)


def tag_is_alive(query, cls, now_ts=None):
    return query.where((cls.lifetime_end >> None) | (cls.lifetime_end > now_ts))


def tag_media_type_exists(tag, media_type, models_ref):
    ManifestListManifest = models_ref.ManifestListManifest
    manifestlistmanifest_set_name = models_ref.manifestlistmanifest_set_name
    return (
        getattr(tag.manifest_list, manifestlistmanifest_set_name)
        .where(ManifestListManifest.media_type == media_type)
        .count()
        > 0
    )


def create_or_update_tag(
    repo, tag_name, models_ref, manifest_list=None, linked_tag=None, tag_kind="release"
):
    Tag = models_ref.Tag

    now_ts = get_epoch_timestamp_ms()
    tag_kind_id = Tag.tag_kind.get_id(tag_kind)
    with db_transaction():
        try:
            tag = db_for_update(
                tag_is_alive(
                    Tag.select().where(
                        Tag.repository == repo, Tag.name == tag_name, Tag.tag_kind == tag_kind_id
                    ),
                    Tag,
                    now_ts,
                )
            ).get()
            if tag.manifest_list == manifest_list and tag.linked_tag == linked_tag:
                return tag
            tag.lifetime_end = now_ts
            tag.save()
        except Tag.DoesNotExist:
            pass

        try:
            return Tag.create(
                repository=repo,
                manifest_list=manifest_list,
                linked_tag=linked_tag,
                name=tag_name,
                lifetime_start=now_ts,
                lifetime_end=None,
                tag_kind=tag_kind_id,
            )
        except IntegrityError:
            msg = "Tag with name %s and lifetime start %s under repository %s/%s already exists"
            raise TagAlreadyCreatedException(
                msg % (tag_name, now_ts, repo.namespace_user, repo.name)
            )


def get_or_initialize_tag(repo, tag_name, models_ref, tag_kind="release"):
    Tag = models_ref.Tag

    try:
        return tag_is_alive(
            Tag.select().where(Tag.repository == repo, Tag.name == tag_name), Tag
        ).get()
    except Tag.DoesNotExist:
        return Tag(repo=repo, name=tag_name, tag_kind=Tag.tag_kind.get_id(tag_kind))


def get_tag(repo, tag_name, models_ref, tag_kind="release"):
    Tag = models_ref.Tag
    return tag_is_alive(
        Tag.select().where(
            Tag.repository == repo,
            Tag.name == tag_name,
            Tag.tag_kind == Tag.tag_kind.get_id(tag_kind),
        ),
        Tag,
    ).get()


def delete_tag(repo, tag_name, models_ref, tag_kind="release"):
    Tag = models_ref.Tag
    tag_kind_id = Tag.tag_kind.get_id(tag_kind)
    tag = tag_is_alive(
        Tag.select().where(
            Tag.repository == repo, Tag.name == tag_name, Tag.tag_kind == tag_kind_id
        ),
        Tag,
    ).get()
    tag.lifetime_end = get_epoch_timestamp_ms()
    tag.save()
    return tag


def tag_exists(repo, tag_name, models_ref, tag_kind="release"):
    Tag = models_ref.Tag
    try:
        get_tag(repo, tag_name, models_ref, tag_kind)
        return True
    except Tag.DoesNotExist:
        return False


def filter_tags_by_media_type(tag_query, media_type, models_ref):
    """
    Return only available tag for a media_type.
    """
    ManifestListManifest = models_ref.ManifestListManifest
    Tag = models_ref.Tag
    media_type = manifest_media_type(media_type)
    t = tag_query.join(
        ManifestListManifest, on=(ManifestListManifest.manifest_list == Tag.manifest_list)
    ).where(ManifestListManifest.media_type == ManifestListManifest.media_type.get_id(media_type))
    return t


def get_most_recent_tag_lifetime_start(repository_ids, models_ref, tag_kind="release"):
    """
    Returns a map from repo ID to the timestamp of the most recently pushed alive tag for each
    specified repository or None if none.
    """
    if not repository_ids:
        return {}

    assert len(repository_ids) > 0 and None not in repository_ids

    Tag = models_ref.Tag
    tag_kind_id = Tag.tag_kind.get_id(tag_kind)
    tags = tag_is_alive(
        Tag.select().where(
            Tag.repository << [rid for rid in repository_ids], Tag.tag_kind == tag_kind_id
        ),
        Tag,
    )
    to_seconds = lambda ms: ms // 1000 if ms is not None else None

    return {t.repository.id: to_seconds(t.lifetime_start) for t in tags}
