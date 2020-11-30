import sys
from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class SaveException(Exception):
    def __init__(self, other):
        self.traceback = sys.exc_info()
        super(SaveException, self).__init__(str(other))


class DeleteException(Exception):
    def __init__(self, other):
        self.traceback = sys.exc_info()
        super(DeleteException, self).__init__(str(other))


class Role(namedtuple("Role", ["role_name"])):
    def to_dict(self):
        return {
            "role": self.role_name,
        }


class UserPermission(
    namedtuple(
        "UserPermission",
        [
            "role_name",
            "username",
            "is_robot",
            "avatar",
            "is_org_member",
            "has_org",
        ],
    )
):
    def to_dict(self):
        perm_dict = {
            "role": self.role_name,
            "name": self.username,
            "is_robot": self.is_robot,
            "avatar": self.avatar,
        }
        if self.has_org:
            perm_dict["is_org_member"] = self.is_org_member
        return perm_dict


class RobotPermission(
    namedtuple(
        "RobotPermission",
        [
            "role_name",
            "username",
            "is_robot",
            "is_org_member",
        ],
    )
):
    def to_dict(self, user=None, team=None, org_members=None):
        return {
            "role": self.role_name,
            "name": self.username,
            "is_robot": True,
            "is_org_member": self.is_org_member,
        }


class TeamPermission(
    namedtuple(
        "TeamPermission",
        [
            "role_name",
            "team_name",
            "avatar",
        ],
    )
):
    def to_dict(self):
        return {
            "role": self.role_name,
            "name": self.team_name,
            "avatar": self.avatar,
        }


@add_metaclass(ABCMeta)
class PermissionDataInterface(object):
    """
    Data interface used by permissions API.
    """

    @abstractmethod
    def get_repo_permissions_by_user(self, namespace_name, repository_name):
        """

        Args:
          namespace_name: string
          repository_name: string

        Returns:
          list(UserPermission)
        """

    @abstractmethod
    def get_repo_roles(self, username, namespace_name, repository_name):
        """

        Args:
          username: string
          namespace_name: string
          repository_name: string

        Returns:
          list(Role) or None
        """

    @abstractmethod
    def get_repo_permission_for_user(self, username, namespace_name, repository_name):
        """

        Args:
          username: string
          namespace_name: string
          repository_name: string

        Returns:
          UserPermission
        """

    @abstractmethod
    def set_repo_permission_for_user(self, username, namespace_name, repository_name, role_name):
        """

        Args:
          username: string
          namespace_name: string
          repository_name: string
          role_name: string

        Returns:
          UserPermission

        Raises:
          SaveException
        """

    @abstractmethod
    def delete_repo_permission_for_user(self, username, namespace_name, repository_name):
        """

        Args:
          username: string
          namespace_name: string
          repository_name: string

        Returns:
          void

        Raises:
          DeleteException
        """

    @abstractmethod
    def get_repo_permissions_by_team(self, namespace_name, repository_name):
        """

        Args:
          namespace_name: string
          repository_name: string

        Returns:
          list(TeamPermission)
        """

    @abstractmethod
    def get_repo_role_for_team(self, team_name, namespace_name, repository_name):
        """

        Args:
          team_name: string
          namespace_name: string
          repository_name: string

        Returns:
          Role
        """

    @abstractmethod
    def set_repo_permission_for_team(self, team_name, namespace_name, repository_name, permission):
        """

        Args:
          team_name: string
          namespace_name: string
          repository_name: string
          permission: string

        Returns:
          TeamPermission

        Raises:
          SaveException
        """

    @abstractmethod
    def delete_repo_permission_for_team(self, team_name, namespace_name, repository_name):
        """

        Args:
          team_name: string
          namespace_name: string
          repository_name: string

        Returns:
          TeamPermission

        Raises:
          DeleteException
        """
