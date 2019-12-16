from peewee import JOIN

from data.database import (
    RepositoryPermission,
    User,
    Repository,
    Visibility,
    Role,
    TeamMember,
    PermissionPrototype,
    Team,
    TeamRole,
    Namespace,
)
from data.model import DataModelException, _basequery
from util.names import parse_robot_username


def list_team_permissions(team):
    return (
        RepositoryPermission.select(RepositoryPermission)
        .join(Repository)
        .join(Visibility)
        .switch(RepositoryPermission)
        .join(Role)
        .switch(RepositoryPermission)
        .where(RepositoryPermission.team == team)
    )


def list_robot_permissions(robot_name):
    return (
        RepositoryPermission.select(RepositoryPermission, User, Repository)
        .join(Repository)
        .join(Visibility)
        .switch(RepositoryPermission)
        .join(Role)
        .switch(RepositoryPermission)
        .join(User)
        .where(User.username == robot_name, User.robot == True)
    )


def list_organization_member_permissions(organization, limit_to_user=None):
    query = (
        RepositoryPermission.select(RepositoryPermission, Repository, User)
        .join(Repository)
        .switch(RepositoryPermission)
        .join(User)
        .where(Repository.namespace_user == organization)
    )

    if limit_to_user is not None:
        query = query.where(RepositoryPermission.user == limit_to_user)
    else:
        query = query.where(User.robot == False)

    return query


def get_all_user_repository_permissions(user):
    return _get_user_repo_permissions(user)


def get_user_repo_permissions(user, repo):
    return _get_user_repo_permissions(user, limit_to_repository_obj=repo)


def get_user_repository_permissions(user, namespace, repo_name):
    return _get_user_repo_permissions(user, limit_namespace=namespace, limit_repo_name=repo_name)


def _get_user_repo_permissions(
    user, limit_to_repository_obj=None, limit_namespace=None, limit_repo_name=None
):
    UserThroughTeam = User.alias()

    base_query = (
        RepositoryPermission.select(RepositoryPermission, Role, Repository, Namespace)
        .join(Role)
        .switch(RepositoryPermission)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .switch(RepositoryPermission)
    )

    if limit_to_repository_obj is not None:
        base_query = base_query.where(RepositoryPermission.repository == limit_to_repository_obj)
    elif limit_namespace and limit_repo_name:
        base_query = base_query.where(
            Repository.name == limit_repo_name, Namespace.username == limit_namespace
        )

    direct = base_query.clone().join(User).where(User.id == user)

    team = (
        base_query.clone()
        .join(Team)
        .join(TeamMember)
        .join(UserThroughTeam, on=(UserThroughTeam.id == TeamMember.user))
        .where(UserThroughTeam.id == user)
    )

    return direct | team


def delete_prototype_permission(org, uid):
    found = get_prototype_permission(org, uid)
    if not found:
        return None

    found.delete_instance()
    return found


def get_prototype_permission(org, uid):
    try:
        return PermissionPrototype.get(
            PermissionPrototype.org == org, PermissionPrototype.uuid == uid
        )
    except PermissionPrototype.DoesNotExist:
        return None


def get_prototype_permissions(org):
    ActivatingUser = User.alias()
    DelegateUser = User.alias()
    query = (
        PermissionPrototype.select()
        .where(PermissionPrototype.org == org)
        .join(
            ActivatingUser,
            JOIN.LEFT_OUTER,
            on=(ActivatingUser.id == PermissionPrototype.activating_user),
        )
        .join(
            DelegateUser, JOIN.LEFT_OUTER, on=(DelegateUser.id == PermissionPrototype.delegate_user)
        )
        .join(Team, JOIN.LEFT_OUTER, on=(Team.id == PermissionPrototype.delegate_team))
        .join(Role, JOIN.LEFT_OUTER, on=(Role.id == PermissionPrototype.role))
    )
    return query


def update_prototype_permission(org, uid, role_name):
    found = get_prototype_permission(org, uid)
    if not found:
        return None

    new_role = Role.get(Role.name == role_name)
    found.role = new_role
    found.save()
    return found


def add_prototype_permission(
    org, role_name, activating_user, delegate_user=None, delegate_team=None
):
    new_role = Role.get(Role.name == role_name)
    return PermissionPrototype.create(
        org=org,
        role=new_role,
        activating_user=activating_user,
        delegate_user=delegate_user,
        delegate_team=delegate_team,
    )


def get_org_wide_permissions(user, org_filter=None):
    Org = User.alias()
    team_with_role = Team.select(Team, Org, TeamRole).join(TeamRole)
    with_org = team_with_role.switch(Team).join(Org, on=(Team.organization == Org.id))
    with_user = with_org.switch(Team).join(TeamMember).join(User)

    if org_filter:
        with_user.where(Org.username == org_filter)

    return with_user.where(User.id == user, Org.organization == True)


def get_all_repo_teams(namespace_name, repository_name):
    return (
        RepositoryPermission.select(Team.name, Role.name, RepositoryPermission)
        .join(Team)
        .switch(RepositoryPermission)
        .join(Role)
        .switch(RepositoryPermission)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(Namespace.username == namespace_name, Repository.name == repository_name)
    )


