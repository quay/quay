from abc import ABCMeta, abstractmethod
from collections import namedtuple

from six import add_metaclass


class BlobDescriptor(namedtuple("Blob", ["mediaType", "size", "digest", "urls"])):
    """
    BlobDescriptor describes a blob with its mediatype, size and digest.

    A BlobDescriptor is used to retrieves the actual blob.
    """


class ChannelReleasesView(namedtuple("ChannelReleasesView", ["name", "current", "releases"])):
    """
    A channel is a pointer to a Release (current).

    Releases are the previous tags pointed by channel (history).
    """


class ChannelView(namedtuple("ChannelView", ["name", "current"])):
    """
    A channel is a pointer to a Release (current).
    """


class ApplicationSummaryView(
    namedtuple(
        "ApplicationSummaryView",
        [
            "name",
            "namespace",
            "visibility",
            "default",
            "manifests",
            "channels",
            "releases",
            "updated_at",
            "created_at",
        ],
    )
):
    """
    ApplicationSummaryView is an aggregated view of an application repository.
    """


class ApplicationManifest(namedtuple("ApplicationManifest", ["mediaType", "digest", "content"])):
    """
    ApplicationManifest embed the BlobDescriptor and some metadata around it.

    An ApplicationManifest is content-addressable.
    """


class ApplicationRelease(
    namedtuple("ApplicationRelease", ["release", "name", "created_at", "manifest"])
):
    """
    The ApplicationRelease associates an ApplicationManifest to a repository and release.
    """


@add_metaclass(ABCMeta)
class AppRegistryDataInterface(object):
    """
    Interface that represents all data store interactions required by a App Registry.
    """

    @abstractmethod
    def list_applications(
        self, namespace=None, media_type=None, search=None, username=None, with_channels=False
    ):
        """
        Lists all repositories that contain applications, with optional filtering to a specific
        namespace and/or to those visible to a specific user.

        Returns: list of ApplicationSummaryView
        """
        pass

    @abstractmethod
    def application_is_public(self, package_name):
        """
        Returns true if the application is public.
        """
        pass

    @abstractmethod
    def create_application(self, package_name, visibility, owner):
        """
        Create a new app repository, owner is the user who creates it.
        """
        pass

    @abstractmethod
    def application_exists(self, package_name):
        """
        Returns true if the application exists.
        """
        pass

    @abstractmethod
    def basic_search(self, query, username=None):
        """ Returns an array of matching application in the format: 'namespace/name'
    Note:
      * Only 'public' repositories are returned
    """
        pass

    # @TODO: Paginate
    @abstractmethod
    def list_releases(self, package_name, media_type=None):
        """ Returns the list of all releases(names) of an AppRepository
    Example:
        >>> get_app_releases('ant31/rocketchat')
        ['1.7.1', '1.7.0', '1.7.2']
    """
        pass

    # @TODO: Paginate
    @abstractmethod
    def list_manifests(self, package_name, release=None):
        """
        Returns the list of all available manifests type of an Application across all releases or
        for a specific one.

    Example:
        >>> get_app_releases('ant31/rocketchat')
        ['1.7.1', '1.7.0', '1.7.2']
        """
        pass

    @abstractmethod
    def fetch_release(self, package_name, release, media_type):
        """
        Returns an ApplicationRelease.
        """
        pass

    @abstractmethod
    def store_blob(self, cnrblob, content_media_type):
        """
        Upload the blob content to a storage location and creates a Blob entry in the DB.

        Returns a BlobDescriptor
        """
        pass

    @abstractmethod
    def create_release(self, package, user, visibility, force=False):
        """
        Creates and returns an ApplicationRelease.

        - package is a data.model.Package object
        - user is the owner of the package
        - visibility is a string: 'public' or 'private'
        """
        pass

    @abstractmethod
    def release_exists(self, package, release):
        """
        Return true if a release with that name already exist or has existed (including deleted
        ones)
        """
        pass

    @abstractmethod
    def delete_release(self, package_name, release, media_type):
        """
        Remove/Delete an app-release from an app-repository.

        It does not delete the entire app-repository, only a single release
        """
        pass

    @abstractmethod
    def list_release_channels(self, package_name, release, active=True):
        """
        Returns a list of Channel that are/was pointing to a release.

        If active is True, returns only active Channel (lifetime_end not null)
        """
        pass

    @abstractmethod
    def channel_exists(self, package_name, channel_name):
        """
        Returns true if the channel with the given name exists under the matching package.
        """
        pass

    @abstractmethod
    def update_channel(self, package_name, channel_name, release):
        """
        Append a new release to the Channel Returns a new Channel with the release as current.
        """
        pass

    @abstractmethod
    def delete_channel(self, package_name, channel_name):
        """
        Delete a Channel, it doesn't delete/touch the ApplicationRelease pointed by the channel.
        """

    # @TODO: Paginate
    @abstractmethod
    def list_channels(self, package_name):
        """
        Returns all AppChannel for a package.
        """
        pass

    @abstractmethod
    def fetch_channel(self, package_name, channel_name, with_releases=True):
        """ Returns an Channel
    Raises: ChannelNotFound, PackageNotFound
    """
        pass

    @abstractmethod
    def log_action(
        self,
        event_name,
        namespace_name,
        repo_name=None,
        analytics_name=None,
        analytics_sample=1,
        **kwargs,
    ):
        """
        Logs an action to the audit log.
        """
        pass

    @abstractmethod
    def get_blob_locations(self, digest):
        """
        Returns a list of strings for the locations in which a Blob is present.
        """
        pass
