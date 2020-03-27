"""
Manage organizations, members and OAuth applications.
"""

import logging
import recaptcha2

from flask import request

import features

from app import (
    billing as stripe,
    avatar,
    all_queues,
    authentication,
    namespace_gc_queue,
    ip_resolver,
    app,
)
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    request_error,
    related_user_resource,
    internal_only,
    require_user_admin,
    log_action,
    show_if,
    path_param,
    require_scope,
    require_fresh_login,
)
from endpoints.exception import Unauthorized, NotFound
from endpoints.api.user import User, PrivateRepositories
from auth.permissions import (
    AdministerOrganizationPermission,
    OrganizationMemberPermission,
    CreateRepositoryPermission,
    ViewTeamPermission,
)
from auth.auth_context import get_authenticated_user
from auth import scopes
from data import model
from data.billing import get_plan
from util.names import parse_robot_username
from util.request import get_request_ip


logger = logging.getLogger(__name__)


def team_view(orgname, team):
    return {
        "name": team.name,
        "description": team.description,
        "role": team.role_name,
        "avatar": avatar.get_data_for_team(team),
        "can_view": ViewTeamPermission(orgname, team.name).can(),
        "repo_count": team.repo_count,
        "member_count": team.member_count,
        "is_synced": team.is_synced,
    }


def org_view(o, teams):
    is_admin = AdministerOrganizationPermission(o.username).can()
    is_member = OrganizationMemberPermission(o.username).can()

    view = {
        "name": o.username,
        "email": o.email if is_admin else "",
        "avatar": avatar.get_data_for_user(o),
        "is_admin": is_admin,
        "is_member": is_member,
    }

    if teams is not None:
        teams = sorted(teams, key=lambda team: team.id)
        view["teams"] = {t.name: team_view(o.username, t) for t in teams}
        view["ordered_teams"] = [team.name for team in teams]

    if is_admin:
        view["invoice_email"] = o.invoice_email
        view["invoice_email_address"] = o.invoice_email_address
        view["tag_expiration_s"] = o.removed_tag_expiration_s
        view["is_free_account"] = o.stripe_id is None

    return view


@resource("/v1/organization/")
class OrganizationList(ApiResource):
    """
    Resource for creating organizations.
    """

    schemas = {
        "NewOrg": {
            "type": "object",
            "description": "Description of a new organization.",
            "required": ["name",],
            "properties": {
                "name": {"type": "string", "description": "Organization username",},
                "email": {"type": "string", "description": "Organization contact email",},
                "recaptcha_response": {
                    "type": "string",
                    "description": "The (may be disabled) recaptcha response code for verification",
                },
            },
        },
    }

    @require_user_admin
    @nickname("createOrganization")
    @validate_json_request("NewOrg")
    def post(self):
        """
        Create a new organization.
        """
        user = get_authenticated_user()
        org_data = request.get_json()
        existing = None

        try:
            existing = model.organization.get_organization(org_data["name"])
        except model.InvalidOrganizationException:
            pass

        if not existing:
            existing = model.user.get_user(org_data["name"])

        if existing:
            msg = "A user or organization with this name already exists"
            raise request_error(message=msg)

        if features.MAILING and not org_data.get("email"):
            raise request_error(message="Email address is required")

        # If recaptcha is enabled, then verify the user is a human.
        if features.RECAPTCHA:
            recaptcha_response = org_data.get("recaptcha_response", "")
            result = recaptcha2.verify(
                app.config["RECAPTCHA_SECRET_KEY"], recaptcha_response, get_request_ip()
            )

            if not result["success"]:
                return {"message": "Are you a bot? If not, please revalidate the captcha."}, 400

        is_possible_abuser = ip_resolver.is_ip_possible_threat(get_request_ip())
        try:
            model.organization.create_organization(
                org_data["name"],
                org_data.get("email"),
                user,
                email_required=features.MAILING,
                is_possible_abuser=is_possible_abuser,
            )
            return "Created", 201
        except model.DataModelException as ex:
            raise request_error(exception=ex)


