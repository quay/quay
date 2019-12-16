import logging
import datetime

from calendar import timegm
from email.utils import formatdate
from functools import partial, wraps

from flask import Blueprint, request, session
from flask_restful import Resource, abort, Api, reqparse
from flask_restful.utils import unpack
from flask_restful.utils.cors import crossdomain
from jsonschema import validate, ValidationError

from app import app, authentication
from auth.permissions import (
    ReadRepositoryPermission,
    ModifyRepositoryPermission,
    AdministerRepositoryPermission,
    UserReadPermission,
    UserAdminPermission,
)
from auth import scopes
from auth.auth_context import (
    get_authenticated_context,
    get_authenticated_user,
    get_validated_oauth_token,
)
from auth.decorators import process_oauth
from data import model as data_model
from data.logs_model import logs_model
from data.database import RepositoryState
from endpoints.csrf import csrf_protect
from endpoints.exception import (
    Unauthorized,
    InvalidRequest,
    InvalidResponse,
    FreshLoginRequired,
    NotFound,
)
from endpoints.decorators import check_anon_protection, require_xhr_from_browser, check_readonly
from util.metrics.prometheus import timed_blueprint
from util.names import parse_namespace_repository
from util.pagination import encrypt_page_token, decrypt_page_token
from util.request import get_request_ip
from util.timedeltastring import convert_to_timedelta

from .__init__models_pre_oci import pre_oci_model as model


logger = logging.getLogger(__name__)
api_bp = timed_blueprint(Blueprint("api", __name__))


CROSS_DOMAIN_HEADERS = ["Authorization", "Content-Type", "X-Requested-With"]
FRESH_LOGIN_TIMEOUT = convert_to_timedelta(app.config.get("FRESH_LOGIN_TIMEOUT", "10m"))


class ApiExceptionHandlingApi(Api):
    @crossdomain(origin="*", headers=CROSS_DOMAIN_HEADERS)
    def handle_error(self, error):
        return super(ApiExceptionHandlingApi, self).handle_error(error)


api = ApiExceptionHandlingApi()
api.init_app(api_bp)
api.decorators = [
    csrf_protect(),
    crossdomain(origin="*", headers=CROSS_DOMAIN_HEADERS),
    process_oauth,
    require_xhr_from_browser,
]


def resource(*urls, **kwargs):
    def wrapper(api_resource):
        if not api_resource:
            return None

        api_resource.registered = True
        api.add_resource(api_resource, *urls, **kwargs)
        return api_resource

    return wrapper


def show_if(value):
    def f(inner):
        if hasattr(inner, "registered") and inner.registered:
            msg = (
                "API endpoint %s is already registered; please switch the "
                + "@show_if to be *below* the @resource decorator"
            )
            raise Exception(msg % inner)

        if not value:
            return None

        return inner

    return f


def hide_if(value):
    def f(inner):
        if hasattr(inner, "registered") and inner.registered:
            msg = (
                "API endpoint %s is already registered; please switch the "
                + "@hide_if to be *below* the @resource decorator"
            )
            raise Exception(msg % inner)

        if value:
            return None

        return inner

    return f


def format_date(date):
    """
    Output an RFC822 date format.
    """
    if date is None:
        return None
    return formatdate(timegm(date.utctimetuple()))


def add_method_metadata(name, value):
    def modifier(func):
        if func is None:
            return None

        if "__api_metadata" not in dir(func):
            func.__api_metadata = {}
        func.__api_metadata[name] = value
        return func

    return modifier


def method_metadata(func, name):
    if func is None:
        return None

    if "__api_metadata" in dir(func):
        return func.__api_metadata.get(name, None)
    return None


nickname = partial(add_method_metadata, "nickname")
related_user_resource = partial(add_method_metadata, "related_user_resource")
internal_only = add_method_metadata("internal", True)


def path_param(name, description):
    def add_param(func):
        if not func:
            return func

        if "__api_path_params" not in dir(func):
            func.__api_path_params = {}
        func.__api_path_params[name] = {"name": name, "description": description}
        return func

    return add_param


def query_param(name, help_str, type=reqparse.text_type, default=None, choices=(), required=False):
    def add_param(func):
        if "__api_query_params" not in dir(func):
            func.__api_query_params = []
        func.__api_query_params.append(
            {
                "name": name,
                "type": type,
                "help": help_str,
                "default": default,
                "choices": choices,
                "required": required,
                "location": ("args"),
            }
        )
        return func

    return add_param


