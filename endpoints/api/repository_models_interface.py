from abc import ABCMeta, abstractmethod
from collections import namedtuple, defaultdict

from datetime import datetime
from six import add_metaclass

import features
from data.database import RepositoryState
from endpoints.api import format_date


class RepositoryBaseElement(
    namedtuple(
        "RepositoryBaseElement",
        [
            "namespace_name",
            "repository_name",
            "is_starred",
            "is_public",
            "kind_name",
            "description",
            "namespace_user_organization",
            "namespace_user_removed_tag_expiration_s",
            "last_modified",
            "action_count",
            "should_last_modified",
            "should_popularity",
            "should_is_starred",
            "is_free_account",
            "state",
        ],
    )
):
    """
    Repository a single quay repository.

    :type namespace_name: string
    :type repository_name: string
    :type is_starred: boolean
    :type is_public: boolean
    :type kind_name: string
    :type description: string
    :type namespace_user_organization: boolean
    :type should_last_modified: boolean
    :type should_popularity: boolean
    :type should_is_starred: boolean
    """

    def to_dict(self):
        repo = {
            "namespace": self.namespace_name,
            "name": self.repository_name,
            "description": self.description,
            "is_public": self.is_public,
            "kind": self.kind_name,
            "state": self.state.name if self.state is not None else None,
        }

        if self.should_last_modified:
            repo["last_modified"] = self.last_modified

        if self.should_popularity:
            repo["popularity"] = float(self.action_count if self.action_count else 0)

        if self.should_is_starred:
            repo["is_starred"] = self.is_starred

        return repo


class ApplicationRepository(
    namedtuple(
        "ApplicationRepository", ["repository_base_elements", "channels", "releases", "state"]
    )
):
    """
    Repository a single quay repository.

    :type repository_base_elements: RepositoryBaseElement
    :type channels: [Channel]
    :type releases: [Release]
    """

    def to_dict(self):
        repo_data = {
            "namespace": self.repository_base_elements.namespace_name,
            "name": self.repository_base_elements.repository_name,
            "kind": self.repository_base_elements.kind_name,
            "description": self.repository_base_elements.description,
            "is_public": self.repository_base_elements.is_public,
            "is_organization": self.repository_base_elements.namespace_user_organization,
            "is_starred": self.repository_base_elements.is_starred,
            "channels": [chan.to_dict() for chan in self.channels],
            "releases": [release.to_dict() for release in self.releases],
            "state": self.state.name if self.state is not None else None,
            "is_free_account": self.repository_base_elements.is_free_account,
        }

        return repo_data


class ImageRepositoryRepository(
    namedtuple(
        "NonApplicationRepository",
        ["repository_base_elements", "tags", "counts", "badge_token", "trust_enabled", "state"],
    )
):
    """
    Repository a single quay repository.

    :type repository_base_elements: RepositoryBaseElement
    :type tags: [Tag]
    :type counts: [count]
    :type badge_token: string
    :type trust_enabled: boolean
    """

    def to_dict(self):
        img_repo = {
            "namespace": self.repository_base_elements.namespace_name,
            "name": self.repository_base_elements.repository_name,
            "kind": self.repository_base_elements.kind_name,
            "description": self.repository_base_elements.description,
            "is_public": self.repository_base_elements.is_public,
            "is_organization": self.repository_base_elements.namespace_user_organization,
            "is_starred": self.repository_base_elements.is_starred,
            "status_token": self.badge_token if not self.repository_base_elements.is_public else "",
            "trust_enabled": bool(features.SIGNING) and self.trust_enabled,
            "tag_expiration_s": self.repository_base_elements.namespace_user_removed_tag_expiration_s,
            "is_free_account": self.repository_base_elements.is_free_account,
            "state": self.state.name if self.state is not None else None,
        }

        if self.tags is not None:
            img_repo["tags"] = {tag.name: tag.to_dict() for tag in self.tags}

        if self.repository_base_elements.state:
            img_repo["state"] = self.repository_base_elements.state.name

        return img_repo


