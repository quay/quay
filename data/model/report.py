from peewee import JOIN, SQL
from data.database import (
    Repository,
    RepositoryPermission,
    RepositoryState,
    Role,
    Team,
    TeamMember,
    TeamRole,
    User,
)


def organization_permission_report(
    org: User, page, page_size, members=True, collaborators=True, include_robots=True, raise_on_error=True
):
    """
    Creates a report of all permissions for an organization based on team membership or collaborator status. The report can be filtered to include only teams or collaborators, and can optionally exclude/include robots.

    Returns the report in the form of a list of dictionaries, where each dictionary represents a user and their permissions on a repository.
    """

    if not members and not collaborators:
        if raise_on_error:
            raise ValueError("Must include either team members or collaborators.")
        else:
            return None

    """
    This query is a bit complicated, so here's a breakdown of what it's doing:

    1. Select all users that are not organizations.
    2. Join the TeamMember table to get the team membership information.
    3. Join the Team table to get the team name.
    4. Join the RepositoryPermission table to get the repository permission information.
    5. Join the Repository table to get the repository name.
    6. Join the Role table to get the role name.
    7. Join the Organization table to get the organization name.
    8. Filter for teams that are defined in the organization.
    9. Filter out any users that are robots.
    10. Filter out any matches where the team role is member but there are no per-repository permission yet (because users in such teams effectively have no permissions on any repositories yet)
    11. Filter out any repositories that are marked for deletion.
    12. Order the results by username, team name, and repository name.

    The result of this query is a list of all permissions of users in the organization that are member of a team defined in this organization, and their per-repository permissions as a result of mapping the team role to the repositories, excluding any repositories that are marked for deletion and any record where the team role is member but there are no per-repository permissions yet.
    """

    Organization = User.alias()

    members_query = (
        User.select(
            User.username.alias("user_name"),
            User.creation_date.alias("user_creation_date"),
            User.enabled.alias("user_enabled"),
            Team.name.alias("team_name"),
            TeamRole.name.alias("team_role"),
            Repository.name.alias("repository_name"),
            Repository.state.alias("repository_state"),
            Role.name.alias("role"),
        )
        .join(TeamMember, JOIN.LEFT_OUTER)
        .join(Team, JOIN.LEFT_OUTER)
        .join(TeamRole, JOIN.LEFT_OUTER)
        .join(RepositoryPermission, JOIN.LEFT_OUTER, on=(RepositoryPermission.team == Team.id))
        .join(
            Repository,
            JOIN.LEFT_OUTER,
            on=(RepositoryPermission.repository == Repository.id),
        )
        .join(Role, JOIN.LEFT_OUTER, on=(Role.id == RepositoryPermission.role))
        .join(Organization, JOIN.LEFT_OUTER, on=(Team.organization == Organization.id))
        .where(User.organization == False)
        .where(Organization.username == org.username)
        .where(
                (Repository.id.is_null(True) & (TeamRole.name != "member")) | 
                (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
    )

    if not include_robots:
        members_query = members_query.where(User.robot == False)

    """
    This query is a less complicated, but for sake of comprehension here is what it's doing:

    1. Select all users that are not organizations.
    2. Join the RepositoryPermission table to get the repository permission information.
    3. Join the Repository table to get the repository name.
    4. Join the Role table to get the role name.
    5. Join the Organization table to get the organization name.
    6. Filter for repositorioes defined in the organization.
    7. Filter out any users that are robots.
    8. Filter out any matches where the team role is member but there are no per-repository permission yet (because users in such teams effectively have no permissions on any repositories yet)
    9. Filter out any repositories that are marked for deletion.
    10. Order the results by username and repository name.

    The result of this query is a list of all permissions of users in the organization that have directly been assigned permissions in any repository that is part of the given organizatron excluding any repositories that are marked for deletion. These are the so called "collaborators". These users are not necessarily part of any team defined in the organization.
    """

    collaborators_query = (
        User.select(
            User.username.alias("user_name"),
            User.creation_date.alias("user_creation_date"),
            User.enabled.alias("user_enabled"),
            SQL("NULL").alias("team_name"),
            SQL("NULL").alias("team_role"),
            Repository.name.alias("repository_name"),
            Repository.state.alias("repository_state"),
            Role.name.alias("role"),
        )
        .join(RepositoryPermission, JOIN.LEFT_OUTER, on=(RepositoryPermission.user == User.id))
        .join(
            Repository,
            JOIN.LEFT_OUTER,
            on=(RepositoryPermission.repository == Repository.id),
        )
        .join(Role, JOIN.LEFT_OUTER, on=(Role.id == RepositoryPermission.role))
        .join(Organization, JOIN.LEFT_OUTER, on=(Repository.namespace_user == Organization.id))
        .where(User.organization == False)
        .where(Organization.username == org.username)
        .where(
                Repository.id.is_null(True) | 
                (Repository.state != RepositoryState.MARKED_FOR_DELETION)
        )
    )

    if not include_robots:
        collaborators_query = collaborators_query.where(User.robot == False)

    if members and collaborators:
        report_query = members_query.union(collaborators_query)
    elif members:
        report_query = members_query
    else:
        report_query = collaborators_query

    report_query = report_query.order_by(SQL("user_name"), SQL("team_name"), SQL("repository_name"))

    report_query.limit(page_size + 1).offset((page - 1) * page_size)

    permissions = [result_dict for result_dict in report_query.dicts()]

    return permissions[0:page_size], len(permissions) > page_size