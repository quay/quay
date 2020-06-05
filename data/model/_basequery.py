import logging

from peewee import fn, PeeweeException
from cachetools.func import lru_cache

from datetime import datetime, timedelta

from data.model import DataModelException, config
from data.readreplica import ReadOnlyModeException
from data.database import (
    Repository,
    RepositoryState,
    User,
    Team,
    TeamMember,
    RepositoryPermission,
    TeamRole,
    Namespace,
    Visibility,
    ImageStorage,
    Image,
    RepositoryKind,
    db_for_update,
    db_count_estimator,
    db,
)
from functools import reduce

logger = logging.getLogger(__name__)


def reduce_as_tree(queries_to_reduce):
    """
    This method will split a list of queries into halves recursively until we reach individual
    queries, at which point it will start unioning the queries, or the already unioned subqueries.

    This works around a bug in peewee SQL generation where reducing linearly generates a chain of
    queries that will exceed the recursion depth limit when it has around 80 queries.
    """
    mid = len(queries_to_reduce) // 2

    left = queries_to_reduce[:mid]
    right = queries_to_reduce[mid:]

    to_reduce_right = right[0]
    if len(right) > 1:
        to_reduce_right = reduce_as_tree(right)

    if len(left) > 1:
        to_reduce_left = reduce_as_tree(left)
    elif len(left) == 1:
        to_reduce_left = left[0]
    else:
        return to_reduce_right

    return to_reduce_left.union_all(to_reduce_right)


def get_existing_repository(namespace_name, repository_name, for_update=False, kind_filter=None):
    query = (
        Repository.select(Repository, Namespace)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
        .where(Repository.state != RepositoryState.MARKED_FOR_DELETION)
    )

    if kind_filter:
        query = (
            query.switch(Repository).join(RepositoryKind).where(RepositoryKind.name == kind_filter)
        )

    if for_update:
        query = db_for_update(query)

    return query.get()


@lru_cache(maxsize=1)
def get_public_repo_visibility():
    return Visibility.get(name="public")


def _lookup_team_role(name):
    return _lookup_team_roles()[name]


@lru_cache(maxsize=1)
def _lookup_team_roles():
    return {role.name: role for role in TeamRole.select()}


def filter_to_repos_for_user(
    query, user_id=None, namespace=None, repo_kind="image", include_public=True, start_id=None
):
    if not include_public and not user_id:
        return Repository.select().where(Repository.id == "-1")

    # Filter on the type of repository.
    if repo_kind is not None:
        try:
            query = query.where(Repository.kind == Repository.kind.get_id(repo_kind))
        except RepositoryKind.DoesNotExist:
            raise DataModelException("Unknown repository kind")

    # Add the start ID if necessary.
    if start_id is not None:
        query = query.where(Repository.id >= start_id)

    # Add a namespace filter if necessary.
    if namespace:
        query = query.where(Namespace.username == namespace)

    # Build a set of queries that, when unioned together, return the full set of visible repositories
    # for the filters specified.
    queries = []

    if include_public:
        queries.append(query.where(Repository.visibility == get_public_repo_visibility()))

    if user_id is not None:
        AdminTeam = Team.alias()
        AdminTeamMember = TeamMember.alias()

        # Add repositories in which the user has permission.
        queries.append(
            query.switch(RepositoryPermission).where(RepositoryPermission.user == user_id)
        )

        # Add repositories in which the user is a member of a team that has permission.
        queries.append(
            query.switch(RepositoryPermission)
            .join(Team)
            .join(TeamMember)
            .where(TeamMember.user == user_id)
        )

        # Add repositories under namespaces in which the user is the org admin.
        queries.append(
            query.switch(Repository)
            .join(AdminTeam, on=(Repository.namespace_user == AdminTeam.organization))
            .join(AdminTeamMember, on=(AdminTeam.id == AdminTeamMember.team))
            .where(AdminTeam.role == _lookup_team_role("admin"))
            .where(AdminTeamMember.user == user_id)
        )

    return reduce(lambda l, r: l | r, queries)


def get_user_organizations(username):
    UserAlias = User.alias()
    return (
        User.select()
        .distinct()
        .join(Team)
        .join(TeamMember)
        .join(UserAlias, on=(UserAlias.id == TeamMember.user))
        .where(User.organization == True, UserAlias.username == username)
    )


def calculate_image_aggregate_size(ancestors_str, image_size, parent_image):
    ancestors = ancestors_str.split("/")[1:-1]
    if not ancestors:
        return image_size

    if parent_image is None:
        raise DataModelException("Could not load parent image")

    ancestor_size = parent_image.aggregate_size
    if ancestor_size is not None:
        return ancestor_size + image_size

    # Fallback to a slower path if the parent doesn't have an aggregate size saved.
    # TODO: remove this code if/when we do a full backfill.
    ancestor_size = (
        ImageStorage.select(fn.Sum(ImageStorage.image_size))
        .join(Image)
        .where(Image.id << ancestors)
        .scalar()
    )
    if ancestor_size is None:
        return None

    return ancestor_size + image_size


def update_last_accessed(token_or_user):
    """
    Updates the `last_accessed` field on the given token or user.

    If the existing field's value is within the configured threshold, the update is skipped.
    """
    if not config.app_config.get("FEATURE_USER_LAST_ACCESSED"):
        return

    threshold = timedelta(seconds=config.app_config.get("LAST_ACCESSED_UPDATE_THRESHOLD_S", 120))
    if (
        token_or_user.last_accessed is not None
        and datetime.utcnow() - token_or_user.last_accessed < threshold
    ):
        # Skip updating, as we don't want to put undue pressure on the database.
        return

    model_class = token_or_user.__class__
    last_accessed = datetime.utcnow()

    try:
        (
            model_class.update(last_accessed=last_accessed)
            .where(model_class.id == token_or_user.id)
            .execute()
        )
        token_or_user.last_accessed = last_accessed
    except ReadOnlyModeException:
        pass
    except PeeweeException as ex:
        # If there is any form of DB exception, only fail if strict logging is enabled.
        strict_logging_disabled = config.app_config.get("ALLOW_PULLS_WITHOUT_STRICT_LOGGING")
        if strict_logging_disabled:
            data = {
                "exception": ex,
                "token_or_user": token_or_user.id,
                "class": str(model_class),
            }

            logger.exception("update last_accessed for token/user failed", extra=data)
        else:
            raise


def estimated_row_count(model_cls):
    """ Returns the estimated number of rows in the given model. If available, uses engine-specific
        estimation (which is very fast) and otherwise falls back to .count()
    """
    return db_count_estimator(model_cls, db)