class Repository(
    namedtuple(
        "Repository",
        [
            "namespace_name",
            "repository_name",
        ],
    )
):
    """
    Repository a single quay repository.

    :type namespace_name: string
    :type repository_name: string
    """


class Channel(namedtuple("Channel", ["name", "linked_tag_name", "linked_tag_lifetime_start"])):
    """
    Repository a single quay repository.

    :type name: string
    :type linked_tag_name: string
    :type linked_tag_lifetime_start: string
    """

    def to_dict(self):
        return {
            "name": self.name,
            "release": self.linked_tag_name,
            "last_modified": format_date(
                datetime.fromtimestamp(self.linked_tag_lifetime_start // 1000)
            ),
        }


class Release(namedtuple("Channel", ["name", "lifetime_start", "releases_channels_map"])):
    """
    Repository a single quay repository.

    :type name: string
    :type last_modified: string
    :type releases_channels_map: {string -> string}
    """

    def to_dict(self):
        return {
            "name": self.name,
            "last_modified": format_date(datetime.fromtimestamp(self.lifetime_start // 1000)),
            "channels": self.releases_channels_map[self.name],
        }


class Tag(
    namedtuple(
        "Tag",
        [
            "name",
            "image_docker_image_id",
            "image_aggregate_size",
            "lifetime_start_ts",
            "tag_manifest_digest",
            "lifetime_end_ts",
        ],
    )
):
    """
    :type name: string
    :type image_docker_image_id: string
    :type image_aggregate_size: int
    :type lifetime_start_ts: int
    :type lifetime_end_ts: int|None
    :type tag_manifest_digest: string

    """

    def to_dict(self):
        tag_info = {
            "name": self.name,
            "image_id": self.image_docker_image_id,
            "size": self.image_aggregate_size,
        }

        if self.lifetime_start_ts > 0:
            last_modified = format_date(datetime.fromtimestamp(self.lifetime_start_ts))
            tag_info["last_modified"] = last_modified

        if self.lifetime_end_ts:
            expiration = format_date(datetime.fromtimestamp(self.lifetime_end_ts))
            tag_info["expiration"] = expiration

        if self.tag_manifest_digest is not None:
            tag_info["manifest_digest"] = self.tag_manifest_digest

        return tag_info


class Count(namedtuple("Count", ["date", "count"])):
    """
    date: DateTime
    count: int
    """

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "count": self.count,
        }


@add_metaclass(ABCMeta)
class RepositoryDataInterface(object):
    """
    Interface that represents all data store interactions required by a Repository.
    """

    @abstractmethod
    def get_repo(self, namespace_name, repository_name, user, include_tags=True, max_tags=500):
        """
        Returns a repository.
        """

    @abstractmethod
    def repo_exists(self, namespace_name, repository_name):
        """
        Returns true if a repo exists and false if not.
        """

    @abstractmethod
    def create_repo(
        self, namespace, name, creating_user, description, visibility="private", repo_kind="image"
    ):
        """
        Returns creates a new repo.
        """

    @abstractmethod
    def get_repo_list(
        self,
        starred,
        user,
        repo_kind,
        namespace,
        username,
        public,
        page_token,
        last_modified,
        popularity,
    ):
        """
        Returns a RepositoryBaseElement.
        """

    @abstractmethod
    def set_repository_visibility(self, namespace_name, repository_name, visibility):
        """
        Sets a repository's visibility if it is found.
        """

    @abstractmethod
    def set_trust(self, namespace_name, repository_name, trust):
        """
        Sets a repository's trust_enabled field if it is found.
        """

    @abstractmethod
    def set_description(self, namespace_name, repository_name, description):
        """
        Sets a repository's description if it is found.
        """

    @abstractmethod
    def mark_repository_for_deletion(self, namespace_name, repository_name, repository_gc_queue):
        """
        Marks a repository for deletion.
        """

    @abstractmethod
    def check_repository_usage(self, user_name, plan_found):
        """
        Creates a notification for a user if they are over or under on their repository usage.
        """

    @abstractmethod
    def set_repository_state(self, namespace_name, repository_name, state):
        """
        Set the State of the Repository.
        """
