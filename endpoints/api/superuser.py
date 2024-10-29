"""
Superuser API.
"""

import logging
import os
import socket
import string
from datetime import datetime
from random import SystemRandom

import bitmath
from cryptography.hazmat.primitives import serialization
from flask import jsonify, make_response, request

import features
from _init import ROOT_DIR
from app import app, authentication, avatar, config_provider, usermanager
from auth import scopes
from auth.auth_context import get_authenticated_user
from auth.permissions import SuperUserPermission
from data.database import ServiceKeyApprovalType
from data.logs_model import logs_model
from data.model import DataModelException, InvalidNamespaceQuota, namespacequota, user
from data.model.quota import get_registry_size, queue_registry_size_calculation
from endpoints.api import (
    ApiResource,
    InvalidRequest,
    InvalidResponse,
    NotFound,
    Unauthorized,
    allow_if_global_readonly_superuser,
    format_date,
    internal_only,
    log_action,
    nickname,
    page_support,
    parse_args,
    path_param,
    query_param,
    request_error,
    require_fresh_login,
    require_scope,
    resource,
    show_if,
    validate_json_request,
    verify_not_prod,
)
from endpoints.api.build import get_logs_or_log_url
from endpoints.api.logs import _validate_logs_arguments
from endpoints.api.namespacequota import get_quota, limit_view, quota_view
from endpoints.api.superuser_models_pre_oci import (
    InvalidRepositoryBuildException,
    ServiceKeyAlreadyApproved,
    ServiceKeyDoesNotExist,
    pre_oci_model,
)
from util.parsing import truthy_bool
from util.request import get_request_ip
from util.useremails import send_confirmation_email, send_recovery_email
from util.validation import validate_service_key_name

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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
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
        "super_user": usermanager.is_superuser(user.username),
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
    @parse_args()
    @query_param(
        "limit",
        "Limit to the number of results to return per page. Max 100.",
        type=int,
        default=None,
    )
    @require_scope(scopes.SUPERUSER)
    @page_support()
    def get(self, parsed_args, page_token):
        """
        Returns a list of all organizations in the system.
        """
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
            if parsed_args["limit"] is not None and parsed_args["limit"] > 100:
                raise InvalidRequest("Page limit cannot be above 100")

            if parsed_args["limit"] is None:
                return {
                    "organizations": [org.to_dict() for org in pre_oci_model.get_organizations()]
                }, None
            else:
                orgs, next_page_token = pre_oci_model.get_organizations_paginated(
                    limit=parsed_args["limit"],
                    page_token=page_token,
                )
                return {"organizations": [org.to_dict() for org in orgs]}, next_page_token

        raise Unauthorized()


@resource("/v1/superuser/registrysize/")
@internal_only
@show_if(features.SUPER_USERS)
class SuperUserRegistrySize(ApiResource):
    """
    Resource for the current registry size.
    """

    @require_fresh_login
    @verify_not_prod
    @nickname("getRegistrySize")
    @require_scope(scopes.SUPERUSER)
    def get(self):
        """
        Returns size of the registry
        """
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
            registry_size = get_registry_size()
            if registry_size is not None:
                return {
                    "size_bytes": registry_size.size_bytes,
                    "last_ran": registry_size.completed_ms,
                    "queued": registry_size.queued,
                    "running": registry_size.running,
                }
            else:
                return {"size_bytes": 0, "last_ran": None, "running": False, "queued": False}

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname("queueRegistrySizeCalculation")
    @require_scope(scopes.SUPERUSER)
    def post(self):
        """
        Queues registry size calculation
        """
        if SuperUserPermission().can():
            queued, already_queued = queue_registry_size_calculation()
            if already_queued:
                return "", 202
            elif queued:
                return "", 201
            else:
                raise InvalidRequest("Could not queue registry size calculation")

        raise Unauthorized()


