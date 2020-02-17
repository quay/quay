import json
from abc import ABCMeta, abstractmethod
from collections import namedtuple
from datetime import datetime

from dateutil.relativedelta import relativedelta
from six import add_metaclass
from tzlocal import get_localzone

from app import avatar, superusers
from buildtrigger.basehandler import BuildTriggerHandler
from data import model
from endpoints.api import format_date
from util.morecollections import AttrDict


def user_view(user):
    return {
        "name": user.username,
        "kind": "user",
        "is_robot": user.robot,
    }


class BuildTrigger(
    namedtuple(
        "BuildTrigger", ["uuid", "service_name", "pull_robot", "can_read", "can_admin", "for_build"]
    )
):
    """
    BuildTrigger represent a trigger that is associated with a build.

    :type uuid: string
    :type service_name: string
    :type pull_robot: User
    :type can_read: boolean
    :type can_admin: boolean
    :type for_build: boolean
    """

    def to_dict(self):
        if not self.uuid:
            return None

        build_trigger = BuildTriggerHandler.get_handler(self)
        build_source = build_trigger.config.get("build_source")

        repo_url = build_trigger.get_repository_url() if build_source else None
        can_read = self.can_read or self.can_admin

        trigger_data = {
            "id": self.uuid,
            "service": self.service_name,
            "is_active": build_trigger.is_active(),
            "build_source": build_source if can_read else None,
            "repository_url": repo_url if can_read else None,
            "config": build_trigger.config if self.can_admin else {},
            "can_invoke": self.can_admin,
        }

        if not self.for_build and self.can_admin and self.pull_robot:
            trigger_data["pull_robot"] = user_view(self.pull_robot)

        return trigger_data


class RepositoryBuild(
    namedtuple(
        "RepositoryBuild",
        [
            "uuid",
            "logs_archived",
            "repository_namespace_user_username",
            "repository_name",
            "can_write",
            "can_read",
            "pull_robot",
            "resource_key",
            "trigger",
            "display_name",
            "started",
            "job_config",
            "phase",
            "status",
            "error",
            "archive_url",
        ],
    )
):
    """
    RepositoryBuild represents a build associated with a repostiory.

    :type uuid: string
    :type logs_archived: boolean
    :type repository_namespace_user_username: string
    :type repository_name: string
    :type can_write: boolean
    :type can_write: boolean
    :type pull_robot: User
    :type resource_key: string
    :type trigger: Trigger
    :type display_name: string
    :type started: boolean
    :type job_config: {Any -> Any}
    :type phase: string
    :type status: string
    :type error: string
    :type archive_url: string
    """

    def to_dict(self):

        resp = {
            "id": self.uuid,
            "phase": self.phase,
            "started": format_date(self.started),
            "display_name": self.display_name,
            "status": self.status or {},
            "subdirectory": self.job_config.get("build_subdir", ""),
            "dockerfile_path": self.job_config.get("build_subdir", ""),
            "context": self.job_config.get("context", ""),
            "tags": self.job_config.get("docker_tags", []),
            "manual_user": self.job_config.get("manual_user", None),
            "is_writer": self.can_write,
            "trigger": self.trigger.to_dict(),
            "trigger_metadata": self.job_config.get("trigger_metadata", None)
            if self.can_read
            else None,
            "resource_key": self.resource_key,
            "pull_robot": user_view(self.pull_robot) if self.pull_robot else None,
            "repository": {
                "namespace": self.repository_namespace_user_username,
                "name": self.repository_name,
            },
            "error": self.error,
        }

        if self.can_write:
            if self.resource_key is not None:
                resp["archive_url"] = self.archive_url
            elif self.job_config.get("archive_url", None):
                resp["archive_url"] = self.job_config["archive_url"]

        return resp


class Approval(namedtuple("Approval", ["approver", "approval_type", "approved_date", "notes"])):
    """
    Approval represents whether a key has been approved or not.

    :type approver: User
    :type approval_type: string
    :type approved_date: Date
    :type notes: string
    """

    def to_dict(self):
        return {
            "approver": self.approver.to_dict() if self.approver else None,
            "approval_type": self.approval_type,
            "approved_date": self.approved_date,
            "notes": self.notes,
        }


