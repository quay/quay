import json
import re
import uuid

from datetime import datetime
from peewee import fn

from data.database import (
    Team,
    TeamMember,
    TeamRole,
    User,
    TeamMemberInvite,
    RepositoryPermission,
    TeamSync,
    LoginService,
    FederatedLogin,
    db_random_func,
    db_transaction,
)
from data.model import (
    DataModelException,
    InvalidTeamException,
    UserAlreadyInTeam,
    InvalidTeamMemberException,
    _basequery,
)
from data.text import prefix_search
from util.validation import validate_username
from util.morecollections import AttrDict


MIN_TEAMNAME_LENGTH = 2
MAX_TEAMNAME_LENGTH = 255

VALID_TEAMNAME_REGEX = r"^([a-z0-9]+(?:[._-][a-z0-9]+)*)$"


def validate_team_name(teamname):
    if not re.match(VALID_TEAMNAME_REGEX, teamname):
        return (False, "Namespace must match expression " + VALID_TEAMNAME_REGEX)

    length_match = len(teamname) >= MIN_TEAMNAME_LENGTH and len(teamname) <= MAX_TEAMNAME_LENGTH
    if not length_match:
        return (
            False,
            "Team must be between %s and %s characters in length"
            % (MIN_TEAMNAME_LENGTH, MAX_TEAMNAME_LENGTH),
        )

    return (True, "")


def create_team(name, org_obj, team_role_name, description=""):
    (teamname_valid, teamname_issue) = validate_team_name(name)
    if not teamname_valid:
        raise InvalidTeamException("Invalid team name %s: %s" % (name, teamname_issue))

    if not org_obj.organization:
        raise InvalidTeamException(
            "Specified organization %s was not an organization" % org_obj.username
        )

    team_role = TeamRole.get(TeamRole.name == team_role_name)
    return Team.create(name=name, organization=org_obj, role=team_role, description=description)


def add_user_to_team(user_obj, team):
    try:
        return TeamMember.create(user=user_obj, team=team)
    except Exception:
        raise UserAlreadyInTeam(
            "User %s is already a member of team %s" % (user_obj.username, team.name)
        )


def remove_user_from_team(org_name, team_name, username, removed_by_username):
    Org = User.alias()
    joined = TeamMember.select().join(User).switch(TeamMember).join(Team)
    with_role = joined.join(TeamRole)
    with_org = with_role.switch(Team).join(Org, on=(Org.id == Team.organization))
    found = list(
        with_org.where(User.username == username, Org.username == org_name, Team.name == team_name)
    )

    if not found:
        raise DataModelException("User %s does not belong to team %s" % (username, team_name))

    if username == removed_by_username:
        admin_team_query = __get_user_admin_teams(org_name, username)
        admin_team_names = {team.name for team in admin_team_query}
        if team_name in admin_team_names and len(admin_team_names) <= 1:
            msg = "User cannot remove themselves from their only admin team."
            raise DataModelException(msg)

    user_in_team = found[0]
    user_in_team.delete_instance()


def set_team_org_permission(team, team_role_name, set_by_username):
    if team.role.name == "admin" and team_role_name != "admin":
        # We need to make sure we're not removing the users only admin role
        user_admin_teams = __get_user_admin_teams(team.organization.username, set_by_username)
        admin_team_set = {admin_team.name for admin_team in user_admin_teams}
        if team.name in admin_team_set and len(admin_team_set) <= 1:
            msg = (
                "Cannot remove admin from team '%s' because calling user "
                + "would no longer have admin on org '%s'"
            ) % (team.name, team.organization.username)
            raise DataModelException(msg)

    new_role = TeamRole.get(TeamRole.name == team_role_name)
    team.role = new_role
    team.save()
    return team


def __get_user_admin_teams(org_name, username):
    Org = User.alias()
    user_teams = Team.select().join(TeamMember).join(User)
    with_org = user_teams.switch(Team).join(Org, on=(Org.id == Team.organization))
    with_role = with_org.switch(Team).join(TeamRole)
    admin_teams = with_role.where(
        User.username == username, Org.username == org_name, TeamRole.name == "admin"
    )
    return admin_teams


