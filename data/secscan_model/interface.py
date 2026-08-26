from abc import ABCMeta, abstractmethod

from six import add_metaclass


class InvalidConfigurationException(Exception):
    """
    Exception raised when attempting to initialize a secscan model fails.
    """


@add_metaclass(ABCMeta)
class SecurityScannerReadInterface(object):
    @abstractmethod
    def load_security_information(
        self, manifest_or_legacy_image, include_vulnerabilities=False, model_cache=None
    ):
        """
        Loads the security information for the given manifest or legacy image, returning a
        SecurityInformationLookupResult structure.
        """

    @abstractmethod
    def lookup_notification_page(self, notification_id, page_index=None):
        """
        Performs the lookup of a page of results for an incoming notification from the security
        scanner.

        Returns a PaginatedNotificationResult or None if this engine doesn't support this method.
        """

    @abstractmethod
    def process_notification_page(self, page_result):
        """
        Processes the page of notification information given and yields UpdatedVulnerability's.
        """

    @abstractmethod
    def mark_notification_handled(self, notification_id):
        """
        Marks that a security notification from the scanner has been handled.
        """

    @abstractmethod
    def garbage_collect_manifest_report(self, manifest_digest):
        """
        Removes the manifest report from the security scanner when the manifest is GC'd.
        """


@add_metaclass(ABCMeta)
class SecurityScannerIndexerInterface(object):
    @abstractmethod
    def perform_indexing(self, start_token=None, batch_size=None):
        """
        Performs indexing of the next set of unindexed manifests/images.

        If start_token is given, the indexing should resume from that point. Returns a new start
        index for the next iteration of indexing. The tokens returned and given are assumed to be
        opaque outside of this implementation and should not be relied upon by the caller to conform
        to any particular format.
        """

    @abstractmethod
    def perform_indexing_recent_manifests(self, batch_size=None):
        """
        Performs indexing of a recent set of unindexed manifests/images.
        """


class SecurityScannerInterface(SecurityScannerReadInterface, SecurityScannerIndexerInterface):
    pass
