import logging

from functools import wraps

from flask import request, url_for, Response

import features

from app import app, storage
from auth.registry_jwt_auth import process_registry_jwt_auth
from digest import digest_tools
from data.database import db_disallow_replica_use
from data.registry_model import registry_model
from data.model.oci.manifest import CreateManifestException
from data.model.oci.tag import RetargetTagException
from endpoints.decorators import anon_protect, parse_repository_name, check_readonly
from endpoints.metrics import image_pulls, image_pushes
from endpoints.v2 import v2_bp, require_repo_read, require_repo_write
from endpoints.v2.errors import (
    ManifestInvalid,
    ManifestUnknown,
    NameInvalid,
    TagExpired,
    NameUnknown,
)
from image.shared import ManifestException
from image.shared.schemas import parse_manifest_from_bytes
from image.docker.schema1 import DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE, DOCKER_SCHEMA1_CONTENT_TYPES
from image.docker.schema2 import DOCKER_SCHEMA2_CONTENT_TYPES
from image.oci import OCI_CONTENT_TYPES
from notifications import spawn_notification
from util.audit import track_and_log
from util.bytes import Bytes
from util.names import VALID_TAG_PATTERN
from util.registry.replication import queue_replication_batch


logger = logging.getLogger(__name__)

BASE_MANIFEST_ROUTE = '/<repopath:repository>/manifests/<regex("{0}"):manifest_ref>'
MANIFEST_DIGEST_ROUTE = BASE_MANIFEST_ROUTE.format(digest_tools.DIGEST_PATTERN)
MANIFEST_TAGNAME_ROUTE = BASE_MANIFEST_ROUTE.format(VALID_TAG_PATTERN)


@v2_bp.route(MANIFEST_TAGNAME_ROUTE, methods=["GET"])
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read
@anon_protect
def fetch_manifest_by_tagname(namespace_name, repo_name, manifest_ref):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        image_pulls.labels("v2", "tag", 404).inc()
        raise NameUnknown()

    tag = registry_model.get_repo_tag(repository_ref, manifest_ref)
    if tag is None:
        if registry_model.has_expired_tag(repository_ref, manifest_ref):
            logger.debug(
                "Found expired tag %s for repository %s/%s", manifest_ref, namespace_name, repo_name
            )
            msg = (
                "Tag %s was deleted or has expired. To pull, revive via time machine" % manifest_ref
            )
            image_pulls.labels("v2", "tag", 404).inc()
            raise TagExpired(msg)

        image_pulls.labels("v2", "tag", 404).inc()
        raise ManifestUnknown()

    manifest = registry_model.get_manifest_for_tag(tag)
    if manifest is None:
        # Something went wrong.
        image_pulls.labels("v2", "tag", 400).inc()
        raise ManifestInvalid()

    manifest_bytes, manifest_digest, manifest_media_type = _rewrite_schema_if_necessary(
        namespace_name, repo_name, manifest_ref, manifest
    )
    if manifest_bytes is None:
        image_pulls.labels("v2", "tag", 404).inc()
        raise ManifestUnknown()

    track_and_log(
        "pull_repo",
        repository_ref,
        analytics_name="pull_repo_100x",
        analytics_sample=0.01,
        tag=manifest_ref,
    )
    image_pulls.labels("v2", "tag", 200).inc()

    return Response(
        manifest_bytes.as_unicode(),
        status=200,
        headers={"Content-Type": manifest_media_type, "Docker-Content-Digest": manifest_digest,},
    )


@v2_bp.route(MANIFEST_DIGEST_ROUTE, methods=["GET"])
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read
@anon_protect
def fetch_manifest_by_digest(namespace_name, repo_name, manifest_ref):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        image_pulls.labels("v2", "manifest", 404).inc()
        raise NameUnknown()

    manifest = registry_model.lookup_manifest_by_digest(repository_ref, manifest_ref)
    if manifest is None:
        image_pulls.labels("v2", "manifest", 404).inc()
        raise ManifestUnknown()

    track_and_log("pull_repo", repository_ref, manifest_digest=manifest_ref)
    image_pulls.labels("v2", "manifest", 200).inc()

    return Response(
        manifest.internal_manifest_bytes.as_unicode(),
        status=200,
        headers={"Content-Type": manifest.media_type, "Docker-Content-Digest": manifest.digest,},
    )


