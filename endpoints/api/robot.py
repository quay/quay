"""
Manage user and organization robot accounts.
"""
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    log_action,
    related_user_resource,
    request_error,
    require_user_admin,
    require_scope,
    path_param,
    parse_args,
    query_param,
    validate_json_request,
    max_json_size,
)
from endpoints.api.robot_models_pre_oci import pre_oci_model as model
from endpoints.exception import Unauthorized
from auth.permissions import AdministerOrganizationPermission, OrganizationMemberPermission
from auth.auth_context import get_authenticated_user
from auth import scopes
from util.names import format_robot_username
from util.parsing import truthy_bool
from flask import abort, request


CREATE_ROBOT_SCHEMA = {
    "type": "object",
    "description": "Optional data for creating a robot",
    "properties": {
        "description": {
            "type": "string",
            "description": "Optional text description for the robot",
            "maxLength": 255,
        },
        "unstructured_metadata": {
            "type": "object",
            "description": "Optional unstructured metadata for the robot",
        },
    },
}

ROBOT_MAX_SIZE = 1024 * 1024  # 1 KB.


def robots_list(prefix, include_permissions=False, include_token=False, limit=None):
    robots = model.list_entity_robot_permission_teams(
        prefix, limit=limit, include_token=include_token, include_permissions=include_permissions
    )
    return {"robots": [robot.to_dict(include_token=include_token) for robot in robots]}


@resource("/v1/user/robots")
class UserRobotList(ApiResource):
    """
    Resource for listing user robots.
    """

    @require_user_admin
    @nickname("getUserRobots")
    @parse_args()
    @query_param(
        "permissions",
        "Whether to include repositories and teams in which the robots have permission.",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "token", "If false, the robot's token is not returned.", type=truthy_bool, default=True
    )
    @query_param("limit", "If specified, the number of robots to return.", type=int, default=None)
    def get(self, parsed_args):
        """
        List the available robots for the user.
        """
        user = get_authenticated_user()
        return robots_list(
            user.username,
            include_token=parsed_args.get("token", True),
            include_permissions=parsed_args.get("permissions", False),
            limit=parsed_args.get("limit"),
        )


@resource("/v1/user/robots/<robot_shortname>")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
class UserRobot(ApiResource):
    """
    Resource for managing a user's robots.
    """

    schemas = {
        "CreateRobot": CREATE_ROBOT_SCHEMA,
    }

    @require_user_admin
    @nickname("getUserRobot")
    def get(self, robot_shortname):
        """
        Returns the user's robot with the specified name.
        """
        parent = get_authenticated_user()
        robot = model.get_user_robot(robot_shortname, parent)
        return robot.to_dict(include_metadata=True, include_token=True)

    @require_user_admin
    @nickname("createUserRobot")
    @max_json_size(ROBOT_MAX_SIZE)
    @validate_json_request("CreateRobot", optional=True)
    def put(self, robot_shortname):
        """
        Create a new user robot with the specified name.
        """
        parent = get_authenticated_user()
        create_data = request.get_json() or {}
        robot = model.create_user_robot(
            robot_shortname,
            parent,
            create_data.get("description"),
            create_data.get("unstructured_metadata"),
        )
        log_action(
            "create_robot",
            parent.username,
            {
                "robot": robot_shortname,
                "description": create_data.get("description"),
                "unstructured_metadata": create_data.get("unstructured_metadata"),
            },
        )
        return robot.to_dict(include_metadata=True, include_token=True), 201

    @require_user_admin
    @nickname("deleteUserRobot")
    def delete(self, robot_shortname):
        """
        Delete an existing robot.
        """
        parent = get_authenticated_user()
        robot_username = format_robot_username(parent.username, robot_shortname)

        if not model.robot_has_mirror(robot_username):
            model.delete_robot(robot_username)
            log_action("delete_robot", parent.username, {"robot": robot_shortname})
            return "", 204
        else:
            raise request_error(message="Robot is being used by a mirror")