def remove_team(org_name, team_name, removed_by_username):
    joined = Team.select(Team, TeamRole).join(User).switch(Team).join(TeamRole)

    found = list(
        joined.where(User.organization == True, User.username == org_name, Team.name == team_name)
    )
    if not found:
        raise InvalidTeamException("Team '%s' is not a team in org '%s'" % (team_name, org_name))

    team = found[0]
    if team.role.name == "admin":
        admin_teams = list(__get_user_admin_teams(org_name, removed_by_username))
        if len(admin_teams) <= 1:
            # The team we are trying to remove is the only admin team containing this user.
            msg = "Deleting team '%s' would remove admin ability for user '%s' in organization '%s'"
            raise DataModelException(msg % (team_name, removed_by_username, org_name))

    team.delete_instance(recursive=True, delete_nullable=True)


def add_or_invite_to_team(inviter, team, user_obj=None, email=None, requires_invite=True):
    # If the user is a member of the organization, then we simply add the
    # user directly to the team. Otherwise, an invite is created for the user/email.
    # We return None if the user was directly added and the invite object if the user was invited.
    if user_obj and requires_invite:
        orgname = team.organization.username

        # If the user is part of the organization (or a robot), then no invite is required.
        if user_obj.robot:
            requires_invite = False
            if not user_obj.username.startswith(orgname + "+"):
                raise InvalidTeamMemberException(
                    "Cannot add the specified robot to this team, "
                    + "as it is not a member of the organization"
                )
        else:
            query = (
                TeamMember.select()
                .where(TeamMember.user == user_obj)
                .join(Team)
                .join(User)
                .where(User.username == orgname, User.organization == True)
            )
            requires_invite = not any(query)

    # If we have a valid user and no invite is required, simply add the user to the team.
    if user_obj and not requires_invite:
        add_user_to_team(user_obj, team)
        return None

    email_address = email if not user_obj else None
    return TeamMemberInvite.create(user=user_obj, email=email_address, team=team, inviter=inviter)


def get_matching_user_teams(team_prefix, user_obj, limit=10):
    team_prefix_search = prefix_search(Team.name, team_prefix)
    query = (
        Team.select(Team.id.distinct(), Team)
        .join(User)
        .switch(Team)
        .join(TeamMember)
        .where(TeamMember.user == user_obj, team_prefix_search)
        .limit(limit)
    )

    return query


def get_organization_team(orgname, teamname):
    joined = Team.select().join(User)
    query = joined.where(
        Team.name == teamname, User.organization == True, User.username == orgname
    ).limit(1)
    result = list(query)
    if not result:
        raise InvalidTeamException("Team does not exist: %s/%s", orgname, teamname)

    return result[0]


def get_matching_admined_teams(team_prefix, user_obj, limit=10):
    team_prefix_search = prefix_search(Team.name, team_prefix)
    admined_orgs = (
        _basequery.get_user_organizations(user_obj.username)
        .switch(Team)
        .join(TeamRole)
        .where(TeamRole.name == "admin")
    )

    query = (
        Team.select(Team.id.distinct(), Team)
        .join(User)
        .switch(Team)
        .join(TeamMember)
        .where(team_prefix_search, Team.organization << (admined_orgs))
        .limit(limit)
    )

    return query


def get_matching_teams(team_prefix, organization):
    team_prefix_search = prefix_search(Team.name, team_prefix)
    query = Team.select().where(team_prefix_search, Team.organization == organization)
    return query.limit(10)


