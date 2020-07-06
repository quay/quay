"""
Conduct searches against all registry context.
"""

import features

from endpoints.api import (
    ApiResource,
    parse_args,
    query_param,
    nickname,
    resource,
    require_scope,
    path_param,
    internal_only,
    Unauthorized,
    InvalidRequest,
    show_if,
)
from data.database import Repository
from data import model
from data.registry_model import registry_model
from auth.permissions import (
    OrganizationMemberPermission,
    ReadRepositoryPermission,
    UserAdminPermission,
    AdministerOrganizationPermission,
    ReadRepositoryPermission,
)
from auth.auth_context import get_authenticated_user
from auth import scopes
from app import app, avatar, authentication
from flask import abort
from operator import itemgetter
from stringscore import liquidmetal
from util.names import parse_robot_username
from util.parsing import truthy_bool

from text_unidecode import unidecode
import math


ENTITY_SEARCH_SCORE = 1
TEAM_SEARCH_SCORE = 2
REPOSITORY_SEARCH_SCORE = 4


@resource("/v1/entities/link/<username>")
@internal_only
class LinkExternalEntity(ApiResource):
    """
    Resource for linking external entities to internal users.
    """

    @nickname("linkExternalUser")
    def post(self, username):
        if not authentication.federated_service:
            abort(404)

        # Only allowed if there is a logged in user.
        if not get_authenticated_user():
            raise Unauthorized()

        # Try to link the user with the given *external* username, to an internal record.
        (user, err_msg) = authentication.link_user(username)
        if user is None:
            raise InvalidRequest(err_msg, payload={"username": username})

        return {
            "entity": {
                "name": user.username,
                "kind": "user",
                "is_robot": False,
                "avatar": avatar.get_data_for_user(user),
            }
        }


@resource("/v1/entities/<prefix>")
class EntitySearch(ApiResource):
    """
    Resource for searching entities.
    """

    @path_param("prefix", "The prefix of the entities being looked up")
    @parse_args()
    @query_param(
        "namespace", "Namespace to use when querying for org entities.", type=str, default=""
    )
    @query_param("includeTeams", "Whether to include team names.", type=truthy_bool, default=False)
    @query_param("includeOrgs", "Whether to include orgs names.", type=truthy_bool, default=False)
    @nickname("getMatchingEntities")
    def get(self, prefix, parsed_args):
        """
        Get a list of entities that match the specified prefix.
        """

        # Ensure we don't have any unicode characters in the search, as it breaks the search. Nothing
        # being searched can have unicode in it anyway, so this is a safe operation.
        prefix = unidecode(prefix).replace(" ", "").lower()

        teams = []
        org_data = []

        namespace_name = parsed_args["namespace"]
        robot_namespace = None
        organization = None

        try:
            organization = model.organization.get_organization(namespace_name)

            # namespace name was an org
            permission = OrganizationMemberPermission(namespace_name)
            if permission.can():
                robot_namespace = namespace_name

                if parsed_args["includeTeams"]:
                    teams = model.team.get_matching_teams(prefix, organization)

                if (
                    parsed_args["includeOrgs"]
                    and AdministerOrganizationPermission(namespace_name)
                    and namespace_name.startswith(prefix)
                ):
                    org_data = [
                        {
                            "name": namespace_name,
                            "kind": "org",
                            "is_org_member": True,
                            "avatar": avatar.get_data_for_org(organization),
                        }
                    ]

        except model.organization.InvalidOrganizationException:
            # namespace name was a user
            user = get_authenticated_user()
            if user and user.username == namespace_name:
                # Check if there is admin user permissions (login only)
                admin_permission = UserAdminPermission(user.username)
                if admin_permission.can():
                    robot_namespace = namespace_name

        # Lookup users in the database for the prefix query.
        users = model.user.get_matching_users(
            prefix,
            robot_namespace,
            organization,
            limit=10,
            exact_matches_only=not features.PARTIAL_USER_AUTOCOMPLETE,
        )

        # Lookup users via the user system for the prefix query. We'll filter out any users that
        # already exist in the database.
        external_users, federated_id, _ = authentication.query_users(prefix, limit=10)
        filtered_external_users = []
        if external_users and federated_id is not None:
            users = list(users)
            user_ids = [user.id for user in users]

            # Filter the users if any are already found via the database. We do so by looking up all
            # the found users in the federated user system.
            federated_query = model.user.get_federated_logins(user_ids, federated_id)
            found = {result.service_ident for result in federated_query}
            filtered_external_users = [
                user for user in external_users if not user.username in found
            ]

        def entity_team_view(team):
            result = {
                "name": team.name,
                "kind": "team",
                "is_org_member": True,
                "avatar": avatar.get_data_for_team(team),
            }
            return result

        def user_view(user):
            user_json = {
                "name": user.username,
                "kind": "user",
                "is_robot": user.robot,
                "avatar": avatar.get_data_for_user(user),
            }

            if organization is not None:
                user_json["is_org_member"] = user.robot or user.is_org_member

            return user_json

        def external_view(user):
            result = {
                "name": user.username,
                "kind": "external",
                "title": user.email or "",
                "avatar": avatar.get_data_for_external_user(user),
            }
            return result

        team_data = [entity_team_view(team) for team in teams]
        user_data = [user_view(user) for user in users]
        external_data = [external_view(user) for user in filtered_external_users]

        return {"results": team_data + user_data + org_data + external_data}


