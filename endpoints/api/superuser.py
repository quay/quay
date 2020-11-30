"""
Superuser API.
"""
import logging
import os
import string
import socket

from datetime import datetime
from random import SystemRandom

from flask import request, make_response, jsonify

import features

from app import app, avatar, superusers, authentication, config_provider
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import SuperUserPermission
from data.database import ServiceKeyApprovalType
from data.logs_model import logs_model
from endpoints.api import (
    ApiResource,
    nickname,
    resource,
    validate_json_request,
    internal_only,
    require_scope,
    show_if,
    parse_args,
    query_param,
    require_fresh_login,
    path_param,
    verify_not_prod,
    page_support,
    log_action,
    format_date,
    InvalidRequest,
    NotFound,
    Unauthorized,
    InvalidResponse,
)
from endpoints.api.build import get_logs_or_log_url
from endpoints.api.superuser_models_pre_oci import (
    pre_oci_model,
    ServiceKeyDoesNotExist,
    ServiceKeyAlreadyApproved,
    InvalidRepositoryBuildException,
)
from endpoints.api.logs import _validate_logs_arguments
from util.parsing import truthy_bool
from util.request import get_request_ip
from util.useremails import send_confirmation_email, send_recovery_email
from util.validation import validate_service_key_name
from _init import ROOT_DIR

logger = logging.getLogger(__name__)


def get_immediate_subdirectories(directory):
    return [name for name in os.listdir(directory) if os.path.isdir(os.path.join(directory, name))]


def get_services():
    services = set(get_immediate_subdirectories(app.config["SYSTEM_SERVICES_PATH"]))
    services = services - set(app.config["SYSTEM_SERVICE_BLACKLIST"])
    return services


@resource("/v1/superuser/aggregatelogs")
@internal_only
class SuperUserAggregateLogs(ApiResource):
    """
    Resource for fetching aggregated logs for the current user.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("listAllAggregateLogs")
    @parse_args()
    @query_param("starttime", "Earliest time from which to get logs. (%m/%d/%Y %Z)", type=str)
    @query_param("endtime", "Latest time to which to get logs. (%m/%d/%Y %Z)", type=str)
    def get(self, parsed_args):
        """
        Returns the aggregated logs for the current system.
        """
        if SuperUserPermission().can():
            (start_time, end_time) = _validate_logs_arguments(
                parsed_args["starttime"], parsed_args["endtime"]
            )
            aggregated_logs = logs_model.get_aggregated_log_counts(start_time, end_time)
            return {"aggregated": [log.to_dict() for log in aggregated_logs]}

        raise Unauthorized()


LOGS_PER_PAGE = 20


@resource("/v1/superuser/logs")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserLogs(ApiResource):
    """
    Resource for fetching all logs in the system.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("listAllLogs")
    @parse_args()
    @query_param("starttime", "Earliest time from which to get logs (%m/%d/%Y %Z)", type=str)
    @query_param("endtime", "Latest time to which to get logs (%m/%d/%Y %Z)", type=str)
    @query_param("page", "The page number for the logs", type=int, default=1)
    @page_support()
    @require_scope(scopes.SUPERUSER)
    def get(self, parsed_args, page_token):
        """
        List the usage logs for the current system.
        """
        if SuperUserPermission().can():
            start_time = parsed_args["starttime"]
            end_time = parsed_args["endtime"]

            (start_time, end_time) = _validate_logs_arguments(start_time, end_time)
            log_entry_page = logs_model.lookup_logs(start_time, end_time, page_token=page_token)
            return (
                {
                    "start_time": format_date(start_time),
                    "end_time": format_date(end_time),
                    "logs": [
                        log.to_dict(avatar, include_namespace=True) for log in log_entry_page.logs
                    ],
                },
                log_entry_page.next_page_token,
            )

        raise Unauthorized()


def org_view(org):
    return {
        "name": org.username,
        "email": org.email,
        "avatar": avatar.get_data_for_org(org),
    }


