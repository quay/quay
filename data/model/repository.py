import logging
import random
import json
import uuid

from enum import Enum
from datetime import timedelta, datetime
from peewee import Case, JOIN, fn, SQL, IntegrityError
from cachetools.func import ttl_cache

from data.model import (
    config,
    DataModelException,
    db_transaction,
    storage,
    permission,
    oci,
    _basequery,
)
from data.database import (
    Repository,
    RepositoryState,
    DeletedRepository,
    Namespace,
    RepositoryTag,
    Star,
    Image,
    ImageStorage,
    User,
    Visibility,
    RepositoryPermission,
    RepositoryActionCount,
    Role,
    RepositoryAuthorizedEmail,
    Label,
    db_for_update,
    get_epoch_timestamp,
    db_random_func,
    db_concat_func,
    RepositorySearchScore,
    RepositoryKind,
    ApprTag,
    ManifestLegacyImage,
    Manifest,
    ManifestChild,
    ExternalNotificationEvent,
    RepositoryNotification,
)
from data.text import prefix_search
from util.itertoolrecipes import take

logger = logging.getLogger(__name__)
SEARCH_FIELDS = Enum("SearchFields", ["name", "description"])


class RepoStateConfigException(Exception):
    """
    Repository.state value requires further configuration to operate.
    """

    pass


def lookup_secscan_notification_severities(repository_id):
    """
    Returns the configured security scanner notification severities for the repository
    or None if none.
    """

    try:
        repo = Repository.get(id=repository_id)
    except Repository.DoesNotExist:
        return None

    event_kind = ExternalNotificationEvent.get(name="vulnerability_found")
    for event in RepositoryNotification.select().where(
        RepositoryNotification.repository == repository_id,
        RepositoryNotification.event == event_kind,
    ):
        severity = json.loads(event.event_config_json).get("vulnerability", {}).get("priority")
        if severity:
            yield severity


def get_max_id():
    """
    Gets the maximum id for repository.
    """
    return Repository.select(fn.Max(Repository.id)).scalar()


def get_min_id():
    """
    Gets the minimum id for repository.
    """
    return Repository.select(fn.Min(Repository.id)).scalar()


def get_repository_count():
    """ Returns the count of repositories. """
    return Repository.select().count()


def get_repo_kind_name(repo):
    return Repository.kind.get_name(repo.kind_id)


def get_estimated_repository_count():
    return _basequery.estimated_row_count(Repository)


def get_public_repo_visibility():
    return _basequery.get_public_repo_visibility()


class _RepositoryExistsException(Exception):
    """Exception raised if a repository exists in create_repository. Used to breakout of
    the transaction.
    """

    def __init__(self, internal_exception):
        self.internal_exception = internal_exception


def create_repository(
    namespace, name, creating_user, visibility="private", repo_kind="image", description=None
):
    namespace_user = User.get(username=namespace)
    yesterday = datetime.now() - timedelta(days=1)

    try:
        with db_transaction():
            # Check if the repository exists to avoid an IntegrityError if possible.
            existing = get_repository(namespace, name)
            if existing is not None:
                return None

            try:
                repo = Repository.create(
                    name=name,
                    visibility=Repository.visibility.get_id(visibility),
                    namespace_user=namespace_user,
                    kind=Repository.kind.get_id(repo_kind),
                    description=description,
                )
            except IntegrityError as ie:
                raise _RepositoryExistsException(ie)

            RepositoryActionCount.create(repository=repo, count=0, date=yesterday)
            RepositorySearchScore.create(repository=repo, score=0)

            # Note: We put the admin create permission under the transaction to ensure it is created.
            if creating_user and not creating_user.organization:
                admin = Role.get(name="admin")
                RepositoryPermission.create(user=creating_user, repository=repo, role=admin)
    except _RepositoryExistsException as ree:
        try:
            return Repository.get(namespace_user=namespace_user, name=name)
        except Repository.DoesNotExist:
            logger.error(
                "Got integrity error when trying to create repository %s/%s: %s",
                namespace,
                name,
                ree.internal_exception,
            )
            return None

    # Apply default permissions (only occurs for repositories under organizations)
    if creating_user and not creating_user.organization and creating_user.username != namespace:
        permission.apply_default_permissions(repo, creating_user)

    return repo


def get_repository(namespace_name, repository_name, kind_filter=None):
    try:
        return _basequery.get_existing_repository(
            namespace_name, repository_name, kind_filter=kind_filter
        )
    except Repository.DoesNotExist:
        return None


