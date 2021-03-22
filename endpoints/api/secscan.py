"""
List and manage repository vulnerabilities and other security information.
"""

import logging
import features

from enum import Enum, unique

from app import storage
from auth.decorators import process_basic_auth_no_pass
from data.registry_model import registry_model
from data.secscan_model import secscan_model
from data.secscan_model.datatypes import ScanLookupStatus
from endpoints.api import (
    require_repo_read,
    path_param,
    RepositoryParamResource,
    resource,
    nickname,
    show_if,
    parse_args,
    query_param,
    disallow_for_app_repositories,
    deprecated,
)
from endpoints.decorators import anon_allowed
from endpoints.exception import NotFound, DownstreamIssue
from endpoints.api.manifest import MANIFEST_DIGEST_ROUTE
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


MAPPED_STATUSES = {}
MAPPED_STATUSES[ScanLookupStatus.FAILED_TO_INDEX] = SecurityScanStatus.FAILED
MAPPED_STATUSES[ScanLookupStatus.SUCCESS] = SecurityScanStatus.SCANNED
MAPPED_STATUSES[ScanLookupStatus.NOT_YET_INDEXED] = SecurityScanStatus.QUEUED
MAPPED_STATUSES[ScanLookupStatus.UNSUPPORTED_FOR_INDEXING] = SecurityScanStatus.UNSUPPORTED


logger = logging.getLogger(__name__)


def _security_info(manifest_or_legacy_image, include_vulnerabilities=True):
    """
    Returns a dict representing the result of a call to the security status API for the given
    manifest or image.
    """
    result = secscan_model.load_security_information(
        manifest_or_legacy_image, include_vulnerabilities=include_vulnerabilities
    )
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


@resource("/v1/repository/<apirepopath:repository>/image/<imageid>/security")
@show_if(features.SECURITY_SCANNER)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("imageid", "The image ID")
class RepositoryImageSecurity(RepositoryParamResource):
    """
    Operations for managing the vulnerabilities in a repository image.

    DEPRECATED: Please retrieve security by manifest .
    """

    @process_basic_auth_no_pass
    @anon_allowed
    @require_repo_read
    @nickname("getRepoImageSecurity")
    @deprecated()
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "vulnerabilities", "Include vulnerabilities information", type=truthy_bool, default=False
    )
    def get(self, namespace, repository, imageid, parsed_args):
        """
        Fetches the features and vulnerabilities (if any) for a repository image.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        legacy_image = registry_model.get_legacy_image(repo_ref, imageid, storage)
        if legacy_image is None:
            raise NotFound()

        return _security_info(legacy_image, parsed_args.vulnerabilities)


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
    @require_repo_read
    @nickname("getRepoManifestSecurity")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "vulnerabilities", "Include vulnerabilities informations", type=truthy_bool, default=False
    )
    def get(self, namespace, repository, manifestref, parsed_args):
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        manifest = registry_model.lookup_manifest_by_digest(repo_ref, manifestref, allow_dead=True)
        if manifest is None:
            raise NotFound()

        return _security_info(manifest, parsed_args.vulnerabilities)
