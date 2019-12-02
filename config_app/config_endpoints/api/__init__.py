import logging

from flask import Blueprint, request, abort
from flask_restful import Resource, Api
from flask_restful.utils.cors import crossdomain
from data import model
from email.utils import formatdate
from calendar import timegm
from functools import partial, wraps
from jsonschema import validate, ValidationError

from config_app.c_app import app, IS_KUBERNETES
from config_app.config_endpoints.exception import InvalidResponse, InvalidRequest

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)

CROSS_DOMAIN_HEADERS = ["Authorization", "Content-Type", "X-Requested-With"]


class ApiExceptionHandlingApi(Api):
    pass

    @crossdomain(origin="*", headers=CROSS_DOMAIN_HEADERS)
    def handle_error(self, error):
        return super(ApiExceptionHandlingApi, self).handle_error(error)


api = ApiExceptionHandlingApi()

api.init_app(api_bp)


def log_action(kind, user_or_orgname, metadata=None, repo=None, repo_name=None):
    if not metadata:
        metadata = {}

    if repo:
        repo_name = repo.name

    model.log.log_action(
        kind, user_or_orgname, repo_name, user_or_orgname, request.remote_addr, metadata
    )


def format_date(date):
    """ Output an RFC822 date format. """
    if date is None:
        return None
    return formatdate(timegm(date.utctimetuple()))


def resource(*urls, **kwargs):
    def wrapper(api_resource):
        if not api_resource:
            return None

        api_resource.registered = True
        api.add_resource(api_resource, *urls, **kwargs)
        return api_resource

    return wrapper


class ApiResource(Resource):
    registered = False
    method_decorators = []

    def options(self):
        return None, 200


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


def no_cache(f):
    @wraps(f)
    def add_no_cache(*args, **kwargs):
        response = f(*args, **kwargs)
        if response is not None:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    return add_no_cache


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
                    raise InvalidResponse(ex.message)

            return resp

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
                raise InvalidRequest(ex.message)

        return wrapped

    return wrapper


def kubernetes_only(f):
    """ Aborts the request with a 400 if the app is not running on kubernetes """

    @wraps(f)
    def abort_if_not_kube(*args, **kwargs):
        if not IS_KUBERNETES:
            abort(400)

        return f(*args, **kwargs)

    return abort_if_not_kube


nickname = partial(add_method_metadata, "nickname")


import config_app.config_endpoints.api.discovery
import config_app.config_endpoints.api.kube_endpoints
import config_app.config_endpoints.api.suconfig
import config_app.config_endpoints.api.superuser
import config_app.config_endpoints.api.tar_config_loader
import config_app.config_endpoints.api.user