def user_view(user, password=None):
    user_data = {
        "kind": "user",
        "name": user.username,
        "username": user.username,
        "email": user.email,
        "verified": user.verified,
        "avatar": avatar.get_data_for_user(user),
        "super_user": superusers.is_superuser(user.username),
        "enabled": user.enabled,
    }

    if password is not None:
        user_data["encrypted_password"] = authentication.encrypt_user_password(password).decode(
            "ascii"
        )

    return user_data


@resource("/v1/superuser/changelog/")
@internal_only
@show_if(features.SUPER_USERS)
class ChangeLog(ApiResource):
    """
    Resource for returning the change log for enterprise customers.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("getChangeLog")
    @require_scope(scopes.SUPERUSER)
    def get(self):
        """
        Returns the change log for this installation.
        """
        if SuperUserPermission().can():
            with open(os.path.join(ROOT_DIR, "CHANGELOG.md"), "r") as f:
                return {"log": f.read()}

        raise Unauthorized()


@resource("/v1/superuser/organizations/")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserOrganizationList(ApiResource):
    """
    Resource for listing organizations in the system.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("listAllOrganizations")
    @require_scope(scopes.SUPERUSER)
    def get(self):
        """
        Returns a list of all organizations in the system.
        """
        if SuperUserPermission().can():
            return {"organizations": [org.to_dict() for org in pre_oci_model.get_organizations()]}

        raise Unauthorized()