@resource("/v1/organization/<orgname>")
@path_param("orgname", "The name of the organization")
@related_user_resource(User)
class Organization(ApiResource):
    """
    Resource for managing organizations.
    """

    schemas = {
        "UpdateOrg": {
            "type": "object",
            "description": "Description of updates for an existing organization",
            "properties": {
                "email": {"type": "string", "description": "Organization contact email",},
                "invoice_email": {
                    "type": "boolean",
                    "description": "Whether the organization desires to receive emails for invoices",
                },
                "invoice_email_address": {
                    "type": ["string", "null"],
                    "description": "The email address at which to receive invoices",
                },
                "tag_expiration_s": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "The number of seconds for tag expiration",
                },
            },
        },
    }

    @nickname("getOrganization")
    def get(self, orgname):
        """
        Get the details for the specified organization.
        """
        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        teams = None
        if OrganizationMemberPermission(orgname).can():
            has_syncing = features.TEAM_SYNCING and bool(authentication.federated_service)
            teams = model.team.get_teams_within_org(org, has_syncing)

        return org_view(org, teams)

    @require_scope(scopes.ORG_ADMIN)
    @nickname("changeOrganizationDetails")
    @validate_json_request("UpdateOrg")
    def put(self, orgname):
        """
        Change the details for the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            org_data = request.get_json()
            if "invoice_email" in org_data:
                logger.debug("Changing invoice_email for organization: %s", org.username)
                model.user.change_send_invoice_email(org, org_data["invoice_email"])

            if (
                "invoice_email_address" in org_data
                and org_data["invoice_email_address"] != org.invoice_email_address
            ):
                new_email = org_data["invoice_email_address"]
                logger.debug("Changing invoice email address for organization: %s", org.username)
                model.user.change_invoice_email_address(org, new_email)

            if "email" in org_data and org_data["email"] != org.email:
                new_email = org_data["email"]
                if model.user.find_user_by_email(new_email):
                    raise request_error(message="E-mail address already used")

                logger.debug("Changing email address for organization: %s", org.username)
                model.user.update_email(org, new_email)

            if features.CHANGE_TAG_EXPIRATION and "tag_expiration_s" in org_data:
                logger.debug(
                    "Changing organization tag expiration to: %ss", org_data["tag_expiration_s"]
                )
                model.user.change_user_tag_expiration(org, org_data["tag_expiration_s"])

            teams = model.team.get_teams_within_org(org)
            return org_view(org, teams)
        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @require_fresh_login
    @nickname("deleteAdminedOrganization")
    def delete(self, orgname):
        """
        Deletes the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            model.user.mark_namespace_for_deletion(org, all_queues, namespace_gc_queue)
            return "", 204

        raise Unauthorized()


