import base64
import json
import logging
from pprint import pprint

from artifacts.plugins.npm.npm_utils import parse_package_tarball, get_package_list, check_valid_package_name, \
    InvalidPackageNameError, parse_package_metadata, get_package_tarball, quayRegistryClient
from artifacts.utils.plugin_auth import apply_auth_result
from artifacts.utils.registry_utils import calculate_sha256_digest
from auth.credentials import validate_credentials

from auth.auth_context import get_authenticated_user, get_authenticated_context, set_authenticated_context
from flask import Blueprint, request, jsonify, make_response, abort

from artifacts.plugins.npm.npm_auth import get_username_password, get_bearer_token, \
    validate_npm_auth_token, generate_auth_token_for_write, delete_npm_token, generate_auth_token_for_read
from artifacts.plugins.npm.npm_models import create_and_save_new_token_for_user

from util.cache import no_cache

bp = Blueprint("npm", __name__)
logger = logging.getLogger(__name__)


@bp.route('/ping')
def ping():
    return jsonify({'ok': 'test'}), 200


@bp.route('/-/v1/login', methods=['POST'])
def login_hostname():
    """
        Example request data:
        {"hostname":"syahmed-mac"}
    """
    logger.info(f'🔴 headers {request.headers}')
    return jsonify({'error': 'validation method not supported'}), 401


def encode_basic_auth(username, password):
    auth_string = f"{username}:{password}"
    auth_bytes = auth_string.encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes)
    return encoded_auth.decode('utf-8')


@bp.route('/-/user/org.couchdb.user:<user_id>', methods=['PUT'])
@no_cache
def npm_login(user_id):
    """
    NPM login user
    ref: https://github.com/npm/registry/blob/master/docs/user/authentication.md#login
    """
    username, password = get_username_password()
    auth_result, _auth_kind = validate_credentials(username, password)
    apply_auth_result(auth_result)
    token = create_and_save_new_token_for_user(get_authenticated_user())
    return make_response(jsonify({"token": token}), 201)


@bp.route('/-/user/token/<token>', methods=['DELETE'])
def logout(token):
    """
    logout a user
    bearer token in the Authorization header identifies the user
    ref: https://docs.npmjs.com/cli/v7/commands/npm-logout
    ref: https://github.com/npm/registry/blob/master/docs/user/authentication.md#token-delete
    """

    auth_result = validate_npm_auth_token(token)
    if not auth_result:
        return jsonify({'error': 'Invalid token'}), 401

    error = delete_npm_token(token)
    if not error:
        return jsonify({'ok': 'Logged out'}), 201

    return make_response(jsonify({'error': error}), 500)


@bp.route('/<path:package>', methods=['PUT'])
def npm_publish_package(package):
    logger.info(f'🔴🟣🔴🟣🔴🟣 PUT package {package}')
    try:
        check_valid_package_name(package)
    except InvalidPackageNameError as e:
        return jsonify({'error': str(e)}), 400

    logger.info(f'🔴 package {package} auth context {get_authenticated_context()}')
    package_data = request.get_json()
    package_name = package_data.get('name')
    package_versions = package_data.get('versions')

    if not package_name or not package_versions or not package_name.startswith('@'):
        return jsonify({'error': 'Invalid package data'}), 400

    # TODO: can there be multiple versions?
    package_version = list(package_versions.keys())[0]

    namespace, repo_name = package_name.split('/')
    namespace = namespace.replace('@', '')
    repo_tag = package_version

    # scope request to upload package
    grant_token = generate_auth_token_for_write(namespace, repo_name)
    logger.info(f'🔴🟣🔴🟣🔴🟣 grant_token {grant_token}')

    # upload config
    data = parse_package_tarball(package_data)
    if not data:
        return jsonify({'error': 'No data found to upload'}), 400

    metadata = parse_package_metadata(package_data)
    if not metadata:
        metadata = {}

    metadata_json = json.dumps(metadata)
    metadata_digest = calculate_sha256_digest(metadata_json.encode('utf-8'))
    response = quayRegistryClient.upload_artifact_blob(namespace, repo_name, metadata_json, metadata_digest, grant_token)
    # TODO: check if the response is good

    data_digest = calculate_sha256_digest(data)
    response = quayRegistryClient.upload_artifact_blob(namespace, repo_name, data, data_digest, grant_token)

    logger.info(f'🔴🟣🔴🟣🔴🟣 digest {data_digest}')
    logger.info(f'🔴🟣🔴🟣🔴🟣 response {response}')

    pprint(dict(response.headers))

    # create manifest
    manifest = quayRegistryClient.create_oci_artifact_manifest(
        media_type='application/vnd.npm.package.v1+json',
        length=len(data),
        digest=data_digest,
        config_media_type='application/vnd.npm.config.v1+json',
        config_digest=metadata_digest,
        config_length=len(metadata),
    )

    logger.info(f'🔴🟣🔴🟣🔴🟣 manifest {manifest}')

    response = quayRegistryClient.upload_oci_artifact_manifest(namespace, repo_name, manifest, repo_tag, grant_token)
    logger.info(f'🔴🟣🔴🟣🔴🟣 manifest response {response} {response.data}')
    # TODO: check if the response is good
    return jsonify({'ok': 'Package published'}), 200


@bp.route('/<path:package>', methods=['GET'])
def npm_get_package(package):
    logger.info(f'🎁🎁🎁🎁 package {package} auth context {get_authenticated_context()}')
    try:
        check_valid_package_name(package)
    except InvalidPackageNameError as e:
        return jsonify({'error': str(e)}), 400

    namespace, repo_name = package.split('/')
    if not namespace or not repo_name:
        return jsonify({'error': 'Invalid package name'}), 400

    namespace = namespace.replace('@', '')
    package_list = get_package_list(namespace, repo_name)
    package_response =  {
        'name': package,
        'versions': package_list
    }
    return jsonify(package_response), 200


@bp.route('/download/<path:namespace>/<path:package_name>/<path:version>', methods=['GET'])
def npm_get_package_tarball(namespace, package_name, version):
    # get the package
    namespace = namespace.replace('@', '')
    logger.info(f'🎁🎁🎁🎁 package {namespace}/{package_name}/{version} auth context {get_authenticated_context()}')
    tarball = get_package_tarball(namespace, package_name, version)
    r = make_response(tarball)
    r.headers.set('Content-Type', 'application/octet-stream')
    return r
