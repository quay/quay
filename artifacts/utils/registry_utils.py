import hashlib
import json
import logging
from pprint import pprint

from app import app

logger = logging.getLogger(__name__)

EMPTY_CONFIG_JSON = "{}"


class RegistryError(Exception):
    pass


def get_artifact_manifest(artifact_name: str, artifact_type: str):
    pass


def calculate_sha256_digest(data):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data)
    digest = sha256_hash.hexdigest()
    return f'sha256:{digest}'


def do_request(method, path, headers=None, query_string=None, data=None):
    with app.test_client() as c:
        response = c.open(
            method=method,
            path=path,
            headers=headers,
            data=data,
            query_string=query_string
        )
        return response


def check_blob_exists(namespace, repo_name, digest, registry_grant_token):
    headers = {
        'Authorization': f'Bearer {registry_grant_token}'
    }
    path = f'/v2/{namespace}/{repo_name}/blobs/{digest}'
    response = do_request('HEAD', path, headers=headers)
    logger.info(f'🚜🚜🚜🚜🚜 check blob exists response {response} {response.data}')
    return response


def start_upload_blob(namespace, repo_name, registry_grant_token):
    headers = {
        'Authorization': f'Bearer {registry_grant_token}'
    }
    path = f'/v2/{namespace}/{repo_name}/blobs/uploads/'
    response = do_request('POST', path, headers=headers)
    logger.info(f'🚜🚜🚜🚜🚜 start blob upload response {response} {response.data}')
    pprint(dict(response.headers))
    return response


def upload_artifact_blob(namespace, repo_name, data, data_digest, registry_grant_token):
    blob_exists_response = check_blob_exists(namespace, repo_name, data_digest, registry_grant_token)
    logger.info(f'🟦 🟦 🟦 🟦  uploading blob {data_digest}, exists? {blob_exists_response.data}')
    if blob_exists_response.status_code == 200:
        return blob_exists_response

    start_response = start_upload_blob(namespace, repo_name, registry_grant_token)
    if start_response.status_code != 202:
        return start_response

    location = start_response.headers.get('Location')
    qs = {
        'digest': data_digest,
    }
    headers = {
        'Authorization': f'Bearer {registry_grant_token}'
    }
    response = do_request('PUT', location, headers=headers, data=data, query_string=qs)
    logger.info(f'🟦 🟦 🟦 🟦  blob upload response {response} {response.data}')
    return response


def ensure_empty_blob(namespace, repo_name, grant_token):
    data = "{}"
    empty_blob_digest = calculate_sha256_digest(data)
    return upload_artifact_blob(namespace, repo_name, data, empty_blob_digest, grant_token)


def create_oci_artifact_manifest(media_type, length, digest, config_media_type=None, config_length=None,
                                 config_digest=None):
    # Generate the list of layer digests
    if not config_length:
        config_media_type = "application/vnd.oci.empty.v1+json"
        config_length = 2
        config_digest = calculate_sha256_digest(EMPTY_CONFIG_JSON)

    # Create the OCI manifest
    manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "artifactType": media_type,
        "config": {
            "mediaType": config_media_type,
            "size": config_length,
            "digest": config_digest
        },
        "layers": [
            {
                "mediaType": media_type,
                "size": length,
                "digest": digest
            }
        ]
    }

    # Convert the manifest to JSON
    manifest_json = json.dumps(manifest, indent=2)
    return manifest_json


def upload_oci_artifact_manifest(namespace, repo_name, manifest, tag, registry_grant_token):
    headers = {
        'Authorization': f'Bearer {registry_grant_token}',
        'Content-Type': 'application/vnd.oci.image.manifest.v1+json'
    }

    path = f'/v2/{namespace}/{repo_name}/manifests/{tag}'
    response = do_request('PUT', path, headers=headers, data=manifest)
    logger.info(f'🟦 🟦 🟦 🟦  manifest upload response {response} {response.data}')
    return response


def list_tags(namespace, repo_name, grant_token):
    path = f'/v2/{namespace}/{repo_name}/tags/list'
    headers = {
        'Authorization': f'Bearer {grant_token}'
    }

    response = do_request('GET', path, headers=headers)
    logger.info(f'🟦 🟦 🟦 🟦  list tags response {response} {response.data}')
    return response


def get_oci_manifest_by_tag(namespace, repo_name, tag, grant_token):
    path = f'/v2/{namespace}/{repo_name}/manifests/{tag}'
    headers = {
        'Authorization': f'Bearer {grant_token}',
        'Accept': 'application/vnd.oci.image.manifest.v1+json'
    }
    response = do_request('GET', path, headers=headers)
    pprint(response.headers)
    logger.info(f'🟦 🟦 🟦 🟦  get manifest response {response} {response.data}')
    return response


def get_oci_blob(namespace, repo_name, digest, grant_token):
    path = f'/v2/{namespace}/{repo_name}/blobs/{digest}'
    headers = {
        "Authorization": f"Bearer {grant_token}"
    }
    response = do_request('GET', path, headers=headers)
    return response