def search_entity_view(username, entity, get_short_name=None):
    kind = "user"
    title = "user"
    avatar_data = avatar.get_data_for_user(entity)
    href = "/user/" + entity.username

    if entity.organization:
        kind = "organization"
        title = "org"
        avatar_data = avatar.get_data_for_org(entity)
        href = "/organization/" + entity.username
    elif entity.robot:
        parts = parse_robot_username(entity.username)
        if parts[0] == username:
            href = "/user/" + username + "?tab=robots&showRobot=" + entity.username
        else:
            href = "/organization/" + parts[0] + "?tab=robots&showRobot=" + entity.username

        kind = "robot"
        title = "robot"
        avatar_data = None

    data = {
        "title": title,
        "kind": kind,
        "avatar": avatar_data,
        "name": entity.username,
        "score": ENTITY_SEARCH_SCORE,
        "href": href,
    }

    if get_short_name:
        data["short_name"] = get_short_name(entity.username)

    return data


def conduct_team_search(username, query, encountered_teams, results):
    """
    Finds the matching teams where the user is a member.
    """
    matching_teams = model.team.get_matching_user_teams(query, get_authenticated_user(), limit=5)
    for team in matching_teams:
        if team.id in encountered_teams:
            continue

        encountered_teams.add(team.id)

        results.append(
            {
                "kind": "team",
                "name": team.name,
                "organization": search_entity_view(username, team.organization),
                "avatar": avatar.get_data_for_team(team),
                "score": TEAM_SEARCH_SCORE,
                "href": "/organization/" + team.organization.username + "/teams/" + team.name,
            }
        )


def conduct_admined_team_search(username, query, encountered_teams, results):
    """
    Finds matching teams in orgs admined by the user.
    """
    matching_teams = model.team.get_matching_admined_teams(query, get_authenticated_user(), limit=5)
    for team in matching_teams:
        if team.id in encountered_teams:
            continue

        encountered_teams.add(team.id)

        results.append(
            {
                "kind": "team",
                "name": team.name,
                "organization": search_entity_view(username, team.organization),
                "avatar": avatar.get_data_for_team(team),
                "score": TEAM_SEARCH_SCORE,
                "href": "/organization/" + team.organization.username + "/teams/" + team.name,
            }
        )


def conduct_repo_search(username, query, results, offset=0, limit=5):
    """
    Finds matching repositories.
    """
    matching_repos = model.repository.get_filtered_matching_repositories(
        query, username, limit=limit, repo_kind=None, offset=offset
    )

    for repo in matching_repos:
        # TODO: make sure the repo.kind.name doesn't cause extra queries
        results.append(repo_result_view(repo, username))


def conduct_namespace_search(username, query, results):
    """
    Finds matching users and organizations.
    """
    matching_entities = model.user.get_matching_user_namespaces(query, username, limit=5)
    for entity in matching_entities:
        results.append(search_entity_view(username, entity))


def conduct_robot_search(username, query, results):
    """
    Finds matching robot accounts.
    """

    def get_short_name(name):
        return parse_robot_username(name)[1]

    matching_robots = model.user.get_matching_robots(query, username, limit=5)
    for robot in matching_robots:
        results.append(search_entity_view(username, robot, get_short_name))