def apply_default_permissions(repo_obj, creating_user_obj):
    org = repo_obj.namespace_user
    user_clause = (PermissionPrototype.activating_user == creating_user_obj) | (
        PermissionPrototype.activating_user >> None
    )

    team_protos = PermissionPrototype.select().where(
        PermissionPrototype.org == org, user_clause, PermissionPrototype.delegate_user >> None
    )

    def create_team_permission(team, repo, role):
        RepositoryPermission.create(team=team, repository=repo, role=role)

    __apply_permission_list(repo_obj, team_protos, "name", create_team_permission)

    user_protos = PermissionPrototype.select().where(
        PermissionPrototype.org == org, user_clause, PermissionPrototype.delegate_team >> None
    )

    def create_user_permission(user, repo, role):
        # The creating user always gets admin anyway
        if user.username == creating_user_obj.username:
            return

        RepositoryPermission.create(user=user, repository=repo, role=role)

    __apply_permission_list(repo_obj, user_protos, "username", create_user_permission)


def __apply_permission_list(repo, proto_query, name_property, create_permission_func):
    final_protos = {}
    for proto in proto_query:
        applies_to = proto.delegate_team or proto.delegate_user
        name = getattr(applies_to, name_property)
        # We will skip the proto if it is pre-empted by a more important proto
        if name in final_protos and proto.activating_user is None:
            continue

        # By this point, it is either a user specific proto, or there is no
        # proto yet, so we can safely assume it applies
        final_protos[name] = (applies_to, proto.role)

    for delegate, role in list(final_protos.values()):
        create_permission_func(delegate, repo, role)


def __entity_permission_repo_query(
    entity_id, entity_table, entity_id_property, namespace_name, repository_name
):
    """
    This method works for both users and teams.
    """

    return (
        RepositoryPermission.select(entity_table, Repository, Namespace, Role, RepositoryPermission)
        .join(entity_table)
        .switch(RepositoryPermission)
        .join(Role)
        .switch(RepositoryPermission)
        .join(Repository)
        .join(Namespace, on=(Repository.namespace_user == Namespace.id))
        .where(
            Repository.name == repository_name,
            Namespace.username == namespace_name,
            entity_id_property == entity_id,
        )
    )


def get_user_reponame_permission(username, namespace_name, repository_name):
    fetched = list(
        __entity_permission_repo_query(
            username, User, User.username, namespace_name, repository_name
        )
    )
    if not fetched:
        raise DataModelException("User does not have permission for repo.")

    return fetched[0]


def get_team_reponame_permission(team_name, namespace_name, repository_name):
    fetched = list(
        __entity_permission_repo_query(team_name, Team, Team.name, namespace_name, repository_name)
    )
    if not fetched:
        raise DataModelException("Team does not have permission for repo.")

    return fetched[0]


def delete_user_permission(username, namespace_name, repository_name):
    if username == namespace_name:
        raise DataModelException("Namespace owner must always be admin.")

    fetched = list(
        __entity_permission_repo_query(
            username, User, User.username, namespace_name, repository_name
        )
    )
    if not fetched:
        raise DataModelException("User does not have permission for repo.")

    fetched[0].delete_instance()


def delete_team_permission(team_name, namespace_name, repository_name):
    fetched = list(
        __entity_permission_repo_query(team_name, Team, Team.name, namespace_name, repository_name)
    )
    if not fetched:
        raise DataModelException("Team does not have permission for repo.")

    fetched[0].delete_instance()


def __set_entity_repo_permission(
    entity, permission_entity_property, namespace_name, repository_name, role_name
):
    repo = _basequery.get_existing_repository(namespace_name, repository_name)
    new_role = Role.get(Role.name == role_name)

    # Fetch any existing permission for this entity on the repo
    try:
        entity_attr = getattr(RepositoryPermission, permission_entity_property)
        perm = RepositoryPermission.get(
            entity_attr == entity, RepositoryPermission.repository == repo
        )
        perm.role = new_role
        perm.save()
        return perm
    except RepositoryPermission.DoesNotExist:
        set_entity_kwargs = {permission_entity_property: entity}
        new_perm = RepositoryPermission.create(repository=repo, role=new_role, **set_entity_kwargs)
        return new_perm


def set_user_repo_permission(username, namespace_name, repository_name, role_name):
    if username == namespace_name:
        raise DataModelException("Namespace owner must always be admin.")

    try:
        user = User.get(User.username == username)
    except User.DoesNotExist:
        raise DataModelException("Invalid username: %s" % username)

    if user.robot:
        parts = parse_robot_username(user.username)
        if not parts:
            raise DataModelException("Invalid robot: %s" % username)

        robot_namespace, _ = parts
        if robot_namespace != namespace_name:
            raise DataModelException(
                "Cannot add robot %s under namespace %s" % (username, namespace_name)
            )

    return __set_entity_repo_permission(user, "user", namespace_name, repository_name, role_name)


def set_team_repo_permission(team_name, namespace_name, repository_name, role_name):
    try:
        team = (
            Team.select()
            .join(User)
            .where(Team.name == team_name, User.username == namespace_name)
            .get()
        )
    except Team.DoesNotExist:
        raise DataModelException("No team %s in organization %s" % (team_name, namespace_name))

    return __set_entity_repo_permission(team, "team", namespace_name, repository_name, role_name)
