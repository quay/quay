import features

from app import avatar
from data import model
from data.database import (
    User,
    FederatedLogin,
    RobotAccountToken,
    Team as TeamTable,
    Repository,
    RobotAccountMetadata,
)
from endpoints.api.robot_models_interface import (
    RobotInterface,
    Robot,
    RobotWithPermissions,
    Team,
    Permission,
)


class RobotPreOCIModel(RobotInterface):
    def list_robot_permissions(self, username):
        permissions = model.permission.list_robot_permissions(username)
        return [
            Permission(
                permission.repository.name,
                model.repository.repository_visibility_name(permission.repository),
                permission.role.name,
            )
            for permission in permissions
        ]

    def list_entity_robot_permission_teams(
        self, prefix, include_token=False, include_permissions=False, limit=None
    ):
        tuples = model.user.list_entity_robot_permission_teams(
            prefix, limit=limit, include_permissions=include_permissions
        )
        robots = {}
        robot_teams = set()

        for robot_tuple in tuples:
            robot_name = robot_tuple.get(User.username)
            if robot_name not in robots:
                token = None
                if include_token:
                    if robot_tuple.get(RobotAccountToken.token):
                        token = robot_tuple.get(RobotAccountToken.token).decrypt()

                robot_dict = {
                    "name": robot_name,
                    "token": token,
                    "created": robot_tuple.get(User.creation_date),
                    "last_accessed": (
                        robot_tuple.get(User.last_accessed) if features.USER_LAST_ACCESSED else None
                    ),
                    "description": robot_tuple.get(RobotAccountMetadata.description),
                    "unstructured_metadata": robot_tuple.get(
                        RobotAccountMetadata.unstructured_json
                    ),
                }

                if include_permissions:
                    robot_dict.update(
                        {
                            "teams": [],
                            "repositories": [],
                        }
                    )

            robots[robot_name] = Robot(
                robot_dict["name"],
                robot_dict["token"],
                robot_dict["created"],
                robot_dict["last_accessed"],
                robot_dict["description"],
                robot_dict["unstructured_metadata"],
            )
            if include_permissions:
                team_name = robot_tuple.get(TeamTable.name)
                repository_name = robot_tuple.get(Repository.name)

                if team_name is not None:
                    check_key = robot_name + ":" + team_name
                    if check_key not in robot_teams:
                        robot_teams.add(check_key)

                        robot_dict["teams"].append(
                            Team(team_name, avatar.get_data(team_name, team_name, "team"))
                        )

                if repository_name is not None:
                    if repository_name not in robot_dict["repositories"]:
                        robot_dict["repositories"].append(repository_name)
                robots[robot_name] = RobotWithPermissions(
                    robot_dict["name"],
                    robot_dict["token"],
                    robot_dict["created"],
                    (robot_dict["last_accessed"] if features.USER_LAST_ACCESSED else None),
                    robot_dict["teams"],
                    robot_dict["repositories"],
                    robot_dict["description"],
                )

        return list(robots.values())

    def regenerate_user_robot_token(self, robot_shortname, owning_user):
        robot, password, metadata = model.user.regenerate_robot_token(robot_shortname, owning_user)
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            metadata.description,
            metadata.unstructured_json,
        )

    def regenerate_org_robot_token(self, robot_shortname, orgname):
        parent = model.organization.get_organization(orgname)
        robot, password, metadata = model.user.regenerate_robot_token(robot_shortname, parent)
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            metadata.description,
            metadata.unstructured_json,
        )

    def delete_robot(self, robot_username):
        model.user.delete_robot(robot_username)

    def create_user_robot(self, robot_shortname, owning_user, description, unstructured_metadata):
        robot, password = model.user.create_robot(
            robot_shortname, owning_user, description or "", unstructured_metadata
        )
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            description or "",
            unstructured_metadata,
        )

    def create_org_robot(self, robot_shortname, orgname, description, unstructured_metadata):
        parent = model.organization.get_organization(orgname)
        robot, password = model.user.create_robot(
            robot_shortname, parent, description or "", unstructured_metadata
        )
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            description or "",
            unstructured_metadata,
        )

    def get_org_robot(self, robot_shortname, orgname):
        parent = model.organization.get_organization(orgname)
        robot, password, metadata = model.user.get_robot_and_metadata(robot_shortname, parent)
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            metadata.description,
            metadata.unstructured_json,
        )

    def get_user_robot(self, robot_shortname, owning_user):
        robot, password, metadata = model.user.get_robot_and_metadata(robot_shortname, owning_user)
        return Robot(
            robot.username,
            password,
            robot.creation_date,
            robot.last_accessed,
            metadata.description,
            metadata.unstructured_json,
        )

    def robot_has_mirror(self, robot_username):
        robot = model.user.lookup_robot(robot_username)
        return model.repo_mirror.robot_has_mirror(robot)


pre_oci_model = RobotPreOCIModel()