@resource("/v1/superuser/users/")
@show_if(features.SUPER_USERS)
class SuperUserList(ApiResource):
    """
    Resource for listing users in the system.
    """

    schemas = {
        "CreateInstallUser": {
            "id": "CreateInstallUser",
            "description": "Data for creating a user",
            "required": ["username"],
            "properties": {
                "username": {
                    "type": "string",
                    "description": "The username of the user being created",
                },
                "email": {
                    "type": "string",
                    "description": "The email address of the user being created",
                },
            },
        }
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("listAllUsers")
    @parse_args()
    @query_param(
        "disabled", "If false, only enabled users will be returned.", type=truthy_bool, default=True
    )
    @require_scope(scopes.SUPERUSER)
    def get(self, parsed_args):
        """
        Returns a list of all users in the system.
        """
        if SuperUserPermission().can():
            users = pre_oci_model.get_active_users(disabled=parsed_args["disabled"])
            return {"users": [user.to_dict() for user in users]}

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("createInstallUser")
    @validate_json_request("CreateInstallUser")
    @require_scope(scopes.SUPERUSER)
    def post(self):
        """
        Creates a new user.
        """
        # Ensure that we are using database auth.
        if app.config["AUTHENTICATION_TYPE"] != "Database":
            raise InvalidRequest("Cannot create a user in a non-database auth system")

        user_information = request.get_json()
        if SuperUserPermission().can():
            # Generate a temporary password for the user.
            random = SystemRandom()
            password = "".join(
                [random.choice(string.ascii_uppercase + string.digits) for _ in range(32)]
            )

            # Create the user.
            username = user_information["username"]
            email = user_information.get("email")
            install_user, confirmation_code = pre_oci_model.create_install_user(
                username, password, email
            )
            if features.MAILING:
                send_confirmation_email(
                    install_user.username, install_user.email, confirmation_code
                )

            return {
                "username": username,
                "email": email,
                "password": password,
                "encrypted_password": authentication.encrypt_user_password(password).decode(
                    "ascii"
                ),
            }

        raise Unauthorized()


@resource("/v1/superusers/users/<username>/sendrecovery")
@internal_only
@show_if(features.SUPER_USERS)
@show_if(features.MAILING)
class SuperUserSendRecoveryEmail(ApiResource):
    """
    Resource for sending a recovery user on behalf of a user.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("sendInstallUserRecoveryEmail")
    @require_scope(scopes.SUPERUSER)
    def post(self, username):
        # Ensure that we are using database auth.
        if app.config["AUTHENTICATION_TYPE"] != "Database":
            raise InvalidRequest("Cannot send a recovery e-mail for non-database auth")

        if SuperUserPermission().can():
            user = pre_oci_model.get_nonrobot_user(username)
            if user is None:
                raise NotFound()

            if superusers.is_superuser(username):
                raise InvalidRequest("Cannot send a recovery email for a superuser")

            code = pre_oci_model.create_reset_password_email_code(user.email)
            send_recovery_email(user.email, code)
            return {"email": user.email}

        raise Unauthorized()


@resource("/v1/superuser/users/<username>")
@path_param("username", "The username of the user being managed")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserManagement(ApiResource):
    """
    Resource for managing users in the system.
    """

    schemas = {
        "UpdateUser": {
            "id": "UpdateUser",
            "type": "object",
            "description": "Description of updates for a user",
            "properties": {
                "password": {
                    "type": "string",
                    "description": "The new password for the user",
                },
                "email": {
                    "type": "string",
                    "description": "The new e-mail address for the user",
                },
                "enabled": {"type": "boolean", "description": "Whether the user is enabled"},
            },
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("getInstallUser")
    @require_scope(scopes.SUPERUSER)
    def get(self, username):
        """
        Returns information about the specified user.
        """
        if SuperUserPermission().can():
            user = pre_oci_model.get_nonrobot_user(username)
            if user is None:
                raise NotFound()

            return user.to_dict()

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("deleteInstallUser")
    @require_scope(scopes.SUPERUSER)
    def delete(self, username):
        """
        Deletes the specified user.
        """
        if SuperUserPermission().can():
            user = pre_oci_model.get_nonrobot_user(username)
            if user is None:
                raise NotFound()

            if superusers.is_superuser(username):
                raise InvalidRequest("Cannot delete a superuser")

            pre_oci_model.mark_user_for_deletion(username)
            return "", 204

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("changeInstallUser")
    @validate_json_request("UpdateUser")
    @require_scope(scopes.SUPERUSER)
    def put(self, username):
        """
        Updates information about the specified user.
        """
        if SuperUserPermission().can():
            user = pre_oci_model.get_nonrobot_user(username)
            if user is None:
                raise NotFound()

            if superusers.is_superuser(username):
                raise InvalidRequest("Cannot update a superuser")

            user_data = request.get_json()
            if "password" in user_data:
                # Ensure that we are using database auth.
                if app.config["AUTHENTICATION_TYPE"] != "Database":
                    raise InvalidRequest("Cannot change password in non-database auth")

                pre_oci_model.change_password(username, user_data["password"])

            if "email" in user_data:
                # Ensure that we are using database auth.
                if app.config["AUTHENTICATION_TYPE"] not in ["Database", "AppToken"]:
                    raise InvalidRequest("Cannot change e-mail in non-database auth")

                pre_oci_model.update_email(username, user_data["email"], auto_verify=True)

            if "enabled" in user_data:
                # Disable/enable the user.
                pre_oci_model.update_enabled(username, bool(user_data["enabled"]))

            if "superuser" in user_data:
                config_object = config_provider.get_config()
                superusers_set = set(config_object["SUPER_USERS"])

                if user_data["superuser"]:
                    superusers_set.add(username)
                elif username in superusers_set:
                    superusers_set.remove(username)

                config_object["SUPER_USERS"] = list(superusers_set)
                config_provider.save_config(config_object)

            return_value = user.to_dict()
            if user_data.get("password") is not None:
                password = user_data.get("password")
                return_value["encrypted_password"] = authentication.encrypt_user_password(
                    password
                ).decode("ascii")
            if user_data.get("email") is not None:
                return_value["email"] = user_data.get("email")

            return return_value

        raise Unauthorized()


@resource("/v1/superuser/takeownership/<namespace>")
@path_param("namespace", "The namespace of the user or organization being managed")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserTakeOwnership(ApiResource):
    """
    Resource for a superuser to take ownership of a namespace.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("takeOwnership")
    @require_scope(scopes.SUPERUSER)
    def post(self, namespace):
        """
        Takes ownership of the specified organization or user.
        """
        if SuperUserPermission().can():
            # Disallow for superusers.
            if superusers.is_superuser(namespace):
                raise InvalidRequest("Cannot take ownership of a superuser")

            authed_user = get_authenticated_user()
            entity_id, was_user = pre_oci_model.take_ownership(namespace, authed_user)
            if entity_id is None:
                raise NotFound()

            # Log the change.
            log_metadata = {
                "entity_id": entity_id,
                "namespace": namespace,
                "was_user": was_user,
                "superuser": authed_user.username,
            }

            log_action("take_ownership", authed_user.username, log_metadata)

            return jsonify({"namespace": namespace})

        raise Unauthorized()


@resource("/v1/superuser/organizations/<name>")
@path_param("name", "The name of the organizaton being managed")
@show_if(features.SUPER_USERS)
class SuperUserOrganizationManagement(ApiResource):
    """
    Resource for managing organizations in the system.
    """

    schemas = {
        "UpdateOrg": {
            "id": "UpdateOrg",
            "type": "object",
            "description": "Description of updates for an organization",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The new name for the organization",
                }
            },
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("deleteOrganization")
    @require_scope(scopes.SUPERUSER)
    def delete(self, name):
        """
        Deletes the specified organization.
        """
        if SuperUserPermission().can():
            pre_oci_model.mark_organization_for_deletion(name)
            return "", 204

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("changeOrganization")
    @validate_json_request("UpdateOrg")
    @require_scope(scopes.SUPERUSER)
    def put(self, name):
        """
        Updates information about the specified user.
        """
        if SuperUserPermission().can():
            org_data = request.get_json()
            old_name = org_data["name"] if "name" in org_data else None
            org = pre_oci_model.change_organization_name(name, old_name)
            return org.to_dict()

        raise Unauthorized()


def key_view(key):
    return {
        "name": key.name,
        "kid": key.kid,
        "service": key.service,
        "jwk": key.jwk,
        "metadata": key.metadata,
        "created_date": key.created_date,
        "expiration_date": key.expiration_date,
        "rotation_duration": key.rotation_duration,
        "approval": approval_view(key.approval) if key.approval is not None else None,
    }


def approval_view(approval):
    return {
        "approver": user_view(approval.approver) if approval.approver else None,
        "approval_type": approval.approval_type,
        "approved_date": approval.approved_date,
        "notes": approval.notes,
    }


@resource("/v1/superuser/keys")
@show_if(features.SUPER_USERS)
class SuperUserServiceKeyManagement(ApiResource):
    """
    Resource for managing service keys.
    """

    schemas = {
        "CreateServiceKey": {
            "id": "CreateServiceKey",
            "type": "object",
            "description": "Description of creation of a service key",
            "required": ["service", "expiration"],
            "properties": {
                "service": {
                    "type": "string",
                    "description": "The service authenticating with this key",
                },
                "name": {
                    "type": "string",
                    "description": "The friendly name of a service key",
                },
                "metadata": {
                    "type": "object",
                    "description": "The key/value pairs of this key's metadata",
                },
                "notes": {
                    "type": "string",
                    "description": "If specified, the extra notes for the key",
                },
                "expiration": {
                    "description": "The expiration date as a unix timestamp",
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                },
            },
        },
    }

    @verify_not_prod
    @nickname("listServiceKeys")
    @require_scope(scopes.SUPERUSER)
    def get(self):
        if SuperUserPermission().can():
            keys = pre_oci_model.list_all_service_keys()

            return jsonify(
                {
                    "keys": [key.to_dict() for key in keys],
                }
            )

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("createServiceKey")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("CreateServiceKey")
    def post(self):
        if SuperUserPermission().can():
            body = request.get_json()
            key_name = body.get("name", "")
            if not validate_service_key_name(key_name):
                raise InvalidRequest("Invalid service key friendly name: %s" % key_name)

            # Ensure we have a valid expiration date if specified.
            expiration_date = body.get("expiration", None)
            if expiration_date is not None:
                try:
                    expiration_date = datetime.utcfromtimestamp(float(expiration_date))
                except ValueError as ve:
                    raise InvalidRequest("Invalid expiration date: %s" % ve)

                if expiration_date <= datetime.now():
                    raise InvalidRequest("Expiration date cannot be in the past")

            # Create the metadata for the key.
            user = get_authenticated_user()
            metadata = body.get("metadata", {})
            metadata.update(
                {
                    "created_by": "Quay Superuser Panel",
                    "creator": user.username,
                    "ip": get_request_ip(),
                }
            )

            # Generate a key with a private key that we *never save*.
            (private_key, key_id) = pre_oci_model.generate_service_key(
                body["service"], expiration_date, metadata=metadata, name=key_name
            )
            # Auto-approve the service key.
            pre_oci_model.approve_service_key(
                key_id, user, ServiceKeyApprovalType.SUPERUSER, notes=body.get("notes", "")
            )

            # Log the creation and auto-approval of the service key.
            key_log_metadata = {
                "kid": key_id,
                "preshared": True,
                "service": body["service"],
                "name": key_name,
                "expiration_date": expiration_date,
                "auto_approved": True,
            }

            log_action("service_key_create", None, key_log_metadata)
            log_action("service_key_approve", None, key_log_metadata)

            return jsonify(
                {
                    "kid": key_id,
                    "name": key_name,
                    "service": body["service"],
                    "public_key": private_key.publickey().exportKey("PEM").decode("ascii"),
                    "private_key": private_key.exportKey("PEM").decode("ascii"),
                }
            )

        raise Unauthorized()


@resource("/v1/superuser/keys/<kid>")
@path_param("kid", "The unique identifier for a service key")
@show_if(features.SUPER_USERS)
class SuperUserServiceKey(ApiResource):
    """
    Resource for managing service keys.
    """

    schemas = {
        "PutServiceKey": {
            "id": "PutServiceKey",
            "type": "object",
            "description": "Description of updates for a service key",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The friendly name of a service key",
                },
                "metadata": {
                    "type": "object",
                    "description": "The key/value pairs of this key's metadata",
                },
                "expiration": {
                    "description": "The expiration date as a unix timestamp",
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                },
            },
        },
    }

    @verify_not_prod
    @nickname("getServiceKey")
    @require_scope(scopes.SUPERUSER)
    def get(self, kid):
        if SuperUserPermission().can():
            try:
                key = pre_oci_model.get_service_key(kid, approved_only=False, alive_only=False)
                return jsonify(key.to_dict())
            except ServiceKeyDoesNotExist:
                raise NotFound()

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("updateServiceKey")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("PutServiceKey")
    def put(self, kid):
        if SuperUserPermission().can():
            body = request.get_json()
            try:
                key = pre_oci_model.get_service_key(kid, approved_only=False, alive_only=False)
            except ServiceKeyDoesNotExist:
                raise NotFound()

            key_log_metadata = {
                "kid": key.kid,
                "service": key.service,
                "name": body.get("name", key.name),
                "expiration_date": key.expiration_date,
            }

            if "expiration" in body:
                expiration_date = body["expiration"]
                if expiration_date is not None and expiration_date != "":
                    try:
                        expiration_date = datetime.utcfromtimestamp(float(expiration_date))
                    except ValueError as ve:
                        raise InvalidRequest("Invalid expiration date: %s" % ve)

                    if expiration_date <= datetime.now():
                        raise InvalidRequest("Cannot have an expiration date in the past")

                key_log_metadata.update(
                    {
                        "old_expiration_date": key.expiration_date,
                        "expiration_date": expiration_date,
                    }
                )

                log_action("service_key_extend", None, key_log_metadata)
                pre_oci_model.set_key_expiration(kid, expiration_date)

            if "name" in body or "metadata" in body:
                key_name = body.get("name")
                if not validate_service_key_name(key_name):
                    raise InvalidRequest("Invalid service key friendly name: %s" % key_name)

                pre_oci_model.update_service_key(kid, key_name, body.get("metadata"))
                log_action("service_key_modify", None, key_log_metadata)

            updated_key = pre_oci_model.get_service_key(kid, approved_only=False, alive_only=False)
            return jsonify(updated_key.to_dict())

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("deleteServiceKey")
    @require_scope(scopes.SUPERUSER)
    def delete(self, kid):
        if SuperUserPermission().can():
            try:
                key = pre_oci_model.delete_service_key(kid)
            except ServiceKeyDoesNotExist:
                raise NotFound()

            key_log_metadata = {
                "kid": kid,
                "service": key.service,
                "name": key.name,
                "created_date": key.created_date,
                "expiration_date": key.expiration_date,
            }

            log_action("service_key_delete", None, key_log_metadata)
            return make_response("", 204)

        raise Unauthorized()