def get_teams_within_org(organization, has_external_auth=False):
    """
    Returns a AttrDict of team info (id, name, description), its role under the org, the number of
    repositories on which it has permission, and the number of members.
    """
    query = Team.select().where(Team.organization == organization).join(TeamRole)

    def _team_view(team):
        return {
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "role_name": Team.role.get_name(team.role_id),
            "repo_count": 0,
            "member_count": 0,
            "is_synced": False,
        }

    teams = {team.id: _team_view(team) for team in query}
    if not teams:
        # Just in case. Should ideally never happen.
        return []

    # Add repository permissions count.
    permission_tuples = (
        RepositoryPermission.select(RepositoryPermission.team, fn.Count(RepositoryPermission.id))
        .where(RepositoryPermission.team << list(teams.keys()))
        .group_by(RepositoryPermission.team)
        .tuples()
    )

    for perm_tuple in permission_tuples:
        teams[perm_tuple[0]]["repo_count"] = perm_tuple[1]

    # Add the member count.
    members_tuples = (
        TeamMember.select(TeamMember.team, fn.Count(TeamMember.id))
        .where(TeamMember.team << list(teams.keys()))
        .group_by(TeamMember.team)
        .tuples()
    )

    for member_tuple in members_tuples:
        teams[member_tuple[0]]["member_count"] = member_tuple[1]

    # Add syncing information.
    if has_external_auth:
        sync_query = TeamSync.select(TeamSync.team).where(TeamSync.team << list(teams.keys()))
        for team_sync in sync_query:
            teams[team_sync.team_id]["is_synced"] = True

    return [AttrDict(team_info) for team_info in list(teams.values())]


def get_user_teams_within_org(username, organization):
    joined = Team.select().join(TeamMember).join(User)
    return joined.where(Team.organization == organization, User.username == username)


def list_organization_members_by_teams(organization):
    query = (
        TeamMember.select(Team, User)
        .join(Team)
        .switch(TeamMember)
        .join(User)
        .where(Team.organization == organization)
    )
    return query


def get_organization_team_member_invites(teamid):
    joined = TeamMemberInvite.select().join(Team).join(User)
    query = joined.where(Team.id == teamid)
    return query


def delete_team_email_invite(team, email):
    try:
        found = TeamMemberInvite.get(TeamMemberInvite.email == email, TeamMemberInvite.team == team)
    except TeamMemberInvite.DoesNotExist:
        return False

    found.delete_instance()
    return True


def delete_team_user_invite(team, user_obj):
    try:
        found = TeamMemberInvite.get(
            TeamMemberInvite.user == user_obj, TeamMemberInvite.team == team
        )
    except TeamMemberInvite.DoesNotExist:
        return False

    found.delete_instance()
    return True


def lookup_team_invites_by_email(email):
    return TeamMemberInvite.select().where(TeamMemberInvite.email == email)


def lookup_team_invites(user_obj):
    return TeamMemberInvite.select().where(TeamMemberInvite.user == user_obj)


def lookup_team_invite(code, user_obj=None):
    # Lookup the invite code.
    try:
        found = TeamMemberInvite.get(TeamMemberInvite.invite_token == code)
    except TeamMemberInvite.DoesNotExist:
        raise DataModelException("Invalid confirmation code.")

    if user_obj and found.user != user_obj:
        raise DataModelException("Invalid confirmation code.")

    return found


def delete_team_invite(code, user_obj=None):
    found = lookup_team_invite(code, user_obj)

    team = found.team
    inviter = found.inviter

    found.delete_instance()

    return (team, inviter)


def find_matching_team_invite(code, user_obj):
    """
    Finds a team invite with the given code that applies to the given user and returns it or raises
    a DataModelException if not found.
    """
    found = lookup_team_invite(code)

    # If the invite is for a specific user, we have to confirm that here.
    if found.user is not None and found.user != user_obj:
        message = (
            """This invite is intended for user "%s".
                 Please login to that account and try again."""
            % found.user.username
        )
        raise DataModelException(message)

    return found


def find_organization_invites(organization, user_obj):
    """
    Finds all organization team invites for the given user under the given organization.
    """
    invite_check = TeamMemberInvite.user == user_obj
    if user_obj.verified:
        invite_check = invite_check | (TeamMemberInvite.email == user_obj.email)

    query = (
        TeamMemberInvite.select().join(Team).where(invite_check, Team.organization == organization)
    )
    return query


