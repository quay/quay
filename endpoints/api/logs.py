"""
Access usage logs for organizations or repositories.
"""
from datetime import datetime, timedelta

from flask import abort, request

import features

from app import app, export_action_logs_queue, avatar
from auth.permissions import AdministerOrganizationPermission
from auth.auth_context import get_authenticated_user
from auth import scopes
from data.logs_model import logs_model
from data.registry_model import registry_model
from endpoints.api import (
    resource,
    nickname,
    ApiResource,
    query_param,
    parse_args,
    RepositoryParamResource,
    require_repo_admin,
    related_user_resource,
    format_date,
    require_user_admin,
    path_param,
    require_scope,
    page_support,
    validate_json_request,
    InvalidRequest,
    show_if,
)
from endpoints.exception import Unauthorized, NotFound


LOGS_PER_PAGE = 20
SERVICE_LEVEL_LOG_KINDS = set(
    [
        "service_key_create",
        "service_key_approve",
        "service_key_delete",
        "service_key_modify",
        "service_key_extend",
        "service_key_rotate",
    ]
)


def _parse_datetime(dt_string):
    if not dt_string:
        return None

    try:
        return datetime.strptime(dt_string + " UTC", "%m/%d/%Y %Z")
    except ValueError:
        return None


def _validate_logs_arguments(start_time, end_time):
    start_time = _parse_datetime(start_time) or (datetime.today() - timedelta(days=1))
    end_time = _parse_datetime(end_time) or datetime.today()
    end_time = end_time + timedelta(days=1)
    return start_time, end_time


def _get_logs(
    start_time,
    end_time,
    performer_name=None,
    repository_name=None,
    namespace_name=None,
    page_token=None,
    filter_kinds=None,
):
    (start_time, end_time) = _validate_logs_arguments(start_time, end_time)
    if end_time < start_time:
        abort(400)
    log_entry_page = logs_model.lookup_logs(
        start_time,
        end_time,
        performer_name,
        repository_name,
        namespace_name,
        filter_kinds,
        page_token,
        app.config["ACTION_LOG_MAX_PAGE"],
    )
    include_namespace = namespace_name is None and repository_name is None
    return (
        {
            "start_time": format_date(start_time),
            "end_time": format_date(end_time),
            "logs": [log.to_dict(avatar, include_namespace) for log in log_entry_page.logs],
        },
        log_entry_page.next_page_token,
    )


def _get_aggregate_logs(
    start_time, end_time, performer_name=None, repository=None, namespace=None, filter_kinds=None
):
    (start_time, end_time) = _validate_logs_arguments(start_time, end_time)
    if end_time < start_time:
        abort(400)
    aggregated_logs = logs_model.get_aggregated_log_counts(
        start_time,
        end_time,
        performer_name=performer_name,
        repository_name=repository,
        namespace_name=namespace,
        filter_kinds=filter_kinds,
    )

    return {"aggregated": [log.to_dict() for log in aggregated_logs]}


@resource("/v1/repository/<apirepopath:repository>/logs")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryLogs(RepositoryParamResource):
    """
    Resource for fetching logs for the specific repository.
    """

    @require_repo_admin
    @nickname("listRepoLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @page_support()
    def get(self, namespace, repository, page_token, parsed_args):
        """
        List the logs for the specified repository.
        """
        if registry_model.lookup_repository(namespace, repository) is None:
            raise NotFound()

        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]
        return _get_logs(
            start_time,
            end_time,
            repository_name=repository,
            page_token=page_token,
            namespace_name=namespace,
        )


@resource("/v1/user/logs")
class UserLogs(ApiResource):
    """
    Resource for fetching logs for the current user.
    """

    @require_user_admin
    @nickname("listUserLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("performer", "Username for which to filter logs.", type=str)
    @page_support()
    def get(self, parsed_args, page_token):
        """
        List the logs for the current user.
        """
        performer_name = parsed_args["performer"]
        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]

        user = get_authenticated_user()
        return _get_logs(
            start_time,
            end_time,
            performer_name=performer_name,
            namespace_name=user.username,
            page_token=page_token,
            filter_kinds=SERVICE_LEVEL_LOG_KINDS,
        )


