import logging

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, abort, request, make_response
from jwt import get_unverified_header

from app import app
from data.logs_model import logs_model
from endpoints.keyserver.models_interface import ServiceKeyDoesNotExist
from endpoints.keyserver.models_pre_oci import pre_oci_model as model
from util.security import jwtutil
from util.request import get_request_ip


logger = logging.getLogger(__name__)
key_server = Blueprint("key_server", __name__)


JWT_HEADER_NAME = "Authorization"
JWT_AUDIENCE = app.config["PREFERRED_URL_SCHEME"] + "://" + app.config["SERVER_HOSTNAME"]


def _validate_jwk(jwk):
    if "kty" not in jwk:
        abort(400)

    if jwk["kty"] == "EC":
        if "x" not in jwk or "y" not in jwk:
            abort(400)
    elif jwk["kty"] == "RSA":
        if "e" not in jwk or "n" not in jwk:
            abort(400)
    else:
        abort(400)


def _validate_jwt(encoded_jwt, jwk, service):
    public_key = jwtutil.jwk_dict_to_public_key(jwk)

    try:
        jwtutil.decode(
            encoded_jwt, public_key, algorithms=["RS256"], audience=JWT_AUDIENCE, issuer=service
        )
    except jwtutil.InvalidTokenError:
        logger.exception("JWT validation failure")
        abort(400)


def _signer_kid(encoded_jwt, allow_none=False):
    headers = get_unverified_header(encoded_jwt)
    kid = headers.get("kid", None)
    if not kid and not allow_none:
        abort(400)

    return kid


def _lookup_service_key(service, signer_kid, approved_only=True):
    try:
        return model.get_service_key(signer_kid, service=service, approved_only=approved_only)
    except ServiceKeyDoesNotExist:
        abort(403)


def jwk_with_kid(key):
    jwk = key.jwk.copy()
    jwk.update({"kid": key.kid})
    return jwk


@key_server.route("/services/<service>/keys", methods=["GET"])
def list_service_keys(service):
    keys = model.list_service_keys(service)
    return jsonify({"keys": [jwk_with_kid(key) for key in keys]})


@key_server.route("/services/<service>/keys/<kid>", methods=["GET"])
def get_service_key(service, kid):
    try:
        key = model.get_service_key(kid, alive_only=False, approved_only=False)
    except ServiceKeyDoesNotExist:
        abort(404)

    if key.approval is None:
        abort(409)

    if key.expiration_date is not None and key.expiration_date <= datetime.utcnow():
        abort(403)

    resp = jsonify(key.jwk)
    lifetime = min(timedelta(days=1), ((key.expiration_date or datetime.max) - datetime.utcnow()))
    resp.cache_control.max_age = max(0, lifetime.total_seconds())
    return resp


@key_server.route("/services/<service>/keys/<kid>", methods=["PUT"])
def put_service_key(service, kid):
    metadata = {"ip": get_request_ip()}

    rotation_duration = request.args.get("rotation", None)
    expiration_date = request.args.get("expiration", None)
    if expiration_date is not None:
        try:
            expiration_date = datetime.utcfromtimestamp(float(expiration_date))
        except ValueError:
            logger.exception("Error parsing expiration date on key")
            abort(400)

    try:
        jwk = request.get_json()
    except ValueError:
        logger.exception("Error parsing JWK")
        abort(400)

    jwt_header = request.headers.get(JWT_HEADER_NAME, "")
    match = jwtutil.TOKEN_REGEX.match(jwt_header)
    if match is None:
        logger.error("Could not find matching bearer token")
        abort(400)

    encoded_jwt = match.group(1)

    _validate_jwk(jwk)

    signer_kid = _signer_kid(encoded_jwt, allow_none=True)
    if kid == signer_kid or signer_kid is None:
        # The key is self-signed. Create a new instance and await approval.
        _validate_jwt(encoded_jwt, jwk, service)
        model.create_service_key(
            "", kid, service, jwk, metadata, expiration_date, rotation_duration=rotation_duration
        )

        logs_model.log_action(
            "service_key_create",
            ip=get_request_ip(),
            metadata={
                "kid": kid,
                "preshared": False,
                "service": service,
                "name": "",
                "expiration_date": expiration_date,
                "user_agent": request.headers.get("User-Agent"),
                "ip": get_request_ip(),
            },
        )

        return make_response("", 202)

    # Key is going to be rotated.
    metadata.update({"created_by": "Key Rotation"})
    signer_key = _lookup_service_key(service, signer_kid)
    signer_jwk = signer_key.jwk

    _validate_jwt(encoded_jwt, signer_jwk, service)

    try:
        model.replace_service_key(signer_key.kid, kid, jwk, metadata, expiration_date)
    except ServiceKeyDoesNotExist:
        abort(404)

    logs_model.log_action(
        "service_key_rotate",
        ip=get_request_ip(),
        metadata={
            "kid": kid,
            "signer_kid": signer_key.kid,
            "service": service,
            "name": signer_key.name,
            "expiration_date": expiration_date,
            "user_agent": request.headers.get("User-Agent"),
            "ip": get_request_ip(),
        },
    )

    return make_response("", 200)


@key_server.route("/services/<service>/keys/<kid>", methods=["DELETE"])
def delete_service_key(service, kid):
    jwt_header = request.headers.get(JWT_HEADER_NAME, "")
    match = jwtutil.TOKEN_REGEX.match(jwt_header)
    if match is None:
        abort(400)

    encoded_jwt = match.group(1)

    signer_kid = _signer_kid(encoded_jwt)
    signer_key = _lookup_service_key(service, signer_kid, approved_only=False)

    self_signed = kid == signer_kid
    approved_key_for_service = signer_key.approval is not None

    if self_signed or approved_key_for_service:
        _validate_jwt(encoded_jwt, signer_key.jwk, service)

        try:
            model.delete_service_key(kid)
        except ServiceKeyDoesNotExist:
            abort(404)

        logs_model.log_action(
            "service_key_delete",
            ip=get_request_ip(),
            metadata={
                "kid": kid,
                "signer_kid": signer_key.kid,
                "service": service,
                "name": signer_key.name,
                "user_agent": request.headers.get("User-Agent"),
                "ip": get_request_ip(),
            },
        )

        return make_response("", 204)

    abort(403)
