from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass

from endpoints.api import format_date


class Permission(
    namedtuple("Permission", ["repository_name", "repository_visibility_name", "role_name"])
):
    """
    Permission the relationship between a robot and a repository and whether that robot can see the
    repo.
    """

    def to_dict(self):
        return {
            "repository": {
                "name": self.repository_name,
                "is_public": self.repository_visibility_name == "public",
            },
            "role": self.role_name,
        }


class Team(namedtuple("Team", ["name", "avatar"])):
    """
    Team represents a team entry for a robot list entry.

    :type name: string
    :type avatar: {string -> string}
    """

    def to_dict(self):
        return {
            "name": self.name,
            "avatar": self.avatar,
        }


class RobotWithPermissions(
    namedtuple(
        "RobotWithPermissions",
        [
            "name",
            "password",
            "created",
            "last_accessed",
            "teams",
            "repository_names",
            "description",
        ],
    )
):
    """
    RobotWithPermissions is a list of robot entries.

    :type name: string
    :type password: string
    :type created: datetime|None
    :type last_accessed: datetime|None
    :type teams: [Team]
    :type repository_names: [string]
    :type description: string
    """

    def to_dict(self, include_token=False):
        data = {
            "name": self.name,
            "created": format_date(self.created) if self.created is not None else None,
            "last_accessed": format_date(self.last_accessed)
            if self.last_accessed is not None
            else None,
            "teams": [team.to_dict() for team in self.teams],
            "repositories": self.repository_names,
            "description": self.description,
        }

        if include_token:
            data["token"] = self.password

        return data


class Robot(
    namedtuple(
        "Robot",
        [
            "name",
            "password",
            "created",
            "last_accessed",
            "description",
            "unstructured_metadata",
        ],
    )
):
    """
    Robot represents a robot entity.

    :type name: string
    :type password: string
    :type created: datetime|None
    :type last_accessed: datetime|None
    :type description: string
    :type unstructured_metadata: dict
    """

    def to_dict(self, include_metadata=False, include_token=False):
        data = {
            "name": self.name,
            "created": format_date(self.created) if self.created is not None else None,
            "last_accessed": format_date(self.last_accessed)
            if self.last_accessed is not None
            else None,
            "description": self.description,
        }

        if include_token:
            data["token"] = self.password

        if include_metadata:
            data["unstructured_metadata"] = self.unstructured_metadata

        return data


@add_metaclass(ABCMeta)
class RobotInterface(object):
    """
    Interface that represents all data store interactions required by the Robot API.
    """

    @abstractmethod
    def get_org_robot(self, robot_shortname, orgname):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def get_user_robot(self, robot_shortname, owning_user):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def create_user_robot(self, robot_shortname, owning_user):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def create_org_robot(self, robot_shortname, orgname):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def delete_robot(self, robot_username):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def regenerate_user_robot_token(self, robot_shortname, owning_user):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def regenerate_org_robot_token(self, robot_shortname, orgname):
        """

        Returns:
          Robot object

        """

    @abstractmethod
    def list_entity_robot_permission_teams(
        self, prefix, include_permissions=False, include_token=False, limit=None
    ):
        """

        Returns:
          list of RobotWithPermissions objects

        """

    @abstractmethod
    def list_robot_permissions(self, username):
        """

        Returns:
          list of Robot objects

        """

    @abstractmethod
    def robot_has_mirror(self, robot_username):
        """
        Returns:
          True if robot is being used by mirror,
          False otherwise.
        """
