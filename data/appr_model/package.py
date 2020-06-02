from cnr.models.package_base import get_media_type, manifest_media_type
from peewee import prefetch


from data import model
from data.database import Repository, Namespace, RepositoryState
from data.appr_model import tag as tag_model


def list_packages_query(
    models_ref, namespace=None, media_type=None, search_query=None, username=None, limit=50,
):
    """
    List and filter repository by search query.
    """
    Tag = models_ref.Tag

    if username and not search_query:
        repositories = model.repository.get_visible_repositories(
            username,
            kind_filter="application",
            include_public=True,
            namespace=namespace,
            limit=limit,
        )
        if not repositories:
            return []

        repo_query = (
            Repository.select(Repository, Namespace.username)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .where(Repository.id << [repo.rid for repo in repositories])
        )

        if namespace:
            repo_query = repo_query.where(Namespace.username == namespace)
    else:
        if search_query is not None:
            fields = [model.repository.SEARCH_FIELDS.name.name]
            repositories = model.repository.get_app_search(
                search_query, username=username, search_fields=fields, limit=limit
            )
            if not repositories:
                return []

            repo_query = (
                Repository.select(Repository, Namespace.username)
                .join(Namespace, on=(Repository.namespace_user == Namespace.id))
                .where(Repository.id << [repo.id for repo in repositories])
            )
        else:
            repo_query = (
                Repository.select(Repository, Namespace.username)
                .join(Namespace, on=(Repository.namespace_user == Namespace.id))
                .where(
                    Repository.visibility == model.repository.get_public_repo_visibility(),
                    Repository.kind == Repository.kind.get_id("application"),
                )
            )

        if namespace:
            repo_query = repo_query.where(Namespace.username == namespace)

    repo_query = repo_query.where(Repository.state != RepositoryState.MARKED_FOR_DELETION)

    tag_query = (
        Tag.select()
        .where(Tag.tag_kind == Tag.tag_kind.get_id("release"))
        .order_by(Tag.lifetime_start)
    )

    if media_type:
        tag_query = tag_model.filter_tags_by_media_type(tag_query, media_type, models_ref)

    tag_query = tag_model.tag_is_alive(tag_query, Tag)
    query = prefetch(repo_query, tag_query)
    return query
