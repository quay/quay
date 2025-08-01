"""
List and manage repository signing information.
"""

import logging

import features
from app import tuf_metadata_api
from endpoints.api import (
    NotFound,
    RepositoryParamResource,
    disallow_for_app_repositories,
    nickname,
    path_param,
    require_repo_read,
    resource,
    show_if,
)
from endpoints.api.signing_models_pre_oci import pre_oci_model as model

logger = logging.getLogger(__name__)


@resource("/v1/repository/<apirepopath:repository>/signatures")
@show_if(features.SIGNING)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositorySignatures(RepositoryParamResource):
    """
    Operations for managing the signatures in a repository image.
    """

    @require_repo_read(allow_for_superuser=True, allow_for_global_readonly_superuser=True)
    @nickname("getRepoSignatures")
    @disallow_for_app_repositories
    def get(self, namespace, repository):
        """
        Fetches the list of signed tags for the repository.
        """
        if not model.is_trust_enabled(namespace, repository):
            raise NotFound()

        return {"delegations": tuf_metadata_api.get_all_tags_with_expiration(namespace, repository)}