def page_support(page_token_kwarg="page_token", parsed_args_kwarg="parsed_args"):
    def inner(func):
        """
        Adds pagination support to an API endpoint.

        The decorated API will have an added query parameter named 'next_page'. Works in tandem with
        the modelutil paginate method.
        """

        @wraps(func)
        @query_param("next_page", "The page token for the next page", type=str)
        def wrapper(self, *args, **kwargs):
            # Note: if page_token is None, we'll receive the first page of results back.
            page_token = decrypt_page_token(kwargs[parsed_args_kwarg]["next_page"])
            kwargs[page_token_kwarg] = page_token

            (result, next_page_token) = func(self, *args, **kwargs)
            if next_page_token is not None:
                result["next_page"] = encrypt_page_token(next_page_token)

            return result

        return wrapper

    return inner


def parse_args(kwarg_name="parsed_args"):
    def inner(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if "__api_query_params" not in dir(func):
                abort(500)

            parser = reqparse.RequestParser()
            for arg_spec in func.__api_query_params:
                parser.add_argument(**arg_spec)
            kwargs[kwarg_name] = parser.parse_args()

            return func(self, *args, **kwargs)

        return wrapper

    return inner


def parse_repository_name(func):
    @wraps(func)
    def wrapper(repository, *args, **kwargs):
        (namespace, repository) = parse_namespace_repository(
            repository, app.config["LIBRARY_NAMESPACE"]
        )
        return func(namespace, repository, *args, **kwargs)

    return wrapper


class ApiResource(Resource):
    registered = False
    method_decorators = [check_anon_protection, check_readonly]

    def options(self):
        return None, 200


class RepositoryParamResource(ApiResource):
    method_decorators = [check_anon_protection, parse_repository_name, check_readonly]


def disallow_for_app_repositories(func):
    @wraps(func)
    def wrapped(self, namespace_name, repository_name, *args, **kwargs):
        # Lookup the repository with the given namespace and name and ensure it is not an application
        # repository.
        if model.is_app_repository(namespace_name, repository_name):
            abort(501)

        return func(self, namespace_name, repository_name, *args, **kwargs)

    return wrapped


def disallow_for_non_normal_repositories(func):
    @wraps(func)
    def wrapped(self, namespace_name, repository_name, *args, **kwargs):
        repo = data_model.repository.get_repository(namespace_name, repository_name)
        if repo and repo.state != RepositoryState.NORMAL:
            abort(503, message="Repository is in read only or mirror mode: %s" % repo.state)

        return func(self, namespace_name, repository_name, *args, **kwargs)

    return wrapped


def require_repo_permission(permission_class, scope, allow_public=False):
    def wrapper(func):
        @add_method_metadata("oauth2_scope", scope)
        @wraps(func)
        def wrapped(self, namespace, repository, *args, **kwargs):
            logger.debug(
                "Checking permission %s for repo: %s/%s", permission_class, namespace, repository
            )
            permission = permission_class(namespace, repository)
            if permission.can() or (
                allow_public and model.repository_is_public(namespace, repository)
            ):
                return func(self, namespace, repository, *args, **kwargs)
            raise Unauthorized()

        return wrapped

    return wrapper


require_repo_read = require_repo_permission(ReadRepositoryPermission, scopes.READ_REPO, True)
require_repo_write = require_repo_permission(ModifyRepositoryPermission, scopes.WRITE_REPO)
require_repo_admin = require_repo_permission(AdministerRepositoryPermission, scopes.ADMIN_REPO)


def require_user_permission(permission_class, scope=None):
    def wrapper(func):
        @add_method_metadata("oauth2_scope", scope)
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            user = get_authenticated_user()
            if not user:
                raise Unauthorized()

            logger.debug("Checking permission %s for user %s", permission_class, user.username)
            permission = permission_class(user.username)
            if permission.can():
                return func(self, *args, **kwargs)
            raise Unauthorized()

        return wrapped

    return wrapper


require_user_read = require_user_permission(UserReadPermission, scopes.READ_USER)
require_user_admin = require_user_permission(UserAdminPermission, scopes.ADMIN_USER)


def verify_not_prod(func):
    @add_method_metadata("enterprise_only", True)
    @wraps(func)
    def wrapped(*args, **kwargs):
        # Verify that we are not running on a production (i.e. hosted) stack. If so, we fail.
        # This should never happen (because of the feature-flag on SUPER_USERS), but we want to be
        # absolutely sure.
        if app.config["SERVER_HOSTNAME"].find("quay.io") >= 0:
            logger.error("!!! Super user method called IN PRODUCTION !!!")
            raise NotFound()

        return func(*args, **kwargs)

    return wrapped


def require_fresh_login(func):
    @add_method_metadata("requires_fresh_login", True)
    @wraps(func)
    def wrapped(*args, **kwargs):
        user = get_authenticated_user()
        if not user or user.robot:
            raise Unauthorized()

        if get_validated_oauth_token():
            return func(*args, **kwargs)

        last_login = session.get("login_time", datetime.datetime.min)
        valid_span = datetime.datetime.now() - FRESH_LOGIN_TIMEOUT
        logger.debug(
            "Checking fresh login for user %s: Last login at %s", user.username, last_login
        )

        if (
            last_login >= valid_span
            or not authentication.supports_fresh_login
            or not authentication.has_password_set(user.username)
        ):
            return func(*args, **kwargs)

        raise FreshLoginRequired()

    return wrapped


def require_scope(scope_object):
    def wrapper(func):
        @add_method_metadata("oauth2_scope", scope_object)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return wrapper


def max_json_size(max_size):
    def wrapper(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            if request.is_json and len(request.get_data()) > max_size:
                raise InvalidRequest()

            return func(self, *args, **kwargs)

        return wrapped

    return wrapper


def validate_json_request(schema_name, optional=False):
    def wrapper(func):
        @add_method_metadata("request_schema", schema_name)
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            schema = self.schemas[schema_name]
            try:
                json_data = request.get_json()
                if json_data is None:
                    if not optional:
                        raise InvalidRequest("Missing JSON body")
                else:
                    validate(json_data, schema)
                return func(self, *args, **kwargs)
            except ValidationError as ex:
                raise InvalidRequest(str(ex))

        return wrapped

    return wrapper


def request_error(exception=None, **kwargs):
    data = kwargs.copy()
    message = "Request error."
    if exception:
        message = str(exception)

    message = data.pop("message", message)
    raise InvalidRequest(message, data)


def log_action(kind, user_or_orgname, metadata=None, repo=None, repo_name=None):
    if not metadata:
        metadata = {}

    oauth_token = get_validated_oauth_token()
    if oauth_token:
        metadata["oauth_token_id"] = oauth_token.id
        metadata["oauth_token_application_id"] = oauth_token.application.client_id
        metadata["oauth_token_application"] = oauth_token.application.name

    performer = get_authenticated_user()

    if repo_name is not None:
        repo = data_model.repository.get_repository(user_or_orgname, repo_name)

    logs_model.log_action(
        kind,
        user_or_orgname,
        repository=repo,
        performer=performer,
        ip=get_request_ip(),
        metadata=metadata,
    )


def define_json_response(schema_name):
    def wrapper(func):
        @add_method_metadata("response_schema", schema_name)
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            schema = self.schemas[schema_name]
            resp = func(self, *args, **kwargs)

            if app.config["TESTING"]:
                try:
                    validate(resp, schema)
                except ValidationError as ex:
                    raise InvalidResponse(str(ex))

            return resp

        return wrapped

    return wrapper


def deprecated():
    """
    Marks a given API resource operation as deprecated by adding `Deprecation` header.
    See https://tools.ietf.org/id/draft-dalal-deprecation-header-01.html#RFC7234.
    """

    def wrapper(func):
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            (data, code, headers) = unpack(func(self, *args, **kwargs))
            headers["Deprecation"] = "true"

            return (data, code, headers)

        return wrapped

    return wrapper


import endpoints.api.appspecifictokens
import endpoints.api.billing
import endpoints.api.build
import endpoints.api.discovery
import endpoints.api.error
import endpoints.api.globalmessages
import endpoints.api.image
import endpoints.api.logs
import endpoints.api.manifest
import endpoints.api.organization
import endpoints.api.permission
import endpoints.api.prototype
import endpoints.api.repository
import endpoints.api.repositorynotification
import endpoints.api.repoemail
import endpoints.api.repotoken
import endpoints.api.robot
import endpoints.api.search
import endpoints.api.suconfig
import endpoints.api.superuser
import endpoints.api.tag
import endpoints.api.team
import endpoints.api.trigger
import endpoints.api.user
import endpoints.api.secscan
import endpoints.api.signing
import endpoints.api.mirror
