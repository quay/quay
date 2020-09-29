import features

from flask import request

from app import all_queues, userfiles, namespace_gc_queue
from auth.permissions import (
    ReadRepositoryPermission,
    ModifyRepositoryPermission,
    AdministerRepositoryPermission,
)
from data import model, database
from endpoints.api.build import get_job_config, _get_build_status
from endpoints.api.superuser_models_interface import BuildTrigger
from endpoints.api.superuser_models_interface import (
    SuperuserDataInterface,
    Organization,
    User,
    ServiceKey,
    Approval,
    RepositoryBuild,
)
from util.request import get_request_ip


def _create_user(user):
    if user is None:
        return None
    return User(user.username, user.email, user.verified, user.enabled, user.robot)


def _create_key(key):
    approval = None
    if key.approval is not None:
        approval = Approval(
            _create_user(key.approval.approver),
            key.approval.approval_type,
            key.approval.approved_date,
            key.approval.notes,
        )

    return ServiceKey(
        key.name,
        key.kid,
        key.service,
        key.jwk,
        key.metadata,
        key.created_date,
        key.expiration_date,
        key.rotation_duration,
        approval,
    )


class ServiceKeyDoesNotExist(Exception):
    pass


class ServiceKeyAlreadyApproved(Exception):
    pass


class InvalidRepositoryBuildException(Exception):
    pass


class PreOCIModel(SuperuserDataInterface):
    """
    PreOCIModel implements the data model for the SuperUser using a database schema before it was
    changed to support the OCI specification.
    """

    def get_repository_build(self, uuid):
        try:
            build = model.build.get_repository_build(uuid)
        except model.InvalidRepositoryBuildException as e:
            raise InvalidRepositoryBuildException(str(e))

        repo_namespace = build.repository.namespace_user.username
        repo_name = build.repository.name

        can_read = ReadRepositoryPermission(repo_namespace, repo_name).can()
        can_write = ModifyRepositoryPermission(repo_namespace, repo_name).can()
        can_admin = AdministerRepositoryPermission(repo_namespace, repo_name).can()
        job_config = get_job_config(build.job_config)
        phase, status, error = _get_build_status(build)
        url = userfiles.get_file_url(self.resource_key, get_request_ip(), requires_cors=True)

        return RepositoryBuild(
            build.uuid,
            build.logs_archived,
            repo_namespace,
            repo_name,
            can_write,
            can_read,
            _create_user(build.pull_robot),
            build.resource_key,
            BuildTrigger(
                build.trigger.uuid,
                build.trigger.service.name,
                _create_user(build.trigger.pull_robot),
                can_read,
                can_admin,
                True,
            ),
            build.display_name,
            build.display_name,
            build.started,
            job_config,
            phase,
            status,
            error,
            url,
        )

    def delete_service_key(self, kid):
        try:
            key = model.service_keys.delete_service_key(kid)
        except model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist
        return _create_key(key)

    def update_service_key(self, kid, name=None, metadata=None):
        model.service_keys.update_service_key(kid, name, metadata)

    def set_key_expiration(self, kid, expiration_date):
        model.service_keys.set_key_expiration(kid, expiration_date)

    def get_service_key(self, kid, service=None, alive_only=True, approved_only=True):
        try:
            key = model.service_keys.get_service_key(
                kid, approved_only=approved_only, alive_only=alive_only
            )
            return _create_key(key)
        except model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist

    def approve_service_key(self, kid, approver, approval_type, notes=""):
        try:
            key = model.service_keys.approve_service_key(
                kid, approval_type, approver=approver, notes=notes
            )
            return _create_key(key)
        except model.ServiceKeyDoesNotExist:
            raise ServiceKeyDoesNotExist
        except model.ServiceKeyAlreadyApproved:
            raise ServiceKeyAlreadyApproved

    def generate_service_key(
        self, service, expiration_date, kid=None, name="", metadata=None, rotation_duration=None
    ):
        (private_key, key) = model.service_keys.generate_service_key(
            service, expiration_date, metadata=metadata, name=name
        )

        return private_key, key.kid

    def list_all_service_keys(self):
        keys = model.service_keys.list_all_keys()
        return [_create_key(key) for key in keys]

    def change_organization_name(self, old_org_name, new_org_name):
        org = model.organization.get_organization(old_org_name)
        if new_org_name is not None:
            org = model.user.change_username(org.id, new_org_name)

        return Organization(org.username, org.email)

    def mark_organization_for_deletion(self, name):
        org = model.organization.get_organization(name)
        model.user.mark_namespace_for_deletion(org, all_queues, namespace_gc_queue, force=True)

    def take_ownership(self, namespace, authed_user):
        entity = model.user.get_user_or_org(namespace)
        if entity is None:
            return None, False

        was_user = not entity.organization
        if entity.organization:
            # Add the superuser as an admin to the owners team of the org.
            model.organization.add_user_as_admin(authed_user, entity)
        else:
            # If the entity is a user, convert it to an organization and add the current superuser
            # as the admin.
            model.organization.convert_user_to_organization(entity, authed_user)
        return entity.id, was_user

    def update_enabled(self, username, enabled):
        user = model.user.get_nonrobot_user(username)
        model.user.update_enabled(user, bool(enabled))

    def update_email(self, username, email, auto_verify):
        user = model.user.get_nonrobot_user(username)
        model.user.update_email(user, email, auto_verify)

    def change_password(self, username, password):
        user = model.user.get_nonrobot_user(username)
        model.user.change_password(user, password)

    def mark_user_for_deletion(self, username):
        user = model.user.get_nonrobot_user(username)
        model.user.mark_namespace_for_deletion(user, all_queues, namespace_gc_queue, force=True)

    def create_reset_password_email_code(self, email):
        code = model.user.create_reset_password_email_code(email)
        return code

    def get_nonrobot_user(self, username):
        user = model.user.get_nonrobot_user(username)
        if user is None:
            return None
        return _create_user(user)

    def create_install_user(self, username, password, email):
        prompts = model.user.get_default_user_prompts(features)
        user = model.user.create_user(
            username,
            password,
            email,
            auto_verify=not features.MAILING,
            email_required=features.MAILING,
            prompts=prompts,
        )

        return_user = _create_user(user)
        # If mailing is turned on, send the user a verification email.
        if features.MAILING:
            confirmation_code = model.user.create_confirm_email_code(user)
            return return_user, confirmation_code

        return return_user, ""

    def get_active_users(self, disabled=True):
        users = model.user.get_active_users(disabled=disabled)
        return [_create_user(user) for user in users]

    def get_organizations(self):
        return [
            Organization(org.username, org.email) for org in model.organization.get_organizations()
        ]


pre_oci_model = PreOCIModel()