@resource("/v1/organization/<orgname>/private")
@path_param("orgname", "The name of the organization")
@internal_only
@related_user_resource(PrivateRepositories)
@show_if(features.BILLING)
class OrgPrivateRepositories(ApiResource):
    """
    Custom verb to compute whether additional private repositories are available.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationPrivateAllowed")
    def get(self, orgname):
        """
        Return whether or not this org is allowed to create new private repositories.
        """
        permission = CreateRepositoryPermission(orgname)
        if permission.can():
            organization = model.organization.get_organization(orgname)
            private_repos = model.user.get_private_repo_count(organization.username)
            data = {"privateAllowed": False}

            if organization.stripe_id:
                cus = stripe.Customer.retrieve(organization.stripe_id)
                if cus.subscription:
                    repos_allowed = 0
                    plan = get_plan(cus.subscription.plan.id)
                    if plan:
                        repos_allowed = plan["privateRepos"]

                    data["privateAllowed"] = private_repos < repos_allowed

            if AdministerOrganizationPermission(orgname).can():
                data["privateCount"] = private_repos

            return data

        raise Unauthorized()


@resource("/v1/organization/<orgname>/collaborators")
@path_param("orgname", "The name of the organization")
class OrganizationCollaboratorList(ApiResource):
    """
    Resource for listing outside collaborators of an organization.

    Collaborators are users that do not belong to any team in the organiztion, but who have direct
    permissions on one or more repositories belonging to the organization.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationCollaborators")
    def get(self, orgname):
        """
        List outside collaborators of the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if not permission.can():
            raise Unauthorized()

        try:
            org = model.organization.get_organization(orgname)
        except model.InvalidOrganizationException:
            raise NotFound()

        all_perms = model.permission.list_organization_member_permissions(org)
        membership = model.team.list_organization_members_by_teams(org)

        org_members = set(m.user.username for m in membership)

        collaborators = {}
        for perm in all_perms:
            username = perm.user.username

            # Only interested in non-member permissions.
            if username in org_members:
                continue

            if username not in collaborators:
                collaborators[username] = {
                    "kind": "user",
                    "name": username,
                    "avatar": avatar.get_data_for_user(perm.user),
                    "repositories": [],
                }

            collaborators[username]["repositories"].append(perm.repository.name)

        return {"collaborators": list(collaborators.values())}


@resource("/v1/organization/<orgname>/members")
@path_param("orgname", "The name of the organization")
class OrganizationMemberList(ApiResource):
    """
    Resource for listing the members of an organization.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationMembers")
    def get(self, orgname):
        """
        List the human members of the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            # Loop to create the members dictionary. Note that the members collection
            # will return an entry for *every team* a member is on, so we will have
            # duplicate keys (which is why we pre-build the dictionary).
            members_dict = {}
            members = model.team.list_organization_members_by_teams(org)
            for member in members:
                if member.user.robot:
                    continue

                if not member.user.username in members_dict:
                    member_data = {
                        "name": member.user.username,
                        "kind": "user",
                        "avatar": avatar.get_data_for_user(member.user),
                        "teams": [],
                        "repositories": [],
                    }

                    members_dict[member.user.username] = member_data

                members_dict[member.user.username]["teams"].append(
                    {"name": member.team.name, "avatar": avatar.get_data_for_team(member.team),}
                )

            # Loop to add direct repository permissions.
            for permission in model.permission.list_organization_member_permissions(org):
                username = permission.user.username
                if not username in members_dict:
                    continue

                members_dict[username]["repositories"].append(permission.repository.name)

            return {"members": list(members_dict.values())}

        raise Unauthorized()


@resource("/v1/organization/<orgname>/members/<membername>")
@path_param("orgname", "The name of the organization")
@path_param("membername", "The username of the organization member")
class OrganizationMember(ApiResource):
    """
    Resource for managing individual organization members.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationMember")
    def get(self, orgname, membername):
        """
        Retrieves the details of a member of the organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            # Lookup the user.
            member = model.user.get_user(membername)
            if not member:
                raise NotFound()

            organization = model.user.get_user_or_org(orgname)
            if not organization:
                raise NotFound()

            # Lookup the user's information in the organization.
            teams = list(model.team.get_user_teams_within_org(membername, organization))
            if not teams:
                # 404 if the user is not a robot under the organization, as that means the referenced
                # user or robot is not a member of this organization.
                if not member.robot:
                    raise NotFound()

                namespace, _ = parse_robot_username(member.username)
                if namespace != orgname:
                    raise NotFound()

            repo_permissions = model.permission.list_organization_member_permissions(
                organization, member
            )

            def local_team_view(team):
                return {
                    "name": team.name,
                    "avatar": avatar.get_data_for_team(team),
                }

            return {
                "name": member.username,
                "kind": "robot" if member.robot else "user",
                "avatar": avatar.get_data_for_user(member),
                "teams": [local_team_view(team) for team in teams],
                "repositories": [permission.repository.name for permission in repo_permissions],
            }

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("removeOrganizationMember")
    def delete(self, orgname, membername):
        """
        Removes a member from an organization, revoking all its repository priviledges and removing
        it from all teams in the organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            # Lookup the user.
            user = model.user.get_nonrobot_user(membername)
            if not user:
                raise NotFound()

            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            # Remove the user from the organization.
            model.organization.remove_organization_member(org, user)
            return "", 204

        raise Unauthorized()


@resource("/v1/app/<client_id>")
@path_param("client_id", "The OAuth client ID")
class ApplicationInformation(ApiResource):
    """
    Resource that returns public information about a registered application.
    """

    @nickname("getApplicationInformation")
    def get(self, client_id):
        """
        Get information on the specified application.
        """
        application = model.oauth.get_application_for_client_id(client_id)
        if not application:
            raise NotFound()

        app_email = application.avatar_email or application.organization.email
        app_data = avatar.get_data(application.name, app_email, "app")

        return {
            "name": application.name,
            "description": application.description,
            "uri": application.application_uri,
            "avatar": app_data,
            "organization": org_view(application.organization, []),
        }


def app_view(application):
    is_admin = AdministerOrganizationPermission(application.organization.username).can()
    client_secret = None
    if is_admin:
        if application.secure_client_secret is not None:
            client_secret = application.secure_client_secret.decrypt()

    assert (client_secret is not None) == is_admin
    return {
        "name": application.name,
        "description": application.description,
        "application_uri": application.application_uri,
        "client_id": application.client_id,
        "client_secret": client_secret,
        "redirect_uri": application.redirect_uri if is_admin else None,
        "avatar_email": application.avatar_email if is_admin else None,
    }


