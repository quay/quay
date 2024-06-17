from flask import jsonify

from app import app, model_cache
from auth.registry_jwt_auth import process_registry_jwt_auth
from data.registry_model import registry_model
from endpoints.decorators import (
    anon_protect,
    disallow_for_account_recovery_mode,
    parse_repository_name,
)
from endpoints.v2 import (
    _MAX_RESULTS_PER_PAGE,
    oci_tag_paginate,
    require_repo_read,
    v2_bp,
)
from endpoints.v2.errors import NameUnknown, TooManyTagsRequested


@v2_bp.route("/<repopath:repository>/tags/list", methods=["GET"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read(allow_for_superuser=True)
@anon_protect
@oci_tag_paginate()
def list_all_tags(namespace_name, repo_name, last_pagination_tag_name, limit, pagination_callback):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown("repository not found")

    tags = []
    has_more = False

    if limit > 0:
        tags, has_more = registry_model.lookup_cached_active_repository_tags(
            model_cache, repository_ref, last_pagination_tag_name, limit
        )

    response = jsonify(
        {
            "name": f"{namespace_name}/{repo_name}",
            "tags": [tag.name for tag in tags][0:limit],
        }
    )

    if limit > 0:
        pagination_callback(tags, has_more, response)

    return response
