"""
Manage default permissions added to repositories.
"""

from flask import request

from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    validate_json_request,
    request_error,
    log_action,
    path_param,
    require_scope,
)
from endpoints.exception import Unauthorized, NotFound
from auth.permissions import AdministerOrganizationPermission
from auth.auth_context import get_authenticated_user
from auth import scopes
from data import model
from app import avatar


def prototype_view(proto, org_members):
    def prototype_user_view(user):
        return {
            "name": user.username,
            "is_robot": user.robot,
            "kind": "user",
            "is_org_member": user.robot or user.username in org_members,
            "avatar": avatar.get_data_for_user(user),
        }

    if proto.delegate_user:
        delegate_view = prototype_user_view(proto.delegate_user)
    else:
        delegate_view = {
            "name": proto.delegate_team.name,
            "kind": "team",
            "avatar": avatar.get_data_for_team(proto.delegate_team),
        }

    return {
        "activating_user": (
            prototype_user_view(proto.activating_user) if proto.activating_user else None
        ),
        "delegate": delegate_view,
        "role": proto.role.name,
        "id": proto.uuid,
    }


def log_prototype_action(action_kind, orgname, prototype, **kwargs):
    username = get_authenticated_user().username
    log_params = {
        "prototypeid": prototype.uuid,
        "username": username,
        "activating_username": (
            prototype.activating_user.username if prototype.activating_user else None
        ),
        "role": prototype.role.name,
    }

    for key, value in list(kwargs.items()):
        log_params[key] = value

    if prototype.delegate_user:
        log_params["delegate_user"] = prototype.delegate_user.username
    elif prototype.delegate_team:
        log_params["delegate_team"] = prototype.delegate_team.name

    log_action(action_kind, orgname, log_params)


@resource("/v1/organization/<orgname>/prototypes")
@path_param("orgname", "The name of the organization")
class PermissionPrototypeList(ApiResource):
    """
    Resource for listing and creating permission prototypes.
    """

    schemas = {
        "NewPrototype": {
            "type": "object",
            "description": "Description of a new prototype",
            "required": ["role", "delegate",],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role that should be applied to the delegate",
                    "enum": ["read", "write", "admin",],
                },
                "activating_user": {
                    "type": "object",
                    "description": "Repository creating user to whom the rule should apply",
                    "required": ["name",],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The username for the activating_user",
                        },
                    },
                },
                "delegate": {
                    "type": "object",
                    "description": "Information about the user or team to which the rule grants access",
                    "required": ["name", "kind",],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name for the delegate team or user",
                        },
                        "kind": {
                            "type": "string",
                            "description": "Whether the delegate is a user or a team",
                            "enum": ["user", "team",],
                        },
                    },
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrganizationPrototypePermissions")
    def get(self, orgname):
        """
        List the existing prototypes for this organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            permissions = model.permission.get_prototype_permissions(org)

            users_filter = {p.activating_user for p in permissions} | {
                p.delegate_user for p in permissions
            }
            org_members = model.organization.get_organization_member_set(
                org, users_filter=users_filter
            )
            return {"prototypes": [prototype_view(p, org_members) for p in permissions]}

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrganizationPrototypePermission")
    @validate_json_request("NewPrototype")
    def post(self, orgname):
        """
        Create a new permission prototype.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            details = request.get_json()
            activating_username = None

            if (
                "activating_user" in details
                and details["activating_user"]
                and "name" in details["activating_user"]
            ):
                activating_username = details["activating_user"]["name"]

            delegate = details["delegate"] if "delegate" in details else {}
            delegate_kind = delegate.get("kind", None)
            delegate_name = delegate.get("name", None)

            delegate_username = delegate_name if delegate_kind == "user" else None
            delegate_teamname = delegate_name if delegate_kind == "team" else None

            activating_user = (
                model.user.get_user(activating_username) if activating_username else None
            )
            delegate_user = model.user.get_user(delegate_username) if delegate_username else None
            delegate_team = (
                model.team.get_organization_team(orgname, delegate_teamname)
                if delegate_teamname
                else None
            )

            if activating_username and not activating_user:
                raise request_error(message="Unknown activating user")

            if not delegate_user and not delegate_team:
                raise request_error(message="Missing delegate user or team")

            role_name = details["role"]

            prototype = model.permission.add_prototype_permission(
                org, role_name, activating_user, delegate_user, delegate_team
            )
            log_prototype_action("create_prototype_permission", orgname, prototype)

            users_filter = {prototype.activating_user, prototype.delegate_user}
            org_members = model.organization.get_organization_member_set(
                org, users_filter=users_filter
            )
            return prototype_view(prototype, org_members)

        raise Unauthorized()


@resource("/v1/organization/<orgname>/prototypes/<prototypeid>")
@path_param("orgname", "The name of the organization")
@path_param("prototypeid", "The ID of the prototype")
class PermissionPrototype(ApiResource):
    """
    Resource for managingin individual permission prototypes.
    """

    schemas = {
        "PrototypeUpdate": {
            "type": "object",
            "description": "Description of a the new prototype role",
            "required": ["role",],
            "properties": {
                "role": {
                    "type": "string",
                    "description": "Role that should be applied to the permission",
                    "enum": ["read", "write", "admin",],
                },
            },
        },
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrganizationPrototypePermission")
    def delete(self, orgname, prototypeid):
        """
        Delete an existing permission prototype.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            prototype = model.permission.delete_prototype_permission(org, prototypeid)
            if not prototype:
                raise NotFound()

            log_prototype_action("delete_prototype_permission", orgname, prototype)

            return "", 204

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("updateOrganizationPrototypePermission")
    @validate_json_request("PrototypeUpdate")
    def put(self, orgname, prototypeid):
        """
        Update the role of an existing permission prototype.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            try:
                org = model.organization.get_organization(orgname)
            except model.InvalidOrganizationException:
                raise NotFound()

            existing = model.permission.get_prototype_permission(org, prototypeid)
            if not existing:
                raise NotFound()

            details = request.get_json()
            role_name = details["role"]
            prototype = model.permission.update_prototype_permission(org, prototypeid, role_name)
            if not prototype:
                raise NotFound()

            log_prototype_action(
                "modify_prototype_permission", orgname, prototype, original_role=existing.role.name
            )

            users_filter = {prototype.activating_user, prototype.delegate_user}
            org_members = model.organization.get_organization_member_set(
                org, users_filter=users_filter
            )
            return prototype_view(prototype, org_members)

        raise Unauthorized()
