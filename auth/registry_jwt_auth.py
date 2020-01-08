import logging

from functools import wraps

from jsonschema import validate, ValidationError
from flask import request, url_for
from flask_principal import identity_changed, Identity

from app import app, get_app_url, instance_keys
from auth.auth_context import set_authenticated_context
from auth.auth_context_type import SignedAuthContext
from auth.permissions import (
    repository_read_grant,
    repository_write_grant,
    repository_admin_grant,
)
from util.http import abort
from util.names import parse_namespace_repository
from util.security.registry_jwt import (
    ANONYMOUS_SUB,
    decode_bearer_header,
    InvalidBearerTokenException,
)


logger = logging.getLogger(__name__)


ACCESS_SCHEMA = {
    "type": "array",
    "description": "List of access granted to the subject",
    "items": {
        "type": "object",
        "required": ["type", "name", "actions",],
        "properties": {
            "type": {
                "type": "string",
                "description": "We only allow repository permissions",
                "enum": ["repository",],
            },
            "name": {
                "type": "string",
                "description": "The name of the repository for which we are receiving access",
            },
            "actions": {
                "type": "array",
                "description": "List of specific verbs which can be performed against repository",
                "items": {"type": "string", "enum": ["push", "pull", "*",],},
            },
        },
    },
}


class InvalidJWTException(Exception):
    pass


def get_auth_headers(repository=None, scopes=None):
    """
    Returns a dictionary of headers for auth responses.
    """
    headers = {}
    realm_auth_path = url_for("v2.generate_registry_jwt")
    authenticate = 'Bearer realm="{0}{1}",service="{2}"'.format(
        get_app_url(), realm_auth_path, app.config["SERVER_HOSTNAME"]
    )
    if repository:
        scopes_string = "repository:{0}".format(repository)
        if scopes:
            scopes_string += ":" + ",".join(scopes)

        authenticate += ',scope="{0}"'.format(scopes_string)

    headers["WWW-Authenticate"] = authenticate
    headers["Docker-Distribution-API-Version"] = "registry/2.0"
    return headers


def identity_from_bearer_token(bearer_header):
    """
    Process a bearer header and return the loaded identity, or raise InvalidJWTException if an
    identity could not be loaded.

    Expects tokens and grants in the format of the Docker registry v2 auth spec:
    https://docs.docker.com/registry/spec/auth/token/
    """
    logger.debug("Validating auth header: %s", bearer_header)

    try:
        payload = decode_bearer_header(bearer_header, instance_keys, app.config)
    except InvalidBearerTokenException as bte:
        logger.exception("Invalid bearer token: %s", bte)
        raise InvalidJWTException(bte)

    loaded_identity = Identity(payload["sub"], "signed_jwt")

    # Process the grants from the payload
    if "access" in payload:
        try:
            validate(payload["access"], ACCESS_SCHEMA)
        except ValidationError:
            logger.exception("We should not be minting invalid credentials")
            raise InvalidJWTException("Token contained invalid or malformed access grants")

        lib_namespace = app.config["LIBRARY_NAMESPACE"]
        for grant in payload["access"]:
            namespace, repo_name = parse_namespace_repository(grant["name"], lib_namespace)

            if "*" in grant["actions"]:
                loaded_identity.provides.add(repository_admin_grant(namespace, repo_name))
            elif "push" in grant["actions"]:
                loaded_identity.provides.add(repository_write_grant(namespace, repo_name))
            elif "pull" in grant["actions"]:
                loaded_identity.provides.add(repository_read_grant(namespace, repo_name))

    default_context = {"kind": "anonymous"}

    if payload["sub"] != ANONYMOUS_SUB:
        default_context = {
            "kind": "user",
            "user": payload["sub"],
        }

    return loaded_identity, payload.get("context", default_context)


def process_registry_jwt_auth(scopes=None):
    """
    Processes the registry JWT auth token found in the authorization header.

    If none found, no error is returned. If an invalid token is found, raises a 401.
    """

    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug("Called with params: %s, %s", args, kwargs)
            auth = request.headers.get("authorization", "").strip()
            if auth:
                try:
                    extracted_identity, context_dict = identity_from_bearer_token(auth)
                    identity_changed.send(app, identity=extracted_identity)
                    logger.debug("Identity changed to %s", extracted_identity.id)

                    auth_context = SignedAuthContext.build_from_signed_dict(context_dict)
                    if auth_context is not None:
                        logger.debug("Auth context set to %s", auth_context.signed_data)
                        set_authenticated_context(auth_context)

                except InvalidJWTException as ije:
                    repository = None
                    if "namespace_name" in kwargs and "repo_name" in kwargs:
                        repository = kwargs["namespace_name"] + "/" + kwargs["repo_name"]

                    abort(
                        401,
                        message=str(ije),
                        headers=get_auth_headers(repository=repository, scopes=scopes),
                    )
            else:
                logger.debug("No auth header.")

            return func(*args, **kwargs)

        return wrapper

    return inner