def _rewrite_schema_if_necessary(namespace_name, repo_name, tag_name, manifest):
    # As per the Docker protocol, if the manifest is not schema version 1 and the manifest's
    # media type is not in the Accept header, we return a schema 1 version of the manifest for
    # the amd64+linux platform, if any, or None if none.
    # See: https://docs.docker.com/registry/spec/manifest-v2-2
    mimetypes = [mimetype for mimetype, _ in request.accept_mimetypes]
    if manifest.media_type in mimetypes:
        return manifest.internal_manifest_bytes, manifest.digest, manifest.media_type

    # Short-circuit check: If the mimetypes is empty or just `application/json`, verify we have
    # a schema 1 manifest and return it.
    if not mimetypes or mimetypes == ["application/json"]:
        if manifest.media_type in DOCKER_SCHEMA1_CONTENT_TYPES:
            return manifest.internal_manifest_bytes, manifest.digest, manifest.media_type

    logger.debug(
        "Manifest `%s` not compatible against %s; checking for conversion",
        manifest.digest,
        request.accept_mimetypes,
    )
    converted = registry_model.convert_manifest(
        manifest, namespace_name, repo_name, tag_name, mimetypes, storage
    )
    if converted is not None:
        return converted.bytes, converted.digest, converted.media_type

    # For back-compat, we always default to schema 1 if the manifest could not be converted.
    schema1 = registry_model.get_schema1_parsed_manifest(
        manifest, namespace_name, repo_name, tag_name, storage
    )
    if schema1 is None:
        return None, None, None

    return schema1.bytes, schema1.digest, schema1.media_type


