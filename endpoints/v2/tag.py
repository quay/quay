from flask import jsonify

from app import app, model_cache
from auth.registry_jwt_auth import process_registry_jwt_auth
from data.registry_model import registry_model
from endpoints.decorators import (
    anon_protect,
    disallow_for_account_recovery_mode,
    parse_repository_name,
    route_show_if,
)
from endpoints.v2 import v2_bp, require_repo_read, paginate
from endpoints.v2.errors import NameUnknown


@v2_bp.route("/<repopath:repository>/tags/list", methods=["GET"])
@disallow_for_account_recovery_mode
@parse_repository_name()
@process_registry_jwt_auth(scopes=["pull"])
@require_repo_read
@anon_protect
@paginate()
def list_all_tags(namespace_name, repo_name, start_id, limit, pagination_callback):
    repository_ref = registry_model.lookup_repository(namespace_name, repo_name)
    if repository_ref is None:
        raise NameUnknown()

    # NOTE: We add 1 to the limit because that's how pagination_callback knows if there are
    # additional tags.
    tags = registry_model.lookup_cached_active_repository_tags(
        model_cache, repository_ref, start_id, limit + 1
    )
    response = jsonify(
        {
            "name": "{0}/{1}".format(namespace_name, repo_name),
            "tags": [tag.name for tag in tags][0:limit],
        }
    )

    pagination_callback(tags, response)
    return response