class ServiceKey(
    namedtuple(
        "ServiceKey",
        [
            "name",
            "kid",
            "service",
            "jwk",
            "metadata",
            "created_date",
            "expiration_date",
            "rotation_duration",
            "approval",
        ],
    )
):
    """
    ServiceKey is an apostille signing key.

    :type name: string
    :type kid: int
    :type service: string
    :type jwk: string
    :type metadata: string
    :type created_date: Date
    :type expiration_date: Date
    :type rotation_duration: Date
    :type approval: Approval
    """

    def to_dict(self):
        return {
            "name": self.name,
            "kid": self.kid,
            "service": self.service,
            "jwk": self.jwk,
            "metadata": self.metadata,
            "created_date": self.created_date,
            "expiration_date": self.expiration_date,
            "rotation_duration": self.rotation_duration,
            "approval": self.approval.to_dict() if self.approval is not None else None,
        }


class User(namedtuple("User", ["username", "email", "verified", "enabled", "robot"])):
    """
    User represents a single user.

    :type username: string
    :type email: string
    :type verified: boolean
    :type enabled: boolean
    :type robot: User
    """

    def to_dict(self):
        user_data = {
            "kind": "user",
            "name": self.username,
            "username": self.username,
            "email": self.email,
            "verified": self.verified,
            "avatar": avatar.get_data_for_user(self),
            "super_user": superusers.is_superuser(self.username),
            "enabled": self.enabled,
        }

        return user_data


class Organization(namedtuple("Organization", ["username", "email"])):
    """
    Organization represents a single org.

    :type username: string
    :type email: string
    """

    def to_dict(self):
        return {
            "name": self.username,
            "email": self.email,
            "avatar": avatar.get_data_for_org(self),
        }


@add_metaclass(ABCMeta)
class SuperuserDataInterface(object):
    """
    Interface that represents all data store interactions required by a superuser api.
    """

    @abstractmethod
    def get_organizations(self):
        """
        Returns a list of Organization.
        """

    @abstractmethod
    def get_active_users(self):
        """
        Returns a list of User.
        """

    @abstractmethod
    def create_install_user(self, username, password, email):
        """
        Returns the created user and confirmation code for email confirmation.
        """

    @abstractmethod
    def get_nonrobot_user(self, username):
        """
        Returns a User.
        """

    @abstractmethod
    def create_reset_password_email_code(self, email):
        """
        Returns a recover password code.
        """

    @abstractmethod
    def mark_user_for_deletion(self, username):
        """
        Returns None.
        """

    @abstractmethod
    def change_password(self, username, password):
        """
        Returns None.
        """

    @abstractmethod
    def update_email(self, username, email, auto_verify):
        """
        Returns None.
        """

    @abstractmethod
    def update_enabled(self, username, enabled):
        """
        Returns None.
        """

    @abstractmethod
    def take_ownership(self, namespace, authed_user):
        """
        Returns id of entity and whether the entity was a user.
        """

    @abstractmethod
    def mark_organization_for_deletion(self, name):
        """
        Returns None.
        """

    @abstractmethod
    def change_organization_name(self, old_org_name, new_org_name):
        """
        Returns updated Organization.
        """

    @abstractmethod
    def list_all_service_keys(self):
        """
        Returns a list of service keys.
        """

    @abstractmethod
    def generate_service_key(
        self, service, expiration_date, kid=None, name="", metadata=None, rotation_duration=None
    ):
        """
        Returns a tuple of private key and public key id.
        """

    @abstractmethod
    def approve_service_key(self, kid, approver, approval_type, notes=""):
        """
        Returns the approved Key.
        """

    @abstractmethod
    def get_service_key(self, kid, service=None, alive_only=True, approved_only=True):
        """
        Returns ServiceKey.
        """

    @abstractmethod
    def set_key_expiration(self, kid, expiration_date):
        """
        Returns None.
        """

    @abstractmethod
    def update_service_key(self, kid, name=None, metadata=None):
        """
        Returns None.
        """

    @abstractmethod
    def delete_service_key(self, kid):
        """
        Returns deleted ServiceKey.
        """

    @abstractmethod
    def get_repository_build(self, uuid):
        """
        Returns RepositoryBuild.
        """