@resource("/v1/organization/<orgname>/applications")
@path_param("orgname", "The name of the organization")
class OrganizationApplications(ApiResource):
    """
    Resource for managing applications defined by an organization.
    """

    schemas = {
        "NewApp": {
            "type": "object",
            "description": "Description of a new organization application.",
            "required": ["name",],
            "properties": {
                "name": {"type": "string", "description": "The name of the application",},
                "redirect_uri": {
                    "type": "string",
                    "description": "The URI for the application's OAuth redirect",
                },
                "application_uri": {
                    "type": "string",
                    "description": "The URI for the application's homepage",
                },
                "description": {
                    "type": "string",
                    "description": "The human-readable description for the application",
                },
                "avatar_email": {
                    "type": "string",
                    "description": "The e-mail address of the avatar to use for the application",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationApplications")
    def get(self, orgname):
        """
        List the applications for the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            applications = model.oauth.list_applications_for_org(org)
            return {"applications": [app_view(application) for application in applications]}

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrganizationApplication")
    @validate_json_request("NewApp")
    def post(self, orgname):
        """
        Creates a new application under this organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            app_data = request.get_json()
            application = model.oauth.create_application(
                org,
                app_data["name"],
                app_data.get("application_uri", ""),
                app_data.get("redirect_uri", ""),
                description=app_data.get("description", ""),
                avatar_email=app_data.get("avatar_email", None),
            )

            app_data.update(
                {"application_name": application.name, "client_id": application.client_id}
            )

            log_action("create_application", orgname, app_data)

            return app_view(application)
        raise Unauthorized()


@resource("/v1/organization/<orgname>/applications/<client_id>")
@path_param("orgname", "The name of the organization")
@path_param("client_id", "The OAuth client ID")
class OrganizationApplicationResource(ApiResource):
    """
    Resource for managing an application defined by an organizations.
    """

    schemas = {
        "UpdateApp": {
            "type": "object",
            "description": "Description of an updated application.",
            "required": ["name", "redirect_uri", "application_uri"],
            "properties": {
                "name": {"type": "string", "description": "The name of the application",},
                "redirect_uri": {
                    "type": "string",
                    "description": "The URI for the application's OAuth redirect",
                },
                "application_uri": {
                    "type": "string",
                    "description": "The URI for the application's homepage",
                },
                "description": {
                    "type": "string",
                    "description": "The human-readable description for the application",
                },
                "avatar_email": {
                    "type": "string",
                    "description": "The e-mail address of the avatar to use for the application",
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationApplication")
    def get(self, orgname, client_id):
        """
        Retrieves the application with the specified client_id under the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            application = model.oauth.lookup_application(org, client_id)
            if not application:
                raise NotFound()

            return app_view(application)

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrganizationApplication")
    @validate_json_request("UpdateApp")
    def put(self, orgname, client_id):
        """
        Updates an application under this organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            application = model.oauth.lookup_application(org, client_id)
            if not application:
                raise NotFound()

            app_data = request.get_json()
            application.name = app_data["name"]
            application.application_uri = app_data["application_uri"]
            application.redirect_uri = app_data["redirect_uri"]
            application.description = app_data.get("description", "")
            application.avatar_email = app_data.get("avatar_email", None)
            application.save()

            app_data.update(
                {"application_name": application.name, "client_id": application.client_id}
            )

            log_action("update_application", orgname, app_data)

            return app_view(application)
        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrganizationApplication")
    def delete(self, orgname, client_id):
        """
        Deletes the application under this organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            application = model.oauth.delete_application(org, client_id)
            if not application:
                raise NotFound()

            log_action(
                "delete_application",
                orgname,
                {"application_name": application.name, "client_id": client_id},
            )

            return "", 204
        raise Unauthorized()


@resource("/v1/organization/<orgname>/applications/<client_id>/resetclientsecret")
@path_param("orgname", "The name of the organization")
@path_param("client_id", "The OAuth client ID")
@internal_only
class OrganizationApplicationResetClientSecret(ApiResource):
    """
    Custom verb for resetting the client secret of an application.
    """

    @nickname("resetOrganizationApplicationClientSecret")
    def post(self, orgname, client_id):
        """
        Resets the client secret of the application.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            application = model.oauth.lookup_application(org, client_id)
            if not application:
                raise NotFound()

            application = model.oauth.reset_client_secret(application)
            log_action(
                "reset_application_client_secret",
                orgname,
                {"application_name": application.name, "client_id": client_id},
            )

            return app_view(application)
        raise Unauthorized()