def repo_result_view(repo, username, last_modified=None, stars=None, popularity=None):
    kind = (
        "application" if Repository.kind.get_name(repo.kind_id) == "application" else "repository"
    )
    view = {
        "kind": kind,
        "title": "app" if kind == "application" else "repo",
        "namespace": search_entity_view(username, repo.namespace_user),
        "name": repo.name,
        "description": repo.description,
        "is_public": model.repository.is_repository_public(repo),
        "score": REPOSITORY_SEARCH_SCORE,
        "href": "/" + kind + "/" + repo.namespace_user.username + "/" + repo.name,
    }

    if last_modified is not None:
        view["last_modified"] = last_modified

    if stars is not None:
        view["stars"] = stars

    if popularity is not None:
        view["popularity"] = popularity

    return view


@resource("/v1/find/all")
class ConductSearch(ApiResource):
    """
    Resource for finding users, repositories, teams, etc.
    """

    @parse_args()
    @query_param("query", "The search query.", type=str, default="")
    @require_scope(scopes.READ_REPO)
    @nickname("conductSearch")
    def get(self, parsed_args):
        """
        Get a list of entities and resources that match the specified query.
        """
        query = parsed_args["query"]
        if not query:
            return {"results": []}

        username = None
        results = []

        if get_authenticated_user():
            username = get_authenticated_user().username

            # Search for teams.
            encountered_teams = set()
            conduct_team_search(username, query, encountered_teams, results)
            conduct_admined_team_search(username, query, encountered_teams, results)

            # Search for robot accounts.
            conduct_robot_search(username, query, results)

        # Search for repos.
        conduct_repo_search(username, query, results)

        # Search for users and orgs.
        conduct_namespace_search(username, query, results)

        # Modify the results' scores via how close the query term is to each result's name.
        for result in results:
            name = result.get("short_name", result["name"])
            lm_score = liquidmetal.score(name, query) or 0.5
            result["score"] = result["score"] * lm_score

        return {"results": sorted(results, key=itemgetter("score"), reverse=True)}


MAX_PER_PAGE = app.config.get("SEARCH_RESULTS_PER_PAGE", 10)
MAX_RESULT_PAGE_COUNT = app.config.get("SEARCH_MAX_RESULT_PAGE_COUNT", 10)


@resource("/v1/find/repositories")
class ConductRepositorySearch(ApiResource):
    """
    Resource for finding repositories.
    """

    @parse_args()
    @query_param("query", "The search query.", type=str, default="")
    @query_param("page", "The page.", type=int, default=1)
    @query_param(
        "includeUsage", "Whether to include usage metadata", type=truthy_bool, default=False
    )
    @nickname("conductRepoSearch")
    def get(self, parsed_args):
        """
        Get a list of apps and repositories that match the specified query.
        """
        query = parsed_args["query"]
        page = min(max(1, parsed_args["page"]), MAX_RESULT_PAGE_COUNT)
        offset = (page - 1) * MAX_PER_PAGE
        limit = MAX_PER_PAGE + 1

        username = get_authenticated_user().username if get_authenticated_user() else None

        # Lookup matching repositories.
        matching_repos = list(
            model.repository.get_filtered_matching_repositories(
                query, username, repo_kind=None, limit=limit, offset=offset
            )
        )

        assert len(matching_repos) <= limit
        has_additional = len(matching_repos) > MAX_PER_PAGE
        matching_repos = matching_repos[0:MAX_PER_PAGE]

        # Load secondary information such as last modified time, star count and action count.
        last_modified_map = None
        star_map = None
        action_sum_map = None
        if parsed_args["includeUsage"]:
            repository_ids = [repo.id for repo in matching_repos]
            last_modified_map = registry_model.get_most_recent_tag_lifetime_start(matching_repos)
            star_map = model.repository.get_stars(repository_ids)
            action_sum_map = model.log.get_repositories_action_sums(repository_ids)

        # Build the results list.
        results = [
            repo_result_view(
                repo,
                username,
                last_modified_map.get(repo.id) if last_modified_map is not None else None,
                star_map.get(repo.id, 0) if star_map is not None else None,
                float(action_sum_map.get(repo.id, 0)) if action_sum_map is not None else None,
            )
            for repo in matching_repos
        ]

        return {
            "results": results,
            "has_additional": has_additional,
            "page": page,
            "page_size": MAX_PER_PAGE,
            "start_index": offset,
        }
