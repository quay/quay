from abc import ABCMeta, abstractmethod, abstractproperty
from six import add_metaclass

from deprecated import deprecated


@add_metaclass(ABCMeta)
class SecurityScannerInterface(object):
    """ Interface for code to work with the security scan data model. This model encapsulates
        all access when speaking to an external security scanner, as well as any data tracking
        in the database.
    """

    @abstractmethod
    def load_security_information(self, manifest_or_legacy_image, include_vulnerabilities=False):
        """ Loads the security information for the given manifest or legacy image, returning
            a SecurityInformationLookupResult structure. The manifest_or_legacy_image must be a Manifest
            or LegacyImage datatype from the registry_model.
        """

    @abstractmethod
    def perform_indexing(self, start_token=None):
        """ Performs indexing of the next set of unindexed manifests/images. If start_token is given,
            the indexing should resume from that point. Returns a new start index for the next
            iteration of indexing. The tokens returned and given are assumed to be opaque outside
            of this implementation and should not be relied upon by the caller to conform to any
            particular format.
        """

    @abstractmethod
    def register_model_cleanup_callbacks(self, data_model_config):
        """ Registers any cleanup callbacks with the data model. Typically, a callback is registered
        to remove the manifest/image from the security indexer if it has been GCed in the data model.
        """

    @abstractproperty
    @deprecated(reason="Only exposed for the legacy notification worker")
    def legacy_api_handler(self):
        """ Exposes the legacy security scan API for legacy workers that need it or None if none. """