def get_or_create_repository(
    namespace, name, creating_user, visibility="private", repo_kind="image"
):
    repo = get_repository(namespace, name, repo_kind)
    if repo is None:
        repo = create_repository(namespace, name, creating_user, visibility, repo_kind)
    return repo


@ttl_cache(maxsize=1, ttl=600)
def _get_gc_expiration_policies():
    policy_tuples_query = (
        Namespace.select(Namespace.removed_tag_expiration_s)
        .distinct()
        .limit(100)  # This sucks but it's the only way to limit memory
        .tuples()
    )
    return [policy[0] for policy in policy_tuples_query]


def get_random_gc_policy():
    """
    Return a single random policy from the database to use when garbage collecting or None if none
    available.
    """
    policies = _get_gc_expiration_policies()
    if not policies:
        return None

    return random.choice(policies)


def star_repository(user, repository):
    """
    Stars a repository.
    """
    star = Star.create(user=user.id, repository=repository.id)
    star.save()


def unstar_repository(user, repository):
    """
    Unstars a repository.
    """
    try:
        (Star.delete().where(Star.repository == repository.id, Star.user == user.id).execute())
    except Star.DoesNotExist:
        raise DataModelException("Star not found.")


def set_trust(repo, trust_enabled):
    repo.trust_enabled = trust_enabled
    repo.save()


def set_description(repo, description):
    repo.description = description
    repo.save()


def get_user_starred_repositories(user, kind_filter="image"):
    """
    Retrieves all of the repositories a user has starred.
    """
    try:
        repo_kind = Repository.kind.get_id(kind_filter)
    except RepositoryKind.DoesNotExist:
        raise DataModelException("Unknown kind of repository")

    query = (
        Repository.select(Repository, User, Visibility, Repository.id.alias("rid"))
        .join(Star)
        .switch(Repository)
        .join(User)
        .switch(Repository)
        .join(Visibility)
        .where(Star.user == user, Repository.kind == repo_kind)
        .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
    )

    return query


def repository_is_starred(user, repository):
    """
    Determines whether a user has starred a repository or not.
    """
    try:
        (Star.select().where(Star.repository == repository.id, Star.user == user.id).get())
        return True
    except Star.DoesNotExist:
        return False


def get_stars(repository_ids):
    """
    Returns a map from repository ID to the number of stars for each repository in the given
    repository IDs list.
    """
    if not repository_ids:
        return {}

    tuples = (
        Star.select(Star.repository, fn.Count(Star.id))
        .where(Star.repository << repository_ids)
        .group_by(Star.repository)
        .tuples()
    )

    star_map = {}
    for record in tuples:
        star_map[record[0]] = record[1]

    return star_map


