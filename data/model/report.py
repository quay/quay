from peewee import JOIN
from data.database import Repository, RepositoryPermission, Role, Team, TeamMember, TeamRole, User


def organization_permission_report(
    org: User, members=True, collaborators=True, include_robots=True, raise_on_error=True
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

    permissions = []

    if members:
        Organization = User.alias()
        members_query = (
            User.select(
                User.username,
                User.creation_date.alias("user_creation_date"),
                Team.name.alias("team_name"),
                TeamRole.name.alias("team_role"),
                Repository.name.alias("repository"),
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
            .where((User.organization == False) & (Organization.username == org.username))
            .order_by(User.username, Team.name, Repository.name)
        )

        if not include_robots:
            members_query = members_query.where(User.robot == False)

        permissions.extend([result_dict for result_dict in members_query.dicts()])

    if collaborators:
        Organization = User.alias()
        collaborators_query = (
            User.select(
                User.username,
                User.creation_date.alias("user_creation_date"),
                Repository.name.alias("repository"),
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
            .where((User.organization == False) & (Organization.username == org.username))
            .order_by(User.username, Repository.name)
        )

        if not include_robots:
            collaborators_query = collaborators_query.where(User.robot == False)

        permissions.extend([result_dict for result_dict in collaborators_query.dicts()])

    return permissions
