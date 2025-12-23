"""
Data interface abstraction for organization mirror worker.

Provides abstraction layer between worker logic and data model for testability.
"""


class OrgMirrorToken:
    """
    Pagination token for organization mirror iteration.

    Used to resume processing from a specific point in the database.
    """

    def __init__(self, min_id):
        """
        Initialize token with minimum ID.

        Args:
            min_id: Minimum organization mirror config ID to start from
        """
        self.min_id = min_id


class OrgMirrorWorkerDataInterface:
    """
    Abstract interface for data access operations.

    This interface allows the worker logic to be tested with mocked data access.
    """

    def orgs_to_mirror(self, start_token=None):
        """
        Return iterator of organization mirrors ready to sync.

        Args:
            start_token: Optional OrgMirrorToken for pagination

        Returns:
            Tuple of (iterator, next_token) or (None, None) if no work
        """
        raise NotImplementedError()

    def get_discovered_repos(self, org_mirror, status=None):
        """
        Query discovered repositories for an organization mirror.

        Args:
            org_mirror: OrgMirrorConfig instance
            status: Optional OrgMirrorRepoStatus to filter by

        Returns:
            List of OrgMirrorRepo objects
        """
        raise NotImplementedError()

    def repos_to_create(self, org_mirror):
        """
        Get repositories ready for creation.

        Args:
            org_mirror: OrgMirrorConfig instance

        Returns:
            List of OrgMirrorRepo objects with DISCOVERED or PENDING_SYNC status
        """
        raise NotImplementedError()
