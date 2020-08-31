"""
Create, list and manage an organization's teams.
"""

import json

from functools import wraps

from flask import request

import features

from app import avatar, authentication
from auth.permissions import (
    AdministerOrganizationPermission,
    ViewTeamPermission,
    SuperUserPermission,
)

from auth.auth_context import get_authenticated_user
from auth import scopes
from data import model
from data.database import Team
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    request_error,
    log_action,
    internal_only,
    require_scope,
    path_param,
    query_param,
    parse_args,
    require_user_admin,
    show_if,
    format_date,
    verify_not_prod,
    require_fresh_login,
)
from endpoints.exception import Unauthorized, NotFound, InvalidRequest
from util.useremails import send_org_invite_email
from util.names import parse_robot_username
from util.parsing import truthy_bool


def permission_view(permission):
    return {
        "repository": {
            "name": permission.repository.name,
            "is_public": model.repository.is_repository_public(permission.repository),
        },
        "role": permission.role.name,
    }


def try_accept_invite(code, user):
    (team, inviter) = model.team.confirm_team_invite(code, user)

    model.notification.delete_matching_notifications(
        user, "org_team_invite", org=team.organization.username
    )

    orgname = team.organization.username
    log_action(
        "org_team_member_invite_accepted",
        orgname,
        {"member": user.username, "team": team.name, "inviter": inviter.username},
    )

    return team


def handle_addinvite_team(inviter, team, user=None, email=None):
    requires_invite = features.MAILING and features.REQUIRE_TEAM_INVITE
    invite = model.team.add_or_invite_to_team(
        inviter, team, user, email, requires_invite=requires_invite
    )
    if not invite:
        # User was added to the team directly.
        return

    orgname = team.organization.username
    if user:
        model.notification.create_notification(
            "org_team_invite",
            user,
            metadata={
                "code": invite.invite_token,
                "inviter": inviter.username,
                "org": orgname,
                "team": team.name,
            },
        )

    send_org_invite_email(
        user.username if user else email,
        user.email if user else email,
        orgname,
        team.name,
        inviter.username,
        invite.invite_token,
    )
    return invite


def team_view(orgname, team, is_new_team=False):
    view_permission = ViewTeamPermission(orgname, team.name)
    return {
        "name": team.name,
        "description": team.description,
        "can_view": view_permission.can(),
        "role": Team.role.get_name(team.role_id),
        "avatar": avatar.get_data_for_team(team),
        "new_team": is_new_team,
    }


def member_view(member, invited=False):
    return {
        "name": member.username,
        "kind": "user",
        "is_robot": member.robot,
        "avatar": avatar.get_data_for_user(member),
        "invited": invited,
    }


def invite_view(invite):
    if invite.user:
        return member_view(invite.user, invited=True)
    else:
        return {
            "email": invite.email,
            "kind": "invite",
            "avatar": avatar.get_data(invite.email, invite.email, "user"),
            "invited": True,
        }