@resource("/v1/superuser/approvedkeys/<kid>")
@path_param("kid", "The unique identifier for a service key")
@show_if(features.SUPER_USERS)
class SuperUserServiceKeyApproval(ApiResource):
    """
    Resource for approving service keys.
    """

    schemas = {
        "ApproveServiceKey": {
            "id": "ApproveServiceKey",
            "type": "object",
            "description": "Information for approving service keys",
            "properties": {
                "notes": {
                    "type": "string",
                    "description": "Optional approval notes",
                },
            },
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname("approveServiceKey")
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("ApproveServiceKey")
    def post(self, kid):
        if SuperUserPermission().can():
            notes = request.get_json().get("notes", "")
            approver = get_authenticated_user()
            try:
                key = pre_oci_model.approve_service_key(
                    kid, approver, ServiceKeyApprovalType.SUPERUSER, notes=notes
                )

                # Log the approval of the service key.
                key_log_metadata = {
                    "kid": kid,
                    "service": key.service,
                    "name": key.name,
                    "expiration_date": key.expiration_date,
                }

                log_action("service_key_approve", None, key_log_metadata)
            except ServiceKeyDoesNotExist:
                raise NotFound()
            except ServiceKeyAlreadyApproved:
                pass

            return make_response("", 201)

        raise Unauthorized()


@resource("/v1/superuser/<build_uuid>/logs")
@path_param("build_uuid", "The UUID of the build")
@show_if(features.SUPER_USERS)
class SuperUserRepositoryBuildLogs(ApiResource):
    """
    Resource for loading repository build logs for the superuser.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("getRepoBuildLogsSuperUser")
    @require_scope(scopes.SUPERUSER)
    def get(self, build_uuid):
        """
        Return the build logs for the build specified by the build uuid.
        """
        if SuperUserPermission().can():
            try:
                repo_build = pre_oci_model.get_repository_build(build_uuid)
                return get_logs_or_log_url(repo_build)
            except InvalidRepositoryBuildException as e:
                raise InvalidResponse(str(e))

        raise Unauthorized()


@resource("/v1/superuser/<build_uuid>/status")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("build_uuid", "The UUID of the build")
@show_if(features.SUPER_USERS)
class SuperUserRepositoryBuildStatus(ApiResource):
    """
    Resource for dealing with repository build status.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("getRepoBuildStatusSuperUser")
    @require_scope(scopes.SUPERUSER)
    def get(self, build_uuid):
        """
        Return the status for the builds specified by the build uuids.
        """
        if SuperUserPermission().can():
            try:
                build = pre_oci_model.get_repository_build(build_uuid)
            except InvalidRepositoryBuildException as e:
                raise InvalidResponse(str(e))
            return build.to_dict()

        raise Unauthorized()


@resource("/v1/superuser/<build_uuid>/build")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("build_uuid", "The UUID of the build")
@show_if(features.SUPER_USERS)
class SuperUserRepositoryBuildResource(ApiResource):
    """
    Resource for dealing with repository builds as a super user.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("getRepoBuildSuperUser")
    @require_scope(scopes.SUPERUSER)
    def get(self, build_uuid):
        """
        Returns information about a build.
        """
        if SuperUserPermission().can():
            try:
                build = pre_oci_model.get_repository_build(build_uuid)
            except InvalidRepositoryBuildException:
                raise NotFound()

            return build.to_dict()

        raise Unauthorized()