def _reject_manifest2_schema2(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        namespace_name = kwargs["namespace_name"]
        if (
            request.content_type
            and request.content_type != "application/json"
            and request.content_type
            not in DOCKER_SCHEMA1_CONTENT_TYPES | DOCKER_SCHEMA2_CONTENT_TYPES | OCI_CONTENT_TYPES
        ):
            raise ManifestInvalid(
                detail={"message": "manifest schema version not supported"}, http_status_code=415
            )

        if namespace_name not in app.config.get("V22_NAMESPACE_BLACKLIST", []):
            if request.content_type in OCI_CONTENT_TYPES:
                if (
                    namespace_name not in app.config.get("OCI_NAMESPACE_WHITELIST", [])
                    and not features.GENERAL_OCI_SUPPORT
                ):
                    raise ManifestInvalid(
                        detail={"message": "manifest schema version not supported"},
                        http_status_code=415,
                    )

            return func(*args, **kwargs)

        if (
            _doesnt_accept_schema_v1()
            or request.content_type in DOCKER_SCHEMA2_CONTENT_TYPES | OCI_CONTENT_TYPES
        ):
            raise ManifestInvalid(
                detail={"message": "manifest schema version not supported"}, http_status_code=415
            )
        return func(*args, **kwargs)

    return wrapped


def _doesnt_accept_schema_v1():
    # If the client doesn't specify anything, still give them Schema v1.
    return (
        len(request.accept_mimetypes) != 0
        and DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE not in request.accept_mimetypes
    )


@v2_bp.route(MANIFEST_TAGNAME_ROUTE, methods=["PUT"])
@parse_repository_name()
@_reject_manifest2_schema2
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def write_manifest_by_tagname(namespace_name, repo_name, manifest_ref):
    parsed = _parse_manifest()
    return _write_manifest_and_log(namespace_name, repo_name, manifest_ref, parsed)


@v2_bp.route(MANIFEST_DIGEST_ROUTE, methods=["PUT"])
@parse_repository_name()
@_reject_manifest2_schema2
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def write_manifest_by_digest(namespace_name, repo_name, manifest_ref):
    parsed = _parse_manifest()
    if parsed.digest != manifest_ref:
        image_pushes.labels("v2", 400, "").inc()
        raise ManifestInvalid(detail={"message": "manifest digest mismatch"})

    if parsed.schema_version != 2:
        return _write_manifest_and_log(namespace_name, repo_name, parsed.tag, parsed)

    # If the manifest is schema version 2, then this cannot be a normal tag-based push, as the
    # manifest does not contain the tag and this call was not given a tag name. Instead, we write the
    # manifest with a temporary tag, as it is being pushed as part of a call for a manifest list.
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        image_pushes.labels("v2", 404, "").inc()
        raise NameUnknown()

    expiration_sec = app.config["PUSH_TEMP_TAG_EXPIRATION_SEC"]
    manifest = registry_model.create_manifest_with_temp_tag(
        repository_ref, parsed, expiration_sec, storage
    )
    if manifest is None:
        image_pushes.labels("v2", 400, "").inc()
        raise ManifestInvalid()

    image_pushes.labels("v2", 201, manifest.media_type).inc()
    return Response(
        "OK",
        status=201,
        headers={
            "Docker-Content-Digest": manifest.digest,
            "Location": url_for(
                "v2.fetch_manifest_by_digest",
                repository="%s/%s" % (namespace_name, repo_name),
                manifest_ref=manifest.digest,
            ),
        },
    )


def _parse_manifest():
    content_type = request.content_type or DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
    if content_type == "application/json":
        # For back-compat.
        content_type = DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE

    try:
        return parse_manifest_from_bytes(Bytes.for_string_or_unicode(request.data), content_type)
    except ManifestException as me:
        logger.exception("failed to parse manifest when writing by tagname")
        raise ManifestInvalid(detail={"message": "failed to parse manifest: %s" % me})


@v2_bp.route(MANIFEST_DIGEST_ROUTE, methods=["DELETE"])
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull", "push"])
@require_repo_write
@anon_protect
@check_readonly
def delete_manifest_by_digest(namespace_name, repo_name, manifest_ref):
    """
    Delete the manifest specified by the digest.

    Note: there is no equivalent method for deleting by tag name because it is
    forbidden by the spec.
    """
    with db_disallow_replica_use():
        repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
        if repository_ref is None:
            raise NameUnknown()

        manifest = registry_model.lookup_manifest_by_digest(repository_ref, manifest_ref)
        if manifest is None:
            raise ManifestUnknown()

        tags = registry_model.delete_tags_for_manifest(manifest)
        if not tags:
            raise ManifestUnknown()

        for tag in tags:
            track_and_log("delete_tag", repository_ref, tag=tag.name, digest=manifest_ref)

        return Response(status=202)


def _write_manifest_and_log(namespace_name, repo_name, tag_name, manifest_impl):
    with db_disallow_replica_use():
        repository_ref, manifest, tag = _write_manifest(
            namespace_name, repo_name, tag_name, manifest_impl
        )

        # Queue all blob manifests for replication.
        if features.STORAGE_REPLICATION:
            blobs = registry_model.get_manifest_local_blobs(manifest, storage)
            if blobs is None:
                logger.error("Could not lookup blobs for manifest `%s`", manifest.digest)
            else:
                with queue_replication_batch(namespace_name) as queue_storage_replication:
                    for blob_digest in blobs:
                        queue_storage_replication(blob_digest)

        track_and_log("push_repo", repository_ref, tag=tag_name)
        spawn_notification(repository_ref, "repo_push", {"updated_tags": [tag_name]})
        image_pushes.labels("v2", 201, manifest.media_type).inc()

        return Response(
            "OK",
            status=201,
            headers={
                "Docker-Content-Digest": manifest.digest,
                "Location": url_for(
                    "v2.fetch_manifest_by_digest",
                    repository="%s/%s" % (namespace_name, repo_name),
                    manifest_ref=manifest.digest,
                ),
            },
        )


def _write_manifest(namespace_name, repo_name, tag_name, manifest_impl):
    # NOTE: These extra checks are needed for schema version 1 because the manifests
    # contain the repo namespace, name and tag name.
    if manifest_impl.schema_version == 1:
        if (
            manifest_impl.namespace == ""
            and features.LIBRARY_SUPPORT
            and namespace_name == app.config["LIBRARY_NAMESPACE"]
        ):
            pass
        elif manifest_impl.namespace != namespace_name:
            raise NameInvalid(
                message="namespace name does not match manifest",
                detail={
                    "namespace name `%s` does not match `%s` in manifest"
                    % (namespace_name, manifest_impl.namespace)
                },
            )

        if manifest_impl.repo_name != repo_name:
            raise NameInvalid(
                message="repository name does not match manifest",
                detail={
                    "repository name `%s` does not match `%s` in manifest"
                    % (repo_name, manifest_impl.repo_name)
                },
            )

        try:
            if not manifest_impl.layers:
                raise ManifestInvalid(detail={"message": "manifest does not reference any layers"})
        except ManifestException as me:
            raise ManifestInvalid(detail={"message": str(me)})

    # Ensure that the repository exists.
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    # Create the manifest(s) and retarget the tag to point to it.
    try:
        manifest, tag = registry_model.create_manifest_and_retarget_tag(
            repository_ref, manifest_impl, tag_name, storage, raise_on_error=True
        )
    except CreateManifestException as cme:
        raise ManifestInvalid(detail={"message": str(cme)})
    except RetargetTagException as rte:
        raise ManifestInvalid(detail={"message": str(rte)})

    if manifest is None:
        raise ManifestInvalid()

    return repository_ref, manifest, tag
