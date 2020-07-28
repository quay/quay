from data.database import (
    RepositoryTag,
    Repository,
    Namespace,
    get_epoch_timestamp,
)


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