@resource("/v1/organization/<orgname>/logs")
@path_param("orgname", "The name of the organization")
@related_user_resource(UserLogs)
class OrgLogs(ApiResource):
    """
    Resource for fetching logs for the entire organization.
    """

    @nickname("listOrgLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("performer", "Username for which to filter logs.", type=str)
    @page_support()
    @require_scope(scopes.ORG_ADMIN)
    def get(self, orgname, page_token, parsed_args):
        """
        List the logs for the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            performer_name = parsed_args["performer"]
            start_time = parsed_args["starttime"]
            end_time = parsed_args["endtime"]

            return _get_logs(
                start_time,
                end_time,
                namespace_name=orgname,
                performer_name=performer_name,
                page_token=page_token,
            )

        raise Unauthorized()


@resource("/v1/repository/<apirepopath:repository>/aggregatelogs")
@show_if(features.AGGREGATED_LOG_COUNT_RETRIEVAL)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryAggregateLogs(RepositoryParamResource):
    """
    Resource for fetching aggregated logs for the specific repository.
    """

    @require_repo_admin
    @nickname("getAggregateRepoLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    def get(self, namespace, repository, parsed_args):
        """
        Returns the aggregated logs for the specified repository.
        """
        if registry_model.lookup_repository(namespace, repository) is None:
            raise NotFound()

        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]
        return _get_aggregate_logs(start_time, end_time, repository=repository, namespace=namespace)


@resource("/v1/user/aggregatelogs")
@show_if(features.AGGREGATED_LOG_COUNT_RETRIEVAL)
class UserAggregateLogs(ApiResource):
    """
    Resource for fetching aggregated logs for the current user.
    """

    @require_user_admin
    @nickname("getAggregateUserLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("performer", "Username for which to filter logs.", type=str)
    def get(self, parsed_args):
        """
        Returns the aggregated logs for the current user.
        """
        performer_name = parsed_args["performer"]
        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]

        user = get_authenticated_user()
        return _get_aggregate_logs(
            start_time,
            end_time,
            performer_name=performer_name,
            namespace=user.username,
            filter_kinds=SERVICE_LEVEL_LOG_KINDS,
        )


@resource("/v1/organization/<orgname>/aggregatelogs")
@show_if(features.AGGREGATED_LOG_COUNT_RETRIEVAL)
@path_param("orgname", "The name of the organization")
@related_user_resource(UserLogs)
class OrgAggregateLogs(ApiResource):
    """
    Resource for fetching aggregate logs for the entire organization.
    """

    @nickname("getAggregateOrgLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("performer", "Username for which to filter logs.", type=str)
    @require_scope(scopes.ORG_ADMIN)
    def get(self, orgname, parsed_args):
        """
        Gets the aggregated logs for the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            performer_name = parsed_args["performer"]
            start_time = parsed_args["starttime"]
            end_time = parsed_args["endtime"]

            return _get_aggregate_logs(
                start_time, end_time, namespace=orgname, performer_name=performer_name
            )

        raise Unauthorized()


EXPORT_LOGS_SCHEMA = {
    "type": "object",
    "description": "Configuration for an export logs operation",
    "properties": {
        "callback_url": {
            "type": "string",
            "description": "The callback URL to invoke with a link to the exported logs",
        },
        "callback_email": {
            "type": "string",
            "description": "The e-mail address at which to e-mail a link to the exported logs",
        },
    },
}


def _queue_logs_export(start_time, end_time, options, namespace_name, repository_name=None):
    callback_url = options.get("callback_url")
    if callback_url:
        if not callback_url.startswith("https://") and not callback_url.startswith("http://"):
            raise InvalidRequest("Invalid callback URL")

    callback_email = options.get("callback_email")
    if callback_email:
        if callback_email.find("@") < 0:
            raise InvalidRequest("Invalid callback e-mail")

    (start_time, end_time) = _validate_logs_arguments(start_time, end_time)
    if end_time < start_time:
        abort(400)
    export_id = logs_model.queue_logs_export(
        start_time,
        end_time,
        export_action_logs_queue,
        namespace_name,
        repository_name,
        callback_url,
        callback_email,
    )
    if export_id is None:
        raise InvalidRequest("Invalid export request")

    return export_id


@resource("/v1/repository/<apirepopath:repository>/exportlogs")
@show_if(features.LOG_EXPORT)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class ExportRepositoryLogs(RepositoryParamResource):
    """
    Resource for exporting the logs for the specific repository.
    """

    schemas = {"ExportLogs": EXPORT_LOGS_SCHEMA}

    @require_repo_admin
    @nickname("exportRepoLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @validate_json_request("ExportLogs")
    def post(self, namespace, repository, parsed_args):
        """
        Queues an export of the logs for the specified repository.
        """
        if registry_model.lookup_repository(namespace, repository) is None:
            raise NotFound()

        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]
        export_id = _queue_logs_export(
            start_time, end_time, request.get_json(), namespace, repository_name=repository
        )
        return {
            "export_id": export_id,
        }


@resource("/v1/user/exportlogs")
@show_if(features.LOG_EXPORT)
class ExportUserLogs(ApiResource):
    """
    Resource for exporting the logs for the current user repository.
    """

    schemas = {"ExportLogs": EXPORT_LOGS_SCHEMA}

    @require_user_admin
    @nickname("exportUserLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @validate_json_request("ExportLogs")
    def post(self, parsed_args):
        """
        Returns the aggregated logs for the current user.
        """
        start_time = parsed_args["starttime"]
        end_time = parsed_args["endtime"]

        user = get_authenticated_user()
        export_id = _queue_logs_export(start_time, end_time, request.get_json(), user.username)
        return {
            "export_id": export_id,
        }


@resource("/v1/organization/<orgname>/exportlogs")
@show_if(features.LOG_EXPORT)
@path_param("orgname", "The name of the organization")
@related_user_resource(ExportUserLogs)
class ExportOrgLogs(ApiResource):
    """
    Resource for exporting the logs for an entire organization.
    """

    schemas = {"ExportLogs": EXPORT_LOGS_SCHEMA}

    @nickname("exportOrgLogs")
    @parse_args()
    @query_param("starttime", 'Earliest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @query_param("endtime", 'Latest time for logs. Format: "%m/%d/%Y" in UTC.', type=str)
    @require_scope(scopes.ORG_ADMIN)
    @validate_json_request("ExportLogs")
    def post(self, orgname, parsed_args):
        """
        Exports the logs for the specified organization.
        """
        permission = AdministerOrganizationPermission(orgname)
        if permission.can():
            start_time = parsed_args["starttime"]
            end_time = parsed_args["endtime"]

            export_id = _queue_logs_export(start_time, end_time, request.get_json(), orgname)
            return {
                "export_id": export_id,
            }

        raise Unauthorized()
