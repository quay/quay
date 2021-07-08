from collections import namedtuple

from flask import jsonify

import features

from app import model_cache
from auth.auth_context import get_authenticated_user, get_authenticated_context
from auth.registry_jwt_auth import process_registry_jwt_auth
from data import model
from data.cache import cache_key
from endpoints.decorators import anon_protect, disallow_for_account_recovery_mode, route_show_if
from endpoints.v2 import v2_bp, paginate


class Repository(namedtuple("Repository", ["id", "namespace_name", "name"])):
    pass


@v2_bp.route("/_catalog", methods=["GET"])
@disallow_for_account_recovery_mode
@process_registry_jwt_auth()
@anon_protect
@paginate()
def catalog_search(start_id, limit, pagination_callback):
    def _load_catalog():
        include_public = bool(features.PUBLIC_CATALOG)
        if not include_public and not get_authenticated_user():
            return []

        username = get_authenticated_user().username if get_authenticated_user() else None
        if username and not get_authenticated_user().enabled:
            return []

        query = model.repository.get_visible_repositories(
            username,
            kind_filter="image",
            include_public=include_public,
            start_id=start_id,
            limit=limit + 1,
        )
        # NOTE: The repository ID is in `rid` (not `id`) here, as per the requirements of
        # the `get_visible_repositories` call.
        return [
            Repository(repo.rid, repo.namespace_user.username, repo.name)._asdict()
            for repo in query
        ]

    context_key = get_authenticated_context().unique_key if get_authenticated_context() else None
    catalog_cache_key = cache_key.for_catalog_page(
        context_key, start_id, limit, model_cache.cache_config
    )
    visible_repositories = [
        Repository(**repo_dict)
        for repo_dict in model_cache.retrieve(catalog_cache_key, _load_catalog)
    ]

    response = jsonify(
        {
            "repositories": [
                "%s/%s" % (repo.namespace_name, repo.name) for repo in visible_repositories
            ][0:limit],
        }
    )

    pagination_callback(visible_repositories, response)
    return response