@resource(
    "/v1/superuser/users/<namespace>/quota",
    "/v1/superuser/organization/<namespace>/quota",
)
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT and features.EDIT_QUOTA)
class SuperUserUserQuotaList(ApiResource):

    schemas = {
        "NewNamespaceQuota": {
            "type": "object",
            "description": "Description of a new organization quota",
            "oneOf": [
                {
                    "required": ["limit_bytes"],
                    "properties": {
                        "limit_bytes": {
                            "type": "integer",
                            "description": "Number of bytes the organization is allowed",
                        },
                    },
                },
                {
                    "required": ["limit"],
                    "properties": {
                        "limit": {
                            "type": "string",
                            "description": "Human readable storage capacity of the organization",
                            "pattern": r"^(\d+\s?(B|KiB|MiB|GiB|TiB|PiB|EiB|ZiB|YiB|Ki|Mi|Gi|Ti|Pi|Ei|Zi|Yi|KB|MB|GB|TB|PB|EB|ZB|YB|K|M|G|T|P|E|Z|Y)?)$",
                        },
                    },
                },
            ],
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname(["listUserQuotaSuperUser", "listOrganizationQuotaSuperUser"])
    @require_scope(scopes.SUPERUSER)
    def get(self, namespace):
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():

            try:
                namespace_user = user.get_user_or_org(namespace)
            except DataModelException as ex:
                raise request_error(exception=ex)

            if not namespace_user:
                raise NotFound()

            quotas = namespacequota.get_namespace_quota_list(namespace_user.username)
            return [quota_view(quota) for quota in quotas]

        raise Unauthorized()

    @require_fresh_login
    @verify_not_prod
    @nickname(["createUserQuotaSuperUser", "createOrganizationQuotaSuperUser"])
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("NewNamespaceQuota")
    def post(self, namespace):
        if SuperUserPermission().can():
            quota_data = request.get_json()

            if "limit" in quota_data:
                try:
                    limit_bytes = bitmath.parse_string_unsafe(quota_data["limit"]).to_Byte().value
                except ValueError:
                    raise request_error(message="Invalid limit format")
            else:
                limit_bytes = quota_data["limit_bytes"]

            namespace_user = user.get_user_or_org(namespace)
            quotas = namespacequota.get_namespace_quota_list(namespace_user.username)

            if quotas:
                raise request_error(message="Quota for '%s' already exists" % namespace)

            try:
                newquota = namespacequota.create_namespace_quota(namespace_user, limit_bytes)
                return "Created", 201
            except DataModelException as ex:
                raise request_error(exception=ex)

        raise Unauthorized()


@resource(
    "/v1/superuser/users/<namespace>/quota/<quota_id>",
    "/v1/superuser/organization/<namespace>/quota/<quota_id>",
)
@show_if(features.SUPER_USERS)
@show_if(features.QUOTA_MANAGEMENT and features.EDIT_QUOTA)
class SuperUserUserQuota(ApiResource):

    schemas = {
        "UpdateNamespaceQuota": {
            "type": "object",
            "description": "Description of a new organization quota",
            "oneOf": [
                {
                    "properties": {
                        "limit_bytes": {
                            "type": "integer",
                            "description": "Number of bytes the organization is allowed",
                        },
                    },
                    "required": ["limit_bytes"],
                    "additionalProperties": False,
                },
                {
                    "properties": {
                        "limit": {
                            "type": "string",
                            "description": "Human readable storage capacity of the organization",
                            "pattern": r"^(\d+\s?(B|KiB|MiB|GiB|TiB|PiB|EiB|ZiB|YiB|Ki|Mi|Gi|Ti|Pi|Ei|Zi|Yi|KB|MB|GB|TB|PB|EB|ZB|YB|K|M|G|T|P|E|Z|Y)?)$",
                        },
                    },
                    "required": ["limit"],
                    "additionalProperties": False,
                },
                {
                    "properties": {
                        "limit_bytes": {"not": {}},
                        "limit": {"not": {}},
                    },
                    "additionalProperties": False,
                },
            ],
        },
    }

    @require_fresh_login
    @verify_not_prod
    @nickname(["changeUserQuotaSuperUser", "changeOrganizationQuotaSuperUser"])
    @require_scope(scopes.SUPERUSER)
    @validate_json_request("UpdateNamespaceQuota")
    def put(self, namespace, quota_id):
        if SuperUserPermission().can():
            quota_data = request.get_json()

            namespace_user = user.get_user_or_org(namespace)
            quota = get_quota(namespace_user.username, quota_id)

            try:
                limit_bytes = None

                if "limit" in quota_data:
                    try:
                        limit_bytes = (
                            bitmath.parse_string_unsafe(quota_data["limit"]).to_Byte().value
                        )
                    except ValueError:
                        raise request_error(message="Invalid limit format")
                elif "limit_bytes" in quota_data:
                    limit_bytes = quota_data["limit_bytes"]

                if limit_bytes:
                    namespacequota.update_namespace_quota_size(quota, limit_bytes)
            except DataModelException as ex:
                raise request_error(exception=ex)

            return quota_view(quota)

        raise Unauthorized()

    @nickname(["deleteUserQuotaSuperUser", "deleteOrganizationQuotaSuperUser"])
    @require_scope(scopes.SUPERUSER)
    def delete(self, namespace, quota_id):
        if SuperUserPermission().can():
            namespace_user = user.get_user_or_org(namespace)
            quota = get_quota(namespace_user.username, quota_id)
            namespacequota.delete_namespace_quota(quota)

            return "", 204

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
    @query_param(
        "limit",
        "Limit to the number of results to return per page. Max 100.",
        type=int,
        default=None,
    )
    @require_scope(scopes.SUPERUSER)
    @page_support()
    def get(self, parsed_args, page_token):
        """
        Returns a list of all users in the system.
        """
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
            if parsed_args["limit"] is not None and parsed_args["limit"] > 100:
                raise InvalidRequest("Page limit cannot be above 100")

            if parsed_args["limit"] is None:
                users = pre_oci_model.get_active_users(disabled=parsed_args["disabled"])
                return {"users": [user.to_dict() for user in users]}, None
            else:
                users, next_page_token = pre_oci_model.get_active_users_paginated(
                    disabled=parsed_args["disabled"],
                    limit=parsed_args["limit"],
                    page_token=page_token,
                )
                return {"users": [user.to_dict() for user in users]}, next_page_token

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

            authed_user = get_authenticated_user()

            log_action(
                "user_create",
                username,
                {"email": email, "username": username, "superuser": authed_user.username},
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

            if usermanager.is_superuser(username):
                raise InvalidRequest("Cannot send a recovery email for a superuser")

            code = pre_oci_model.create_reset_password_email_code(user.email)
            send_recovery_email(user.email, code)
            return {"email": user.email}

        raise Unauthorized()


@resource("/v1/superuser/users/<username>")
@path_param("username", "The username of the user being managed")
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

            if usermanager.is_superuser(username):
                raise InvalidRequest("Cannot delete a superuser")

            log_action("user_delete", username, {"username": username})

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

            if usermanager.is_superuser(username):
                raise InvalidRequest("Cannot update a superuser")

            authed_user = get_authenticated_user()

            user_data = request.get_json()
            if "password" in user_data:
                # Ensure that we are using database auth.
                if app.config["AUTHENTICATION_TYPE"] != "Database":
                    raise InvalidRequest("Cannot change password in non-database auth")

                log_action(
                    "user_change_password",
                    username,
                    {"username": username, "superuser": authed_user.username},
                )

                pre_oci_model.change_password(username, user_data["password"])

            if "email" in user_data:
                # Ensure that we are using database auth.
                if app.config["AUTHENTICATION_TYPE"] not in ["Database", "AppToken"]:
                    raise InvalidRequest("Cannot change e-mail in non-database auth")

                old_email = user.email
                new_email = user_data["email"]

                pre_oci_model.update_email(username, user_data["email"], auto_verify=True)

                log_action(
                    "user_change_email",
                    username,
                    {"old_email": old_email, "email": new_email, "superuser": authed_user.username},
                )

            if "enabled" in user_data:
                # Disable/enable the user.
                enabled = bool(user_data["enabled"])

                authed_user = get_authenticated_user()

                if enabled:
                    log_action(
                        "user_enable",
                        username,
                        {"username": username, "superuser": authed_user.username},
                    )
                else:
                    log_action(
                        "user_disable",
                        username,
                        {"username": username, "superuser": authed_user.username},
                    )

                pre_oci_model.update_enabled(username, enabled)

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
            if usermanager.is_superuser(namespace):
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
            new_name = org_data["name"] if "name" in org_data else None

            authed_user = get_authenticated_user()

            log_action(
                "org_change_name",
                name,
                {"old_name": name, "new_name": new_name, "superuser": authed_user.username},
            )

            org = pre_oci_model.change_organization_name(name, new_name)
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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
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

            public_pem = private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )

            return jsonify(
                {
                    "kid": key_id,
                    "name": key_name,
                    "service": body["service"],
                    "public_key": public_pem.decode("ascii"),
                    "private_key": private_pem.decode("ascii"),
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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
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
        if SuperUserPermission().can() or allow_if_global_readonly_superuser():
            try:
                build = pre_oci_model.get_repository_build(build_uuid)
            except InvalidRepositoryBuildException:
                raise NotFound()

            return build.to_dict()

        raise Unauthorized()
