from collections import namedtuple
from datetime import datetime

import cnr.semver

from cnr.exception import raise_package_not_found, raise_channel_not_found, CnrException

import features
import data.model

from app import app, storage, authentication, model_cache
from data import appr_model
from data import model as data_model
from data.cache import cache_key
from data.database import Repository, MediaType, db_transaction
from data.appr_model.models import NEW_MODELS
from endpoints.appr.models_interface import (
    ApplicationManifest,
    ApplicationRelease,
    ApplicationSummaryView,
    AppRegistryDataInterface,
    BlobDescriptor,
    ChannelView,
    ChannelReleasesView,
)
from util.audit import track_and_log
from util.morecollections import AttrDict
from util.names import parse_robot_username


class ReadOnlyException(CnrException):
    status_code = 405
    errorcode = "read-only"


def _strip_sha256_header(digest):
    if digest.startswith("sha256:"):
        return digest.split("sha256:")[1]
    return digest


def _split_package_name(package):
    """
    Returns the namespace and package-name.
    """
    return package.split("/")


def _join_package_name(ns, name):
    """
    Returns a app-name in the 'namespace/name' format.
    """
    return "%s/%s" % (ns, name)


def _timestamp_to_iso(timestamp, in_ms=True):
    if in_ms:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp).isoformat()


def _application(package):
    ns, name = _split_package_name(package)
    repo = data.model.repository.get_app_repository(ns, name)
    if repo is None:
        raise_package_not_found(package)
    return repo


