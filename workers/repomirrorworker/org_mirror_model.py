"""
Model interface for organization-level mirror worker operations.

Follows the same pattern as repo_mirror_model.py for consistent worker behavior.
"""

from collections import namedtuple
from math import log10

from data.database import OrgMirrorConfig, OrgMirrorRepository
from data.model.org_mirror import (
    get_eligible_org_mirror_configs,
    get_eligible_org_mirror_repos,
    get_max_id_for_org_mirror_config,
    get_max_id_for_org_mirror_repo,
    get_min_id_for_org_mirror_config,
    get_min_id_for_org_mirror_repo,
)
from util.migrate.allocator import yield_random_entries


class OrgMirrorConfigToken(namedtuple("NextOrgMirrorConfigToken", ["min_id"])):
    """
    OrgMirrorConfigToken represents an opaque token for the discovery phase.

    Used to continue discovery processing across worker runs.
    """


class OrgMirrorToken(namedtuple("NextOrgMirrorToken", ["min_id"])):
    """
    OrgMirrorToken represents an opaque token that can be passed between runs of the
    organization mirror worker to continue mirroring wherever the previous run left off.

    Note that the data of the token is *opaque* to the worker, and the worker
    should *not* pull any data out or modify the token in any way.
    """


class OrgMirrorModel:
    """
    Data interface for organization-level mirror worker operations.
    """

    def configs_to_discover(self, start_token=None):
        """
        Returns a tuple of (iterator, next_token) for org mirror configs ready for discovery.

        The iterator yields tuples of (OrgMirrorConfig, abort_signal, num_remaining).
        If no configs are ready, returns (None, None).

        Args:
            start_token: Optional OrgMirrorConfigToken to resume from a previous run

        Returns:
            Tuple of (iterator, OrgMirrorConfigToken) or (None, None)
        """

        def batch_query():
            return get_eligible_org_mirror_configs()

        # Find the minimum ID
        if start_token is not None:
            min_id = start_token.min_id
        else:
            min_id = get_min_id_for_org_mirror_config()

        # Get the ID of the last org mirror config
        max_id = get_max_id_for_org_mirror_config()
        if max_id is None:
            return (None, None)

        if min_id is None or min_id > max_id:
            return (None, None)

        # 4^log10(total) gives us a scalable batch size
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        iterator = yield_random_entries(batch_query, OrgMirrorConfig.id, batch_size, max_id, min_id)

        return (iterator, OrgMirrorConfigToken(max_id + 1))

    def repositories_to_mirror(self, start_token=None):
        """
        Returns a tuple of (iterator, next_token) for org mirror repositories ready to sync.

        The iterator yields tuples of (OrgMirrorRepository, abort_signal, num_remaining).
        If no repositories are ready, returns (None, None).

        Args:
            start_token: Optional OrgMirrorToken to resume from a previous run

        Returns:
            Tuple of (iterator, OrgMirrorToken) or (None, None)
        """

        def batch_query():
            return get_eligible_org_mirror_repos()

        # Find the minimum ID
        if start_token is not None:
            min_id = start_token.min_id
        else:
            min_id = get_min_id_for_org_mirror_repo()

        # Get the ID of the last org mirror repo. Will be None if there are none in the database.
        max_id = get_max_id_for_org_mirror_repo()
        if max_id is None:
            return (None, None)

        if min_id is None or min_id > max_id:
            return (None, None)

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        iterator = yield_random_entries(
            batch_query, OrgMirrorRepository.id, batch_size, max_id, min_id
        )

        return (iterator, OrgMirrorToken(max_id + 1))


org_mirror_model = OrgMirrorModel()
