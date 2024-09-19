"""
List and manage repository vulnerabilities and other security information.
"""

import logging
from enum import Enum, unique

import features
from app import model_cache, storage
from auth.decorators import process_basic_auth_no_pass
from data.registry_model import registry_model
from data.secscan_model import secscan_model
from data.secscan_model.datatypes import ScanLookupStatus
from endpoints.api import (
    RepositoryParamResource,
    deprecated,
    disallow_for_app_repositories,
    nickname,
    parse_args,
    path_param,
    query_param,
    require_repo_read,
    resource,
    show_if,
)
from endpoints.api.manifest import MANIFEST_DIGEST_ROUTE
from endpoints.decorators import anon_allowed
from endpoints.exception import DownstreamIssue, NotFound
from util.parsing import truthy_bool


@unique
class SecurityScanStatus(Enum):
    """
    Security scan status enum.
    """

    SCANNED = "scanned"
    FAILED = "failed"
    QUEUED = "queued"
    UNSUPPORTED = "unsupported"
    MANIFEST_LAYER_TOO_LARGE = "manifest_layer_too_large"


MAPPED_STATUSES = {}
MAPPED_STATUSES[ScanLookupStatus.FAILED_TO_INDEX] = SecurityScanStatus.FAILED
MAPPED_STATUSES[ScanLookupStatus.SUCCESS] = SecurityScanStatus.SCANNED
MAPPED_STATUSES[ScanLookupStatus.NOT_YET_INDEXED] = SecurityScanStatus.QUEUED
MAPPED_STATUSES[ScanLookupStatus.UNSUPPORTED_FOR_INDEXING] = SecurityScanStatus.UNSUPPORTED
MAPPED_STATUSES[
    ScanLookupStatus.MANIFEST_LAYER_TOO_LARGE
] = SecurityScanStatus.MANIFEST_LAYER_TOO_LARGE


logger = logging.getLogger(__name__)


def _security_info(manifest_or_legacy_image, include_vulnerabilities=True, raw=False):
    """
    Returns a dict representing the result of a call to the security status API for the given
    manifest or image.
    """
    result = secscan_model.load_security_information(
        manifest_or_legacy_image,
        include_vulnerabilities=include_vulnerabilities,
        proxy_clair_response=raw,
        model_cache=model_cache,
    )

    # lets see if we can bundle raw in result and status check
    if raw:
        return result

    if result.status == ScanLookupStatus.UNKNOWN_MANIFEST_OR_IMAGE:
        raise NotFound()

    if result.status == ScanLookupStatus.COULD_NOT_LOAD:
        raise DownstreamIssue(result.scanner_request_error)

    assert result.status in MAPPED_STATUSES
    return {
        "status": MAPPED_STATUSES[result.status].value,
        "data": result.security_information.to_dict()
        if result.security_information is not None
        else None,
    }


@resource(MANIFEST_DIGEST_ROUTE + "/security")
@show_if(features.SECURITY_SCANNER)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
class RepositoryManifestSecurity(RepositoryParamResource):
    """
    Operations for managing the vulnerabilities in a repository manifest.
    """

    @process_basic_auth_no_pass
    @anon_allowed
    @require_repo_read(allow_for_superuser=True)
    @nickname("getRepoManifestSecurity")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "vulnerabilities", "Include vulnerabilities informations", type=truthy_bool, default=False
    )
    @query_param(
        "raw",
        "Returns a vulnerability report for the specified manifest from Clair",
        type=truthy_bool,
        default=False,
    )
    def get(self, namespace, repository, manifestref, parsed_args):
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref, allow_dead=True)
        if manifest is None:
            raise NotFound()

        return _security_info(manifest, parsed_args.vulnerabilities, parsed_args.raw)
