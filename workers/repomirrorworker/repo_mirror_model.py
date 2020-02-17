from math import log10

from data.model.repo_mirror import (
    get_eligible_mirrors,
    get_max_id_for_repo_mirror_config,
    get_min_id_for_repo_mirror_config,
)
from data.database import RepoMirrorConfig
from util.migrate.allocator import yield_random_entries

from workers.repomirrorworker.models_interface import RepoMirrorToken, RepoMirrorWorkerDataInterface


class RepoMirrorModel(RepoMirrorWorkerDataInterface):
    def repositories_to_mirror(self, start_token=None):
        def batch_query():
            return get_eligible_mirrors()

        # Find the minimum ID.
        if start_token is not None:
            min_id = start_token.min_id
        else:
            min_id = get_min_id_for_repo_mirror_config()

        # Get the ID of the last repository mirror config. Will be None if there are none in the database.
        max_id = get_max_id_for_repo_mirror_config()
        if max_id is None:
            return (None, None)

        if min_id is None or min_id > max_id:
            return (None, None)

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        iterator = yield_random_entries(
            batch_query, RepoMirrorConfig.id, batch_size, max_id, min_id
        )

        return (iterator, RepoMirrorToken(max_id + 1))


repo_mirror_model = RepoMirrorModel()
