"""
Implementation of data interface for organization mirror worker.

Wraps data/model/org_mirror.py to provide worker-specific interface.
"""

from data.model import org_mirror
from workers.orgmirrorworker.models_interface import OrgMirrorWorkerDataInterface


class OrgMirrorWorkerDataInterfaceImpl(OrgMirrorWorkerDataInterface):
    """
    Concrete implementation of data interface using data.model.org_mirror.
    """

    def orgs_to_mirror(self, start_token=None):
        """
        Return iterator of organization mirrors ready to sync.

        Args:
            start_token: Optional OrgMirrorToken for pagination

        Returns:
            Tuple of (iterator, next_token) or (None, None) if no work
        """
        return org_mirror.orgs_to_mirror(start_token=start_token)

    def get_discovered_repos(self, org_mirror_config, status=None):
        """
        Query discovered repositories for an organization mirror.

        Args:
            org_mirror_config: OrgMirrorConfig instance
            status: Optional OrgMirrorRepoStatus to filter by

        Returns:
            List of OrgMirrorRepo objects
        """
        return org_mirror.get_discovered_repos(org_mirror_config, status=status)

    def repos_to_create(self, org_mirror_config):
        """
        Get repositories ready for creation.

        Args:
            org_mirror_config: OrgMirrorConfig instance

        Returns:
            List of OrgMirrorRepo objects with DISCOVERED or PENDING_SYNC status
        """
        return org_mirror.repos_to_create(org_mirror_config)


# Default instance
org_mirror_model = OrgMirrorWorkerDataInterfaceImpl()
