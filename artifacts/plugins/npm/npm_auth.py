import logging
import uuid
from functools import wraps
from hashlib import sha512

from util.http import abort

from artifacts.utils.plugin_auth import apply_auth_result

from data.model import DataModelException

from auth.validateresult import ValidateResult, AuthKind

from artifacts.plugins.npm.npm_models import NpmToken
from auth.decorators import authentication_count
from endpoints.v2.v2auth import generate_registry_jwt

from auth.credentials import validate_credentials, CredentialKind
from flask import request, jsonify

logger = logging.getLogger(__name__)


def get_bearer_token():
    return request.headers.get('Authorization').split(' ')[1] if request.headers.get('Authorization') else None


def get_username_password():
    user_data = request.get_json()
    username = user_data.get('name')
    password = user_data.get('password')
    return username, password


def validate_npm_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_bearer_token():
            return {'error': 'Unauthorized'}, 401
        return f(*args, **kwargs)


def delete_npm_token(token):
    token_key = sha512(token.encode('utf-8')).hexdigest()
    try:
        token = NpmToken.get(token_key=token_key)
        token.delete_instance()
        return None
    except DataModelException as e:
        logger.error('Error deleting token', e)
        return f"Error deleting token: {e}"


def get_token_from_db(token):
    token_key = sha512(token.encode('utf-8')).hexdigest()
    return NpmToken.get(token_key=token_key)


def validate_npm_auth_token(token):
    # get the token from the DB and validate it
    if not token:
        abort(401, message='No token found')

    try:
        db_token = get_token_from_db(token)
        if not db_token:
            return ValidateResult(AuthKind.credentials, missing=True)
        return ValidateResult(AuthKind.credentials, user=db_token.user)
    except Exception as e:
        # TODO: use specific exception
        logger.error("Error validating token: %s", e)
        abort(401, message='Error validating token')


def generate_auth_token_for_write(namespace, repo_name):
    token = get_bearer_token()
    auth_result = validate_npm_auth_token(token)
    apply_auth_result(auth_result)
    aud_params = "localhost:8080"
    push_scope = f"repository:{namespace}/{repo_name}:push"
    scope_params = [push_scope]
    return generate_registry_jwt(auth_result, True, aud_params, scope_params)


def generate_auth_token_for_read(namespace, repo_name):
    # TODO handle anonymous read
    token = get_bearer_token()
    auth_result = validate_npm_auth_token(token)
    apply_auth_result(auth_result)
    aud_params = "localhost:8080"
    pull_scope = f"repository:{namespace}/{repo_name}:pull"
    # scope_result = _authorize_or_downscope_request(push_scope, has_valid_auth_context)
    scope_params = [pull_scope]
    return generate_registry_jwt(auth_result, True, aud_params, scope_params)