def get_visible_repositories(
    username, namespace=None, kind_filter="image", include_public=False, start_id=None, limit=None
):
    """
    Returns the repositories visible to the given user (if any).
    """
    if not include_public and not username:
        # Short circuit by returning a query that will find no repositories. We need to return a query
        # here, as it will be modified by other queries later on.
        return Repository.select(Repository.id.alias("rid")).where(Repository.id == -1)

    query = (
        Repository.select(
            Repository.name,
            Repository.id.alias("rid"),
            Repository.description,
            Namespace.username,
            Repository.visibility,
            Repository.kind,
            Repository.state,
        )
        .switch(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
    )

    user_id = None
    if username:
        # Note: We only need the permissions table if we will filter based on a user's permissions.
        query = query.switch(Repository).distinct().join(RepositoryPermission, JOIN.LEFT_OUTER)
        found_namespace = _get_namespace_user(username)
        if not found_namespace:
            return Repository.select(Repository.id.alias("rid")).where(Repository.id == -1)

        user_id = found_namespace.id

    query = _basequery.filter_to_repos_for_user(
        query, user_id, namespace, kind_filter, include_public, start_id=start_id
    )

    if limit is not None:
        query = query.limit(limit).order_by(SQL("rid"))

    return query


def get_app_repository(namespace_name, repository_name):
    """
    Find an application repository.
    """
    try:
        return _basequery.get_existing_repository(
            namespace_name, repository_name, kind_filter="application"
        )
    except Repository.DoesNotExist:
        return None


def get_app_search(lookup, search_fields=None, username=None, limit=50):
    if search_fields is None:
        search_fields = set([SEARCH_FIELDS.name.name])

    return get_filtered_matching_repositories(
        lookup,
        filter_username=username,
        search_fields=search_fields,
        repo_kind="application",
        offset=0,
        limit=limit,
    )


def _get_namespace_user(username):
    try:
        return User.get(username=username)
    except User.DoesNotExist:
        return None


def get_filtered_matching_repositories(
    lookup_value, filter_username=None, repo_kind="image", offset=0, limit=25, search_fields=None
):
    """
    Returns an iterator of all repositories matching the given lookup value, with optional filtering
    to a specific user.

    If the user is unspecified, only public repositories will be returned.
    """
    if search_fields is None:
        search_fields = set([SEARCH_FIELDS.description.name, SEARCH_FIELDS.name.name])

    # Build the unfiltered search query.
    unfiltered_query = _get_sorted_matching_repositories(
        lookup_value,
        repo_kind=repo_kind,
        search_fields=search_fields,
        include_private=filter_username is not None,
        ids_only=filter_username is not None,
    )

    # Add a filter to the iterator, if necessary.
    if filter_username is not None:
        filter_user = _get_namespace_user(filter_username)
        if filter_user is None:
            return []

        # NOTE: We add the offset to the limit here to ensure we have enough results
        # for the take's we conduct below.
        iterator = _filter_repositories_visible_to_user(
            unfiltered_query, filter_user.id, offset + limit, repo_kind
        )
        if offset > 0:
            take(offset, iterator)

        # Return the results.
        return list(take(limit, iterator))

    return list(unfiltered_query.offset(offset).limit(limit))


def _filter_repositories_visible_to_user(unfiltered_query, filter_user_id, limit, repo_kind):
    encountered = set()
    chunk_count = limit * 2
    unfiltered_page = 0
    iteration_count = 0

    while iteration_count < 10:  # Just to be safe
        # Find the next chunk's worth of repository IDs, paginated by the chunk size.
        unfiltered_page = unfiltered_page + 1
        found_ids = [r.id for r in unfiltered_query.paginate(unfiltered_page, chunk_count)]

        # Make sure we haven't encountered these results before. This code is used to handle
        # the case where we've previously seen a result, as pagination is not necessary
        # stable in SQL databases.
        unfiltered_repository_ids = set(found_ids)
        new_unfiltered_ids = unfiltered_repository_ids - encountered
        if not new_unfiltered_ids:
            break

        encountered.update(new_unfiltered_ids)

        # Filter the repositories found to only those visible to the current user.
        query = (
            Repository.select(Repository, Namespace)
            .distinct()
            .join(Namespace, on=(Namespace.id == Repository.namespace_user))
            .switch(Repository)
            .join(RepositoryPermission)
            .where(Repository.id << list(new_unfiltered_ids))
        )

        filtered = _basequery.filter_to_repos_for_user(query, filter_user_id, repo_kind=repo_kind)

        # Sort the filtered repositories by their initial order.
        all_filtered_repos = list(filtered)
        all_filtered_repos.sort(key=lambda repo: found_ids.index(repo.id))

        # Yield the repositories in sorted order.
        for filtered_repo in all_filtered_repos:
            yield filtered_repo

        # If the number of found IDs is less than the chunk count, then we're done.
        if len(found_ids) < chunk_count:
            break

        iteration_count = iteration_count + 1


def _get_sorted_matching_repositories(
    lookup_value, repo_kind="image", include_private=False, search_fields=None, ids_only=False
):
    """
    Returns a query of repositories matching the given lookup string, with optional inclusion of
    private repositories.

    Note that this method does *not* filter results based on visibility to users.
    """
    select_fields = [Repository.id] if ids_only else [Repository, Namespace]

    if not lookup_value:
        # This is a generic listing of repositories. Simply return the sorted repositories based
        # on RepositorySearchScore.
        query = (
            Repository.select(*select_fields)
            .join(RepositorySearchScore)
            .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
            .order_by(RepositorySearchScore.score.desc(), RepositorySearchScore.id)
        )
    else:
        if search_fields is None:
            search_fields = set([SEARCH_FIELDS.description.name, SEARCH_FIELDS.name.name])

        # Always search at least on name (init clause)
        clause = Repository.name.match(lookup_value)
        computed_score = RepositorySearchScore.score.alias("score")

        # If the description field is in the search fields, then we need to compute a synthetic score
        # to discount the weight of the description more than the name.
        if SEARCH_FIELDS.description.name in search_fields:
            clause = Repository.description.match(lookup_value) | clause
            cases = [
                (Repository.name.match(lookup_value), 100 * RepositorySearchScore.score),
            ]
            computed_score = Case(None, cases, RepositorySearchScore.score).alias("score")

        select_fields.append(computed_score)
        query = (
            Repository.select(*select_fields)
            .join(RepositorySearchScore)
            .where(clause)
            .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
            .order_by(SQL("score").desc(), RepositorySearchScore.id)
        )

    if repo_kind is not None:
        query = query.where(Repository.kind == Repository.kind.get_id(repo_kind))

    if not include_private:
        query = query.where(Repository.visibility == _basequery.get_public_repo_visibility())

    if not ids_only:
        query = query.switch(Repository).join(
            Namespace, on=(Namespace.id == Repository.namespace_user)
        )

    return query


def lookup_repository(repo_id):
    try:
        return Repository.get(Repository.id == repo_id)
    except Repository.DoesNotExist:
        return None


def repository_visibility_name(repository):
    return "public" if is_repository_public(repository) else "private"


def is_repository_public(repository):
    return repository.visibility_id == _basequery.get_public_repo_visibility().id


def repository_is_public(namespace_name, repository_name):
    try:
        (
            Repository.select()
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .switch(Repository)
            .join(Visibility)
            .where(
                Namespace.username == namespace_name,
                Repository.name == repository_name,
                Visibility.name == "public",
            )
            .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
            .get()
        )
        return True
    except Repository.DoesNotExist:
        return False


def set_repository_visibility(repo, visibility):
    visibility_obj = Visibility.get(name=visibility)
    if not visibility_obj:
        return

    repo.visibility = visibility_obj
    repo.save()


def get_email_authorized_for_repo(namespace, repository, email):
    try:
        return (
            RepositoryAuthorizedEmail.select(RepositoryAuthorizedEmail, Repository, Namespace)
            .join(Repository)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .where(
                Namespace.username == namespace,
                Repository.name == repository,
                RepositoryAuthorizedEmail.email == email,
            )
            .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
            .get()
        )
    except RepositoryAuthorizedEmail.DoesNotExist:
        return None


def create_email_authorization_for_repo(namespace_name, repository_name, email):
    try:
        repo = _basequery.get_existing_repository(namespace_name, repository_name)
    except Repository.DoesNotExist:
        raise DataModelException("Invalid repository %s/%s" % (namespace_name, repository_name))

    return RepositoryAuthorizedEmail.create(repository=repo, email=email, confirmed=False)


def confirm_email_authorization_for_repo(code):
    try:
        found = (
            RepositoryAuthorizedEmail.select(RepositoryAuthorizedEmail, Repository, Namespace)
            .join(Repository)
            .join(Namespace, on=(Repository.namespace_user == Namespace.id))
            .where(RepositoryAuthorizedEmail.code == code)
            .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
            .get()
        )
    except RepositoryAuthorizedEmail.DoesNotExist:
        raise DataModelException("Invalid confirmation code.")

    found.confirmed = True
    found.save()

    return found


def get_repository_state(namespace_name, repository_name):
    """
    Return the Repository State if the Repository exists.

    Otherwise, returns None.
    """
    repo = get_repository(namespace_name, repository_name)
    if repo:
        return repo.state

    return None


def set_repository_state(repo, state):
    repo.state = state
    repo.save()


def mark_repository_for_deletion(namespace_name, repository_name, repository_gc_queue):
    """
    Marks a repository for future deletion in the background.

    The repository will be renamed and hidden, and then deleted later by a worker.
    """
    repo = get_repository(namespace_name, repository_name)
    if not repo:
        return None

    with db_transaction():
        # Delete any stars for the repository.
        Star.delete().where(Star.repository == repo).execute()

        # Change the name and state of the repository.
        repo.name = str(uuid.uuid4())
        repo.state = RepositoryState.MARKED_FOR_DELETION
        repo.save()

        # Create a tracking row and a queueitem to delete the repository.
        marker = DeletedRepository.create(repository=repo, original_name=repository_name)

        # Add a queueitem to delete the repository.
        marker.queue_id = repository_gc_queue.put(
            [namespace_name, str(repo.id)],
            json.dumps(
                {
                    "marker_id": marker.id,
                    "original_name": repository_name,
                }
            ),
        )
        marker.save()

    # Run callbacks for the deleted repo.
    for callback in config.repo_cleanup_callbacks:
        callback(namespace_name, repository_name)

    return marker.id