def disallow_for_synced_team(except_robots=False):
    """
    Disallows the decorated operation for a team that is marked as being synced from an internal
    auth provider such as LDAP.

    If except_robots is True, then the operation is allowed if the member specified on the operation
    is a robot account.
    """

    def inner(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Team syncing can only be enabled if we have a federated service.
            if features.TEAM_SYNCING and authentication.federated_service:
                orgname = kwargs["orgname"]
                teamname = kwargs["teamname"]
                if model.team.get_team_sync_information(orgname, teamname):
                    if not except_robots or not parse_robot_username(kwargs.get("membername", "")):
                        raise InvalidRequest("Cannot call this method on an auth-synced team")

            return func(self, *args, **kwargs)

        return wrapper

    return inner


disallow_nonrobots_for_synced_team = disallow_for_synced_team(except_robots=True)
disallow_all_for_synced_team = disallow_for_synced_team(except_robots=False)


@resource("/v1/organization/<orgname>/team/<teamname>")
@path_param("orgname", "The name of the organization")
@path_param("teamname", "The name of the team")
class OrganizationTeam(ApiResource):
    """
    Resource for manging an organization's teams.
    """

    schemas = {
        "TeamDescription": {
            "type": "object",
            "description": "Description of a team",
            "required": [
                "role",
            ],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Org wide permissions that should apply to the team",
                    "enum": [
                        "member",
                        "creator",
                        "admin",
                    ],
                },
                "description": {
                    "type": "string",
                    "description": "Markdown description for the team",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrganizationTeam")
    @validate_json_request("TeamDescription")
    def put(self, orgname, teamname):
        """
        Update the org-wide permission for the specified team.
        """
        edit_permission = AdministerOrganizationPermission(orgname)
        if edit_permission.can():
            team = None

            details = request.get_json()
            is_existing = False
            try:
                team = model.team.get_organization_team(orgname, teamname)
                is_existing = True
            except model.InvalidTeamException:
                # Create the new team.
                description = details["description"] if "description" in details else ""
                role = details["role"] if "role" in details else "member"

                org = model.organization.get_organization(orgname)
                team = model.team.create_team(teamname, org, role, description)
                log_action("org_create_team", orgname, {"team": teamname})

            if is_existing:
                if "description" in details and team.description != details["description"]:
                    team.description = details["description"]
                    team.save()
                    log_action(
                        "org_set_team_description",
                        orgname,
                        {"team": teamname, "description": team.description},
                    )

                if "role" in details:
                    role = Team.role.get_name(team.role_id)
                    if role != details["role"]:
                        team = model.team.set_team_org_permission(
                            team, details["role"], get_authenticated_user().username
                        )
                        log_action(
                            "org_set_team_role",
                            orgname,
                            {"team": teamname, "role": details["role"]},
                        )

            return team_view(orgname, team, is_new_team=not is_existing), 200

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrganizationTeam")
    def delete(self, orgname, teamname):
        """
        Delete the specified team.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            model.team.remove_team(orgname, teamname, get_authenticated_user().username)
            log_action("org_delete_team", orgname, {"team": teamname})
            return "", 204

        raise Unauthorized()


def _syncing_setup_allowed(orgname):
    """
    Returns whether syncing setup is allowed for the current user over the matching org.
    """
    if not features.NONSUPERUSER_TEAM_SYNCING_SETUP and not SuperUserPermission().can():
        return False

    return AdministerOrganizationPermission(orgname).can()


@resource("/v1/organization/<orgname>/team/<teamname>/syncing")
@path_param("orgname", "The name of the organization")
@path_param("teamname", "The name of the team")
@show_if(features.TEAM_SYNCING)
class OrganizationTeamSyncing(ApiResource):
    """
    Resource for managing syncing of a team by a backing group.
    """

    @require_scope(scopes.ORG_ADMIN)
    @require_scope(scopes.SUPERUSER)
    @nickname("enableOrganizationTeamSync")
    @verify_not_prod
    @require_fresh_login
    def post(self, orgname, teamname):
        if _syncing_setup_allowed(orgname):
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            config = request.get_json()

            # Ensure that the specified config points to a valid group.
            status, err = authentication.check_group_lookup_args(config)
            if not status:
                raise InvalidRequest("Could not sync to group: %s" % err)

            # Set the team's syncing config.
            model.team.set_team_syncing(team, authentication.federated_service, config)

            return team_view(orgname, team)

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @require_scope(scopes.SUPERUSER)
    @nickname("disableOrganizationTeamSync")
    @verify_not_prod
    @require_fresh_login
    def delete(self, orgname, teamname):
        if _syncing_setup_allowed(orgname):
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            model.team.remove_team_syncing(orgname, teamname)
            return team_view(orgname, team)

        raise Unauthorized()


@resource("/v1/organization/<orgname>/team/<teamname>/members")
@path_param("orgname", "The name of the organization")
@path_param("teamname", "The name of the team")
class TeamMemberList(ApiResource):
    """
    Resource for managing the list of members for a team.
    """

    @require_scope(scopes.ORG_ADMIN)
    @parse_args()
    @query_param(
        "includePending", "Whether to include pending members", type=truthy_bool, default=False
    )
    @nickname("getOrganizationTeamMembers")
    def get(self, orgname, teamname, parsed_args):
        """
        Retrieve the list of members for the specified team.
        """
        view_permission = ViewTeamPermission(orgname, teamname)
        edit_permission = AdministerOrganizationPermission(orgname)

        if view_permission.can():
            team = None
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            members = model.organization.get_organization_team_members(team.id)
            invites = []

            if parsed_args["includePending"] and edit_permission.can():
                invites = model.team.get_organization_team_member_invites(team.id)

            data = {
                "name": teamname,
                "members": [member_view(m) for m in members] + [invite_view(i) for i in invites],
                "can_edit": edit_permission.can(),
            }

            if features.TEAM_SYNCING and authentication.federated_service:
                if _syncing_setup_allowed(orgname):
                    data["can_sync"] = {
                        "service": authentication.federated_service,
                    }

                    data["can_sync"].update(authentication.service_metadata())

                sync_info = model.team.get_team_sync_information(orgname, teamname)
                if sync_info is not None:
                    data["synced"] = {
                        "service": sync_info.service.name,
                    }

                    if SuperUserPermission().can():
                        data["synced"].update(
                            {
                                "last_updated": format_date(sync_info.last_updated),
                                "config": json.loads(sync_info.config),
                            }
                        )

            return data

        raise Unauthorized()


@resource("/v1/organization/<orgname>/team/<teamname>/members/<membername>")
@path_param("orgname", "The name of the organization")
@path_param("teamname", "The name of the team")
@path_param("membername", "The username of the team member")
class TeamMember(ApiResource):
    """
    Resource for managing individual members of a team.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrganizationTeamMember")
    @disallow_nonrobots_for_synced_team
    def put(self, orgname, teamname, membername):
        """
        Adds or invites a member to an existing team.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            team = None
            user = None

            # Find the team.
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            # Find the user.
            user = model.user.get_user(membername)
            if not user:
                raise request_error(message="Unknown user")

            # Add or invite the user to the team.
            inviter = get_authenticated_user()
            invite = handle_addinvite_team(inviter, team, user=user)
            if not invite:
                log_action("org_add_team_member", orgname, {"member": membername, "team": teamname})
                return member_view(user, invited=False)

            # User was invited.
            log_action(
                "org_invite_team_member",
                orgname,
                {"user": membername, "member": membername, "team": teamname},
            )
            return member_view(user, invited=True)

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrganizationTeamMember")
    @disallow_nonrobots_for_synced_team
    def delete(self, orgname, teamname, membername):
        """
        Delete a member of a team.

        If the user is merely invited to join the team, then the invite is removed instead.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            # Remote the user from the team.
            invoking_user = get_authenticated_user().username

            # Find the team.
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            # Find the member.
            member = model.user.get_user(membername)
            if not member:
                raise NotFound()

            # First attempt to delete an invite for the user to this team. If none found,
            # then we try to remove the user directly.
            if model.team.delete_team_user_invite(team, member):
                log_action(
                    "org_delete_team_member_invite",
                    orgname,
                    {"user": membername, "team": teamname, "member": membername},
                )
                return "", 204

            model.team.remove_user_from_team(orgname, teamname, membername, invoking_user)
            log_action("org_remove_team_member", orgname, {"member": membername, "team": teamname})
            return "", 204

        raise Unauthorized()


@resource("/v1/organization/<orgname>/team/<teamname>/invite/<email>")
@show_if(features.MAILING)
class InviteTeamMember(ApiResource):
    """
    Resource for inviting a team member via email address.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("inviteTeamMemberEmail")
    @disallow_all_for_synced_team
    def put(self, orgname, teamname, email):
        """
        Invites an email address to an existing team.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            team = None

            # Find the team.
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            # Invite the email to the team.
            inviter = get_authenticated_user()
            invite = handle_addinvite_team(inviter, team, email=email)
            log_action(
                "org_invite_team_member",
                orgname,
                {"email": email, "team": teamname, "member": email},
            )
            return invite_view(invite)

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteTeamMemberEmailInvite")
    def delete(self, orgname, teamname, email):
        """
        Delete an invite of an email address to join a team.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            team = None

            # Find the team.
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            # Delete the invite.
            if not model.team.delete_team_email_invite(team, email):
                raise NotFound()

            log_action(
                "org_delete_team_member_invite",
                orgname,
                {"email": email, "team": teamname, "member": email},
            )
            return "", 204

        raise Unauthorized()


@resource("/v1/organization/<orgname>/team/<teamname>/permissions")
@path_param("orgname", "The name of the organization")
@path_param("teamname", "The name of the team")
class TeamPermissions(ApiResource):
    """
    Resource for listing the permissions an org's team has in the system.
    """

    @nickname("getOrganizationTeamPermissions")
    def get(self, orgname, teamname):
        """
        Returns the list of repository permissions for the org's team.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                team = model.team.get_organization_team(orgname, teamname)
            except model.InvalidTeamException:
                raise NotFound()

            permissions = model.permission.list_team_permissions(team)

            return {"permissions": [permission_view(permission) for permission in permissions]}

        raise Unauthorized()


@resource("/v1/teaminvite/<code>")
@internal_only
@show_if(features.MAILING)
class TeamMemberInvite(ApiResource):
    """
    Resource for managing invites to join a team.
    """

    @require_user_admin
    @nickname("acceptOrganizationTeamInvite")
    def put(self, code):
        """
        Accepts an invite to join a team in an organization.
        """
        # Accept the invite for the current user.
        team = try_accept_invite(code, get_authenticated_user())
        if not team:
            raise NotFound()

        orgname = team.organization.username
        return {"org": orgname, "team": team.name}

    @nickname("declineOrganizationTeamInvite")
    @require_user_admin
    def delete(self, code):
        """
        Delete an existing invitation to join a team.
        """
        (team, inviter) = model.team.delete_team_invite(code, user_obj=get_authenticated_user())

        model.notification.delete_matching_notifications(
            get_authenticated_user(), "org_team_invite", code=code
        )

        orgname = team.organization.username
        log_action(
            "org_team_member_invite_declined",
            orgname,
            {
                "member": get_authenticated_user().username,
                "team": team.name,
                "inviter": inviter.username,
            },
        )

        return "", 204