class CNRAppModel(AppRegistryDataInterface):
    def __init__(self, models_ref, is_readonly):
        self.models_ref = models_ref
        self.is_readonly = is_readonly

    def log_action(
        self,
        event_name,
        namespace_name,
        repo_name=None,
        analytics_name=None,
        analytics_sample=1,
        metadata=None,
    ):
        metadata = {} if metadata is None else metadata

        repo = None
        if repo_name is not None:
            db_repo = data.model.repository.get_repository(
                namespace_name, repo_name, kind_filter="application"
            )
            repo = AttrDict(
                {
                    "id": db_repo.id,
                    "name": db_repo.name,
                    "namespace_name": db_repo.namespace_user.username,
                    "is_free_namespace": db_repo.namespace_user.stripe_id is None,
                }
            )
        track_and_log(
            event_name,
            repo,
            analytics_name=analytics_name,
            analytics_sample=analytics_sample,
            **metadata,
        )

    def list_applications(
        self, namespace=None, media_type=None, search=None, username=None, with_channels=False
    ):
        """
        Lists all repositories that contain applications, with optional filtering to a specific
        namespace and view a specific user.
        """
        limit = app.config.get("APP_REGISTRY_RESULTS_LIMIT", 50)
        namespace_whitelist = app.config.get("APP_REGISTRY_PACKAGE_LIST_CACHE_WHITELIST", [])

        # NOTE: This caching only applies for the super-large and commonly requested results
        # sets.
        if (
            namespace is not None
            and namespace in namespace_whitelist
            and media_type is None
            and search is None
            and username is None
            and not with_channels
        ):

            def _list_applications():
                return [
                    found._asdict()
                    for found in self._list_applications(namespace=namespace, limit=limit)
                ]

            apps_cache_key = cache_key.for_appr_applications_list(namespace, limit)
            return [
                ApplicationSummaryView(**found)
                for found in model_cache.retrieve(apps_cache_key, _list_applications)
            ]
        else:
            return self._list_applications(
                namespace, media_type, search, username, with_channels, limit=limit
            )

    def _list_applications(
        self,
        namespace=None,
        media_type=None,
        search=None,
        username=None,
        with_channels=False,
        limit=None,
    ):
        limit = limit or app.config.get("APP_REGISTRY_RESULTS_LIMIT", 50)
        views = []
        for repo in appr_model.package.list_packages_query(
            self.models_ref, namespace, media_type, search, username=username, limit=limit
        ):
            tag_set_prefetch = getattr(repo, self.models_ref.tag_set_prefetch_name)
            releases = [t.name for t in tag_set_prefetch]
            if not releases:
                continue
            available_releases = [
                str(x) for x in sorted(cnr.semver.versions(releases, False), reverse=True)
            ]
            channels = None
            if with_channels:
                channels = [
                    ChannelView(name=chan.name, current=chan.linked_tag.name)
                    for chan in appr_model.channel.get_repo_channels(repo, self.models_ref)
                ]

            app_name = _join_package_name(repo.namespace_user.username, repo.name)
            manifests = self.list_manifests(app_name, available_releases[0])
            view = ApplicationSummaryView(
                namespace=repo.namespace_user.username,
                name=app_name,
                visibility=data_model.repository.repository_visibility_name(repo),
                default=available_releases[0],
                channels=channels,
                manifests=manifests,
                releases=available_releases,
                updated_at=_timestamp_to_iso(tag_set_prefetch[-1].lifetime_start),
                created_at=_timestamp_to_iso(tag_set_prefetch[0].lifetime_start),
            )
            views.append(view)

        return views

    def application_is_public(self, package_name):
        """
        Returns:
          * True if the repository is public
        """
        namespace, name = _split_package_name(package_name)
        return data.model.repository.repository_is_public(namespace, name)

    def create_application(self, package_name, visibility, owner):
        """
        Create a new app repository, owner is the user who creates it.
        """
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        ns, name = _split_package_name(package_name)
        data.model.repository.create_repository(ns, name, owner, visibility, "application")

    def application_exists(self, package_name):
        """
        Create a new app repository, owner is the user who creates it.
        """
        ns, name = _split_package_name(package_name)
        return data.model.repository.get_repository(ns, name, kind_filter="application") is not None

    def basic_search(self, query, username=None):
        """Returns an array of matching AppRepositories in the format: 'namespace/name'
        Note:
          * Only 'public' repositories are returned

        Todo:
          * Filter results with readeable reposistory for the user (including visibilitys)
        """
        limit = app.config.get("APP_REGISTRY_RESULTS_LIMIT", 50)
        return [
            _join_package_name(r.namespace_user.username, r.name)
            for r in data.model.repository.get_app_search(
                lookup=query, username=username, limit=limit
            )
        ]

    def list_releases(self, package_name, media_type=None):
        """Return the list of all releases of an Application
        Example:
            >>> get_app_releases('ant31/rocketchat')
            ['1.7.1', '1.7.0', '1.7.2']

        Todo:
          * Paginate
        """
        return appr_model.release.get_releases(
            _application(package_name), self.models_ref, media_type
        )

    def list_manifests(self, package_name, release=None):
        """
        Returns the list of all manifests of an Application.

        Todo:
          * Paginate
        """
        try:
            repo = _application(package_name)
            return list(appr_model.manifest.get_manifest_types(repo, self.models_ref, release))
        except (Repository.DoesNotExist, self.models_ref.Tag.DoesNotExist):
            raise_package_not_found(package_name, release)

    def fetch_release(self, package_name, release, media_type):
        """
        Retrieves an AppRelease from it's repository-name and release-name.
        """
        repo = _application(package_name)
        try:
            tag, manifest, blob = appr_model.release.get_app_release(
                repo, release, media_type, self.models_ref
            )
            created_at = _timestamp_to_iso(tag.lifetime_start)

            blob_descriptor = BlobDescriptor(
                digest=_strip_sha256_header(blob.digest),
                mediaType=blob.media_type.name,
                size=blob.size,
                urls=[],
            )

            app_manifest = ApplicationManifest(
                digest=manifest.digest, mediaType=manifest.media_type.name, content=blob_descriptor
            )

            app_release = ApplicationRelease(
                release=tag.name, created_at=created_at, name=package_name, manifest=app_manifest
            )
            return app_release
        except (
            self.models_ref.Tag.DoesNotExist,
            self.models_ref.Manifest.DoesNotExist,
            self.models_ref.Blob.DoesNotExist,
            Repository.DoesNotExist,
            MediaType.DoesNotExist,
        ):
            raise_package_not_found(package_name, release, media_type)

    def store_blob(self, cnrblob, content_media_type):
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        fp = cnrblob.packager.io_file
        path = cnrblob.upload_url(cnrblob.digest)
        locations = storage.preferred_locations
        storage.stream_write(locations, path, fp, "application/x-gzip")
        db_blob = appr_model.blob.get_or_create_blob(
            cnrblob.digest, cnrblob.size, content_media_type, locations, self.models_ref
        )
        return BlobDescriptor(
            mediaType=content_media_type,
            digest=_strip_sha256_header(db_blob.digest),
            size=db_blob.size,
            urls=[],
        )

    def create_release(self, package, user, visibility, force=False):
        """
        Add an app-release to a repository package is an instance of data.cnr.package.Package.
        """
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        manifest = package.manifest()
        ns, name = package.namespace, package.name
        repo = data.model.repository.get_or_create_repository(
            ns, name, user, visibility=visibility, repo_kind="application"
        )
        tag_name = package.release
        appr_model.release.create_app_release(
            repo,
            tag_name,
            package.manifest(),
            manifest["content"]["digest"],
            self.models_ref,
            force,
        )

    def delete_release(self, package_name, release, media_type):
        """
        Remove/Delete an app-release from an app-repository.

        It does not delete the entire app-repository, only a single release
        """
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        repo = _application(package_name)
        try:
            appr_model.release.delete_app_release(repo, release, media_type, self.models_ref)
        except (
            self.models_ref.Channel.DoesNotExist,
            self.models_ref.Tag.DoesNotExist,
            MediaType.DoesNotExist,
        ):
            raise_package_not_found(package_name, release, media_type)

    def release_exists(self, package, release):
        """
        Return true if a release with that name already exist or have existed (include deleted ones)
        """
        # TODO: Figure out why this isn't implemented.

    def channel_exists(self, package_name, channel_name):
        """
        Returns true if channel exists.
        """
        repo = _application(package_name)
        return appr_model.tag.tag_exists(repo, channel_name, self.models_ref, "channel")

    def delete_channel(self, package_name, channel_name):
        """Delete an AppChannel
        Note:
          It doesn't delete the AppReleases
        """
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        repo = _application(package_name)
        try:
            appr_model.channel.delete_channel(repo, channel_name, self.models_ref)
        except (self.models_ref.Channel.DoesNotExist, self.models_ref.Tag.DoesNotExist):
            raise_channel_not_found(package_name, channel_name)

    def list_channels(self, package_name):
        """
        Returns all AppChannel for a package.
        """
        repo = _application(package_name)
        channels = appr_model.channel.get_repo_channels(repo, self.models_ref)
        return [ChannelView(name=chan.name, current=chan.linked_tag.name) for chan in channels]

    def fetch_channel(self, package_name, channel_name, with_releases=True):
        """
        Returns an AppChannel.
        """
        repo = _application(package_name)

        try:
            channel = appr_model.channel.get_channel(repo, channel_name, self.models_ref)
        except (self.models_ref.Channel.DoesNotExist, self.models_ref.Tag.DoesNotExist):
            raise_channel_not_found(package_name, channel_name)

        if with_releases:
            releases = appr_model.channel.get_channel_releases(repo, channel, self.models_ref)
            chanview = ChannelReleasesView(
                current=channel.linked_tag.name,
                name=channel.name,
                releases=[channel.linked_tag.name] + [c.name for c in releases],
            )
        else:
            chanview = ChannelView(current=channel.linked_tag.name, name=channel.name)

        return chanview

    def list_release_channels(self, package_name, release, active=True):
        repo = _application(package_name)
        try:
            channels = appr_model.channel.get_tag_channels(
                repo, release, self.models_ref, active=active
            )
            return [ChannelView(name=c.name, current=release) for c in channels]
        except (self.models_ref.Channel.DoesNotExist, self.models_ref.Tag.DoesNotExist):
            raise_package_not_found(package_name, release)

    def update_channel(self, package_name, channel_name, release):
        """Append a new release to the AppChannel
        Returns:
          A new AppChannel with the release
        """
        if self.is_readonly:
            raise ReadOnlyException("Currently in read-only mode")

        repo = _application(package_name)
        channel = appr_model.channel.create_or_update_channel(
            repo, channel_name, release, self.models_ref
        )
        return ChannelView(current=channel.linked_tag.name, name=channel.name)

    def get_blob_locations(self, digest):
        return appr_model.blob.get_blob_locations(digest, self.models_ref)


# Phase 3: Read and write from new tables.
model = CNRAppModel(NEW_MODELS, features.READONLY_APP_REGISTRY)