@resource("/v1/organization/<orgname>/robots")
@path_param("orgname", "The name of the organization")
@related_user_resource(UserRobotList)
class OrgRobotList(ApiResource):
    """
    Resource for listing an organization's robots.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgRobots")
    @parse_args()
    @query_param(
        "permissions",
        "Whether to include repostories and teams in which the robots have permission.",
        type=truthy_bool,
        default=False,
    )
    @query_param(
        "token", "If false, the robot's token is not returned.", type=truthy_bool, default=True
    )
    @query_param("limit", "If specified, the number of robots to return.", type=int, default=None)
    def get(self, orgname, parsed_args):
        """
        List the organization's robots.
        """
        permission = OrganizationMemberPermission(orgname)
        if permission.can():
            include_token = AdministerOrganizationPermission(orgname).can() and parsed_args.get(
                "token", True
            )
            include_permissions = AdministerOrganizationPermission(
                orgname
            ).can() and parsed_args.get("permissions", False)
            return robots_list(
                orgname,
                include_permissions=include_permissions,
                include_token=include_token,
                limit=parsed_args.get("limit"),
            )

        raise Unauthorized()


@resource("/v1/organization/<orgname>/robots/<robot_shortname>")
@path_param("orgname", "The name of the organization")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
@related_user_resource(UserRobot)
class OrgRobot(ApiResource):
    """
    Resource for managing an organization's robots.
    """

    schemas = {
        "CreateRobot": CREATE_ROBOT_SCHEMA,
    }

    @require_scope(scopes.ORG_ADMIN)
    @nickname("getOrgRobot")
    def get(self, orgname, robot_shortname):
        """
        Returns the organization's robot with the specified name.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            robot = model.get_org_robot(robot_shortname, orgname)
            return robot.to_dict(include_metadata=True, include_token=True)

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("createOrgRobot")
    @max_json_size(ROBOT_MAX_SIZE)
    @validate_json_request("CreateRobot", optional=True)
    def put(self, orgname, robot_shortname):
        """
        Create a new robot in the organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            create_data = request.get_json() or {}
            robot = model.create_org_robot(
                robot_shortname,
                orgname,
                create_data.get("description"),
                create_data.get("unstructured_metadata"),
            )
            log_action(
                "create_robot",
                orgname,
                {
                    "robot": robot_shortname,
                    "description": create_data.get("description"),
                    "unstructured_metadata": create_data.get("unstructured_metadata"),
                },
            )
            return robot.to_dict(include_metadata=True, include_token=True), 201

        raise Unauthorized()

    @require_scope(scopes.ORG_ADMIN)
    @nickname("deleteOrgRobot")
    def delete(self, orgname, robot_shortname):
        """
        Delete an existing organization robot.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            robot_username = format_robot_username(orgname, robot_shortname)
            if not model.robot_has_mirror(robot_username):
                model.delete_robot(robot_username)
                log_action("delete_robot", orgname, {"robot": robot_shortname})
                return "", 204
            else:
                raise request_error(message="Robot is being used by a mirror")

        raise Unauthorized()


@resource("/v1/user/robots/<robot_shortname>/permissions")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
class UserRobotPermissions(ApiResource):
    """
    Resource for listing the permissions a user's robot has in the system.
    """

    @require_user_admin
    @nickname("getUserRobotPermissions")
    def get(self, robot_shortname):
        """
        Returns the list of repository permissions for the user's robot.
        """
        parent = get_authenticated_user()
        robot = model.get_user_robot(robot_shortname, parent)
        permissions = model.list_robot_permissions(robot.name)

        return {"permissions": [permission.to_dict() for permission in permissions]}


@resource("/v1/organization/<orgname>/robots/<robot_shortname>/permissions")
@path_param("orgname", "The name of the organization")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
@related_user_resource(UserRobotPermissions)
class OrgRobotPermissions(ApiResource):
    """
    Resource for listing the permissions an org's robot has in the system.
    """

    @require_user_admin
    @nickname("getOrgRobotPermissions")
    def get(self, orgname, robot_shortname):
        """
        Returns the list of repository permissions for the org's robot.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            robot = model.get_org_robot(robot_shortname, orgname)
            permissions = model.list_robot_permissions(robot.name)

            return {"permissions": [permission.to_dict() for permission in permissions]}

        abort(403)


@resource("/v1/user/robots/<robot_shortname>/regenerate")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
class RegenerateUserRobot(ApiResource):
    """
    Resource for regenerate an organization's robot's token.
    """

    @require_user_admin
    @nickname("regenerateUserRobotToken")
    def post(self, robot_shortname):
        """
        Regenerates the token for a user's robot.
        """
        parent = get_authenticated_user()
        robot = model.regenerate_user_robot_token(robot_shortname, parent)
        log_action("regenerate_robot_token", parent.username, {"robot": robot_shortname})
        return robot.to_dict(include_token=True)


@resource("/v1/organization/<orgname>/robots/<robot_shortname>/regenerate")
@path_param("orgname", "The name of the organization")
@path_param(
    "robot_shortname", "The short name for the robot, without any user or organization prefix"
)
@related_user_resource(RegenerateUserRobot)
class RegenerateOrgRobot(ApiResource):
    """
    Resource for regenerate an organization's robot's token.
    """

    @require_scope(scopes.ORG_ADMIN)
    @nickname("regenerateOrgRobotToken")
    def post(self, orgname, robot_shortname):
        """
        Regenerates the token for an organization robot.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            robot = model.regenerate_org_robot_token(robot_shortname, orgname)
            log_action("regenerate_robot_token", orgname, {"robot": robot_shortname})
            return robot.to_dict(include_token=True)

        raise Unauthorized()
