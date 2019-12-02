""" List and manage repository vulnerabilities and other security information. """

import logging
import features

from app import app, secscan_api
from auth.decorators import process_basic_auth_no_pass
from data.registry_model import registry_model
from data.registry_model.datatypes import SecurityScanStatus
from endpoints.api import (
    require_repo_read,
    path_param,
    RepositoryParamResource,
    resource,
    nickname,
    show_if,
    parse_args,
    query_param,
    truthy_bool,
    disallow_for_app_repositories,
)
from endpoints.exception import NotFound, DownstreamIssue
from endpoints.api.manifest import MANIFEST_DIGEST_ROUTE
from util.secscan.api import APIRequestFailure


logger = logging.getLogger(__name__)


def _security_info(manifest_or_legacy_image, include_vulnerabilities=True):
    """ Returns a dict representing the result of a call to the security status API for the given
      manifest or image.
  """
    status = registry_model.get_security_status(manifest_or_legacy_image)
    if status is None:
        raise NotFound()

    if status != SecurityScanStatus.SCANNED:
        return {
            "status": status.value,
        }

    try:
        if include_vulnerabilities:
            data = secscan_api.get_layer_data(
                manifest_or_legacy_image, include_vulnerabilities=True
            )
        else:
            data = secscan_api.get_layer_data(manifest_or_legacy_image, include_features=True)
    except APIRequestFailure as arf:
        raise DownstreamIssue(arf.message)

    if data is None:
        # If no data was found but we reached this point, then it indicates we have incorrect security
        # status for the manifest or legacy image. Mark the manifest or legacy image as unindexed
        # so it automatically gets re-indexed.
        if app.config.get("REGISTRY_STATE", "normal") == "normal":
            registry_model.reset_security_status(manifest_or_legacy_image)

        return {
            "status": SecurityScanStatus.QUEUED.value,
        }

    return {
        "status": status.value,
        "data": data,
    }


@resource("/v1/repository/<apirepopath:repository>/image/<imageid>/security")
@show_if(features.SECURITY_SCANNER)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("imageid", "The image ID")
class RepositoryImageSecurity(RepositoryParamResource):
    """ Operations for managing the vulnerabilities in a repository image. """

    @process_basic_auth_no_pass
    @require_repo_read
    @nickname("getRepoImageSecurity")
    @disallow_for_app_repositories
    @parse_args()
    @query_param(
        "vulnerabilities", "Include vulnerabilities informations", type=truthy_bool, default=False
    )
    def get(self, namespace, repository, imageid, parsed_args):
        """ Fetches the features and vulnerabilities (if any) for a repository image. """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        legacy_image = registry_model.get_legacy_image(repo_ref, imageid)
        if legacy_image is None:
            raise NotFound()

        return _security_info(legacy_image, parsed_args.vulnerabilities)


@resource(MANIFEST_DIGEST_ROUTE + "/security")
@show_if(features.SECURITY_SCANNER)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("manifestref", "The digest of the manifest")
class RepositoryManifestSecurity(RepositoryParamResource):
    """ Operations for managing the vulnerabilities in a repository manifest. """

    @process_basic_auth_no_pass
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
