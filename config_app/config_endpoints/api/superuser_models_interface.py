from abc import ABCMeta, abstractmethod
from collections import namedtuple
from six import add_metaclass

from config_app.config_endpoints.api import format_date


def user_view(user):
    return {
        "name": user.username,
        "kind": "user",
        "is_robot": user.robot,
    }


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
  RepositoryBuild represents a build associated with a repostiory
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
  Approval represents whether a key has been approved or not
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
  ServiceKey is an apostille signing key
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
        }


@add_metaclass(ABCMeta)
class SuperuserDataInterface(object):
    """
  Interface that represents all data store interactions required by a superuser api.
  """

    @abstractmethod
    def list_all_service_keys(self):
        """
    Returns a list of service keys
    """