def confirm_team_invite(code, user_obj):
    """
    Confirms the given team invite code for the given user by adding the user to the team and
    deleting the code.

    Raises a DataModelException if the code was not found or does not apply to the given user. If
    the user is invited to two or more teams under the same organization, they are automatically
    confirmed for all of them.
    """
    found = find_matching_team_invite(code, user_obj)

    # Find all matching invitations for the user under the organization.
    code_found = False
    for invite in find_organization_invites(found.team.organization, user_obj):
        # Add the user to the team.
        try:
            code_found = True
            add_user_to_team(user_obj, invite.team)
        except UserAlreadyInTeam:
            # Ignore.
            pass

        # Delete the invite and return the team.
        invite.delete_instance()

    if not code_found:
        if found.user:
            message = (
                """This invite is intended for user "%s".
                   Please login to that account and try again."""
                % found.user.username
            )
            raise DataModelException(message)
        else:
            message = (
                """This invite is intended for email "%s".
                   Please login to that account and try again."""
                % found.email
            )
            raise DataModelException(message)

    team = found.team
    inviter = found.inviter
    return (team, inviter)


def get_federated_team_member_mapping(team, login_service_name):
    """
    Returns a dict of all federated IDs for all team members in the team whose users are bound to
    the login service within the given name.

    The dictionary is from federated service identifier (username) to their Quay User table ID.
    """
    login_service = LoginService.get(name=login_service_name)

    query = (
        FederatedLogin.select(FederatedLogin.service_ident, User.id)
        .join(User)
        .join(TeamMember)
        .join(Team)
        .where(Team.id == team, User.robot == False, FederatedLogin.service == login_service)
    )
    return dict(query.tuples())


def list_team_users(team):
    """
    Returns an iterator of all the *users* found in a team.

    Does not include robots.
    """
    return User.select().join(TeamMember).join(Team).where(Team.id == team, User.robot == False)


def list_team_robots(team):
    """
    Returns an iterator of all the *robots* found in a team.

    Does not include users.
    """
    return User.select().join(TeamMember).join(Team).where(Team.id == team, User.robot == True)


def set_team_syncing(team, login_service_name, config):
    """
    Sets the given team to sync to the given service using the given config.
    """
    login_service = LoginService.get(name=login_service_name)
    return TeamSync.create(
        team=team, transaction_id="", service=login_service, config=json.dumps(config)
    )


def remove_team_syncing(orgname, teamname):
    """
    Removes syncing on the team matching the given organization name and team name.
    """
    existing = get_team_sync_information(orgname, teamname)
    if existing:
        existing.delete_instance()


def get_stale_team(stale_timespan):
    """
    Returns a team that is setup to sync to an external group, and who has not been synced in.

    now - stale_timespan. Returns None if none found.
    """
    stale_at = datetime.now() - stale_timespan

    try:
        candidates = (
            TeamSync.select(TeamSync.id)
            .where((TeamSync.last_updated <= stale_at) | (TeamSync.last_updated >> None))
            .limit(500)
            .alias("candidates")
        )

        found = TeamSync.select(candidates.c.id).from_(candidates).order_by(db_random_func()).get()

        if found is None:
            return

        return TeamSync.select(TeamSync, Team).join(Team).where(TeamSync.id == found.id).get()
    except TeamSync.DoesNotExist:
        return None


def get_team_sync_information(orgname, teamname):
    """
    Returns the team syncing information for the team with the given name under the organization
    with the given name or None if none.
    """
    query = (
        TeamSync.select(TeamSync, LoginService)
        .join(Team)
        .join(User)
        .switch(TeamSync)
        .join(LoginService)
        .where(Team.name == teamname, User.organization == True, User.username == orgname)
    )

    try:
        return query.get()
    except TeamSync.DoesNotExist:
        return None


def update_sync_status(team_sync_info):
    """
    Attempts to update the transaction ID and last updated time on a TeamSync object.

    If the transaction ID on the entry in the DB does not match that found on the object, this
    method returns False, which indicates another caller updated it first.
    """
    new_transaction_id = str(uuid.uuid4())
    query = TeamSync.update(transaction_id=new_transaction_id, last_updated=datetime.now()).where(
        TeamSync.id == team_sync_info.id, TeamSync.transaction_id == team_sync_info.transaction_id
    )
    return query.execute() == 1


def delete_members_not_present(team, member_id_set):
    """
    Deletes all members of the given team that are not found in the member ID set.
    """
    with db_transaction():
        user_ids = set([u.id for u in list_team_users(team)])
        to_delete = list(user_ids - member_id_set)
        if to_delete:
            query = TeamMember.delete().where(TeamMember.team == team, TeamMember.user << to_delete)
            return query.execute()

    return 0
