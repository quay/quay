from flask import Response, request

import features

from digest import digest_tools
from data.database import Manifest, ManifestSubject
from data.registry_model import registry_model
from data.model import RepositoryDoesNotExist, ManifestDoesNotExist
from endpoints.api import require_repo_read, show_if
from endpoints.decorators import (
    anon_protect,
    disallow_for_account_recovery_mode,
    parse_repository_name,
)
from endpoints.metrics import image_pulls
from endpoints.v2 import v2_bp
from endpoints.v2.errors import (
    ManifestUnknown,
    NameUnknown,
)
from image.oci.index import OCIIndexBuilder
from image.shared.schemas import parse_manifest_from_bytes
from util.bytes import Bytes


BASE_REFERRERS_ROUTE = '/<repopath:repository>/referrers/<regex("{0}"):manifest_ref>'
REFERRERS_DIGEST_ROUTE = BASE_REFERRERS_ROUTE.format(digest_tools.DIGEST_PATTERN)


# TODO: We'll add permissions back in when we conclude what
# they need to be
@v2_bp.route(REFERRERS_DIGEST_ROUTE, methods=["GET"])
@disallow_for_account_recovery_mode
@parse_repository_name()
# @require_repo_read(allow_for_superuser=True)
@anon_protect
# @show_if(features.OCI_11)
def fetch_referrers(namespace_name, repo_name, manifest_ref):
    artifactType = request.args.get("artifactType")

    try:
        repository_ref = registry_model.lookup_repository(
            namespace_name, repo_name, raise_on_error=True, manifest_ref=manifest_ref
        )
    except RepositoryDoesNotExist as e:
        raise NameUnknown("repository not found") from e

    # TODO: Do we return manifest unknown here? Or just an empty list?
    try:
        manifest = registry_model.lookup_manifest_by_digest(
            repository_ref, manifest_ref, raise_on_error=True
        )
    except ManifestDoesNotExist as e:
        raise ManifestUnknown(str(e)) from e

    manifest_builder = OCIIndexBuilder()
    try:
        manifest: Manifest
        for manifest in (
            Manifest.select()
            .join(ManifestSubject)
            .where(
                ManifestSubject.subject == manifest_ref, ManifestSubject.manifest_id == Manifest.id
            )
        ):
            subManifest = parse_manifest_from_bytes(
                Bytes.for_string_or_unicode(manifest.manifest_bytes), manifest.media_type.name
            )
            if artifactType is None or (
                artifactType is not None and artifactType == subManifest.artifact_type
            ):
                manifest_builder.add_manifest(subManifest, "", "", subManifest.artifact_type)
    except ManifestDoesNotExist as e:
        pass

    if artifactType is not None:
        manifest_builder.add_annotation(
            "org.opencontainers.referrers.filtersApplied", "artifactType"
        )

    manifest_index = manifest_builder.build(allow_empty=True)
    return Response(
        manifest_index.bytes.as_unicode(),
        status=200,
        headers={
            "Content-Type": manifest_index.media_type,
            "Docker-Content-Digest": manifest_index.digest,
        },
    )
