import features

from flask import Response, request

from auth.registry_jwt_auth import process_registry_jwt_auth
from data.model import ManifestDoesNotExist
from data.registry_model import registry_model
from digest import digest_tools
from endpoints.decorators import (
    inject_registry_model,
    anon_protect,
    disallow_for_account_recovery_mode,
    parse_repository_name,
    check_readonly,
    route_show_if,
)
from endpoints.v2 import v2_bp, require_repo_read
from endpoints.v2.errors import ManifestUnknown, NameUnknown
from image.oci.index import OCIIndexBuilder

from util.http import abort


BASE_REFERRERS_ROUTE = '/<repopath:repository>/referrers/<regex("{0}"):manifest_ref>'
MANIFEST_REFERRERS_ROUTE = BASE_REFERRERS_ROUTE.format(digest_tools.DIGEST_PATTERN)


@v2_bp.route(MANIFEST_REFERRERS_ROUTE, methods=["GET"])
# @route_show_if(features.REFERRERS_API)
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read(allow_for_superuser=True)
@anon_protect
@inject_registry_model()
def list_manifest_referrers(namespace_name, repo_name, manifest_ref, registry_model):
    try:
        repository_ref = registry_model.lookup_repository(
            namespace_name, repo_name, raise_on_error=True, manifest_ref=manifest_ref
        )
    except RepositoryDoesNotExist as e:
        raise NameUnknown("repository not found")

    try:
        manifest = registry_model.lookup_manifest_by_digest(
            repository_ref, manifest_ref, raise_on_error=True
        )
    except ManifestDoesNotExist as e:
        raise ManifestUnknown(str(e))

    artifact_type = request.args.get("artifactType", None)

    referrers = registry_model.lookup_referrers_for_manifest(manifest, artifact_type)
    index = _build_referrers_index_for_manifests(referrers)

    return Response(
        index.bytes.as_unicode(),
        status=200,
        headers={
            "Content-Type": index.media_type
        }
    )


def _build_referrers_index_for_manifests(referrers):
    index_builder = OCIIndexBuilder()

    for referrer in referrers:
        parsed_referrer = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(referrer.manifest_bytes), referrer.media_type.name
        )
        index_builder.add_manifest(referrer)

    index = index_builder.build()
    return index
