# TODO to extract the discovery stuff into a util at the top level and then use it both here and config_app discovery.py
"""
API discovery information.
"""

import re
import logging
import sys

from collections import OrderedDict

from flask_restful import reqparse

from app import app
from auth import scopes
from endpoints.api import (
    ApiResource,
    resource,
    method_metadata,
    nickname,
    parse_args,
    query_param,
)
from endpoints.decorators import anon_allowed
from util.parsing import truthy_bool


logger = logging.getLogger(__name__)


PARAM_REGEX = re.compile(r"<([^:>]+:)*([\w]+)>")


TYPE_CONVERTER = {
    truthy_bool: "boolean",
    str: "string",
    reqparse.text_type: "string",
    int: "integer",
}

PREFERRED_URL_SCHEME = app.config["PREFERRED_URL_SCHEME"]
SERVER_HOSTNAME = app.config["SERVER_HOSTNAME"]


def fully_qualified_name(method_view_class):
    return "%s.%s" % (method_view_class.__module__, method_view_class.__name__)


def swagger_route_data(include_internal=False, compact=False):
    def swagger_parameter(
        name, description, kind="path", param_type="string", required=True, enum=None, schema=None
    ):
        # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#parameterObject
        parameter_info = {"name": name, "in": kind, "required": required}

        if not compact:
            parameter_info["description"] = description or ""

        if schema:
            parameter_info["schema"] = {"$ref": "#/definitions/%s" % schema}
        else:
            parameter_info["type"] = param_type

        if enum is not None and len(list(enum)) > 0:
            parameter_info["enum"] = list(enum)

        return parameter_info

    paths = {}
    models = {}
    tags = []
    tags_added = set()
    operationIds = set()

    for rule in app.url_map.iter_rules():
        endpoint_method = app.view_functions[rule.endpoint]

        # Verify that we have a view class for this API method.
        if not "view_class" in dir(endpoint_method):
            continue

        view_class = endpoint_method.view_class

        # Hide the class if it is internal.
        internal = method_metadata(view_class, "internal")
        if not include_internal and internal:
            continue

        # Build the tag.
        parts = fully_qualified_name(view_class).split(".")
        tag_name = parts[-2]
        if not tag_name in tags_added:
            tags_added.add(tag_name)
            tags.append(
                {
                    "name": tag_name,
                    "description": (sys.modules[view_class.__module__].__doc__ or "").strip(),
                }
            )

        # Build the Swagger data for the path.
        swagger_path = PARAM_REGEX.sub(r"{\2}", rule.rule)
        full_name = fully_qualified_name(view_class)
        path_swagger = {"x-name": full_name, "x-path": swagger_path, "x-tag": tag_name}

        if include_internal:
            related_user_res = method_metadata(view_class, "related_user_resource")
            if related_user_res is not None:
                path_swagger["x-user-related"] = fully_qualified_name(related_user_res)

        paths[swagger_path] = path_swagger

        # Add any global path parameters.
        param_data_map = (
            view_class.__api_path_params if "__api_path_params" in dir(view_class) else {}
        )
        if param_data_map:
            path_parameters_swagger = []
            for path_parameter in param_data_map:
                description = param_data_map[path_parameter].get("description")
                path_parameters_swagger.append(swagger_parameter(path_parameter, description))

            path_swagger["parameters"] = path_parameters_swagger

        # Add the individual HTTP operations.
        method_names = list(rule.methods.difference(["HEAD", "OPTIONS"]))
        for method_name in method_names:
            # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object
            method = getattr(view_class, method_name.lower(), None)
            if method is None:
                logger.debug("Unable to find method for %s in class %s", method_name, view_class)
                continue

            operationId = method_metadata(method, "nickname")
            operation_swagger = {
                "operationId": operationId,
                "parameters": [],
            }

            if operationId is None:
                continue

            if operationId in operationIds:
                raise Exception("Duplicate operation Id: %s" % operationId)

            operationIds.add(operationId)

            if not compact:
                operation_swagger.update(
                    {
                        "description": method.__doc__.strip() if method.__doc__ else "",
                        "tags": [tag_name],
                    }
                )

            # Mark the method as internal.
            internal = method_metadata(method, "internal")
            if internal is not None:
                operation_swagger["x-internal"] = True

            if include_internal:
                requires_fresh_login = method_metadata(method, "requires_fresh_login")
                if requires_fresh_login is not None:
                    operation_swagger["x-requires-fresh-login"] = True

            # Add the path parameters.
            if rule.arguments:
                for path_parameter in rule.arguments:
                    description = param_data_map.get(path_parameter, {}).get("description")
                    operation_swagger["parameters"].append(
                        swagger_parameter(path_parameter, description)
                    )

            # Add the query parameters.
            if "__api_query_params" in dir(method):
                for query_parameter_info in method.__api_query_params:
                    name = query_parameter_info["name"]
                    description = query_parameter_info["help"]
                    param_type = TYPE_CONVERTER[query_parameter_info["type"]]
                    required = query_parameter_info["required"]

                    operation_swagger["parameters"].append(
                        swagger_parameter(
                            name,
                            description,
                            kind="query",
                            param_type=param_type,
                            required=required,
                            enum=query_parameter_info["choices"],
                        )
                    )

            # Add the OAuth security block.
            # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#securityRequirementObject
            scope = method_metadata(method, "oauth2_scope")
            if scope and not compact:
                operation_swagger["security"] = [{"oauth2_implicit": [scope.scope]}]

            # Add the responses block.
            # https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#responsesObject
            response_schema_name = method_metadata(method, "response_schema")
            if not compact:
                if response_schema_name:
                    models[response_schema_name] = view_class.schemas[response_schema_name]

                models["ApiError"] = {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "integer",
                            "description": "Status code of the response.",
                        },
                        "type": {
                            "type": "string",
                            "description": "Reference to the type of the error.",
                        },
                        "detail": {
                            "type": "string",
                            "description": "Details about the specific instance of the error.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Unique error code to identify the type of error.",
                        },
                        "error_message": {
                            "type": "string",
                            "description": "Deprecated; alias for detail",
                        },
                        "error_type": {
                            "type": "string",
                            "description": "Deprecated; alias for detail",
                        },
                    },
                    "required": [
                        "status",
                        "type",
                        "title",
                    ],
                }

                responses = {
                    "400": {
                        "description": "Bad Request",
                    },
                    "401": {
                        "description": "Session required",
                    },
                    "403": {
                        "description": "Unauthorized access",
                    },
                    "404": {
                        "description": "Not found",
                    },
                }

                for _, body in list(responses.items()):
                    body["schema"] = {"$ref": "#/definitions/ApiError"}

                if method_name == "DELETE":
                    responses["204"] = {"description": "Deleted"}
                elif method_name == "POST":
                    responses["201"] = {"description": "Successful creation"}
                else:
                    responses["200"] = {"description": "Successful invocation"}

                    if response_schema_name:
                        responses["200"]["schema"] = {
                            "$ref": "#/definitions/%s" % response_schema_name
                        }

                operation_swagger["responses"] = responses

            # Add the request block.
            request_schema_name = method_metadata(method, "request_schema")
            if request_schema_name and not compact:
                models[request_schema_name] = view_class.schemas[request_schema_name]

                operation_swagger["parameters"].append(
                    swagger_parameter(
                        "body", "Request body contents.", kind="body", schema=request_schema_name
                    )
                )

            # Add the operation to the parent path.
            if not internal or (internal and include_internal):
                path_swagger[method_name.lower()] = operation_swagger

    tags.sort(key=lambda t: t["name"])
    paths = OrderedDict(sorted(list(paths.items()), key=lambda p: p[1]["x-tag"]))

    if compact:
        return {"paths": paths}

    swagger_data = {
        "swagger": "2.0",
        "host": SERVER_HOSTNAME,
        "basePath": "/",
        "schemes": [PREFERRED_URL_SCHEME],
        "info": {
            "version": "v1",
            "title": "Quay Frontend",
            "description": (
                "This API allows you to perform many of the operations required to work "
                "with Quay repositories, users, and organizations. You can find out more "
                'at <a href="https://quay.io">Quay</a>.'
            ),
            "termsOfService": "https://quay.io/tos",
            "contact": {"email": "support@quay.io"},
        },
        "securityDefinitions": {
            "oauth2_implicit": {
                "type": "oauth2",
                "flow": "implicit",
                "authorizationUrl": "%s://%s/oauth/authorize"
                % (PREFERRED_URL_SCHEME, SERVER_HOSTNAME),
                "scopes": {
                    scope.scope: scope.description
                    for scope in list(scopes.app_scopes(app.config).values())
                },
            },
        },
        "paths": paths,
        "definitions": models,
        "tags": tags,
    }

    return swagger_data


@resource("/v1/discovery")
class DiscoveryResource(ApiResource):
    """
    Ability to inspect the API for usage information and documentation.
    """

    @parse_args()
    @query_param("internal", "Whether to include internal APIs.", type=truthy_bool, default=False)
    @nickname("discovery")
    @anon_allowed
    def get(self, parsed_args):
        """
        List all of the API endpoints available in the swagger API format.
        """
        return swagger_route_data(parsed_args["internal"])
