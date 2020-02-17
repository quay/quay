from data.appr_model import tag as tag_model


def get_channel_releases(repo, channel, models_ref):
    """
    Return all previously linked tags.

    This works based upon Tag lifetimes.
    """
    Channel = models_ref.Channel
    Tag = models_ref.Tag

    tag_kind_id = Channel.tag_kind.get_id("channel")
    channel_name = channel.name
    return (
        Tag.select(Tag, Channel)
        .join(Channel, on=(Tag.id == Channel.linked_tag))
        .where(
            Channel.repository == repo,
            Channel.name == channel_name,
            Channel.tag_kind == tag_kind_id,
            Channel.lifetime_end != None,
        )
        .order_by(Tag.lifetime_end)
    )


def get_channel(repo, channel_name, models_ref):
    """
    Find a Channel by name.
    """
    channel = tag_model.get_tag(repo, channel_name, models_ref, "channel")
    return channel


def get_tag_channels(repo, tag_name, models_ref, active=True):
    """
    Find the Channels associated with a Tag.
    """
    Tag = models_ref.Tag

    tag = tag_model.get_tag(repo, tag_name, models_ref, "release")
    query = tag.tag_parents

    if active:
        query = tag_model.tag_is_alive(query, Tag)

    return query


def delete_channel(repo, channel_name, models_ref):
    """
    Delete a channel by name.
    """
    return tag_model.delete_tag(repo, channel_name, models_ref, "channel")


def create_or_update_channel(repo, channel_name, tag_name, models_ref):
    """
    Creates or updates a channel to include a particular tag.
    """
    tag = tag_model.get_tag(repo, tag_name, models_ref, "release")
    return tag_model.create_or_update_tag(
        repo, channel_name, models_ref, linked_tag=tag, tag_kind="channel"
    )


def get_repo_channels(repo, models_ref):
    """
    Creates or updates a channel to include a particular tag.
    """
    Channel = models_ref.Channel
    Tag = models_ref.Tag

    tag_kind_id = Channel.tag_kind.get_id("channel")
    query = (
        Channel.select(Channel, Tag)
        .join(Tag, on=(Tag.id == Channel.linked_tag))
        .where(Channel.repository == repo, Channel.tag_kind == tag_kind_id)
    )
    return tag_model.tag_is_alive(query, Channel)
