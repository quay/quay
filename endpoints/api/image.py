"""
List and lookup repository images.
"""
import json

from collections import defaultdict
from datetime import datetime

from app import storage
from data.registry_model import registry_model
from endpoints.api import (
    resource,
    nickname,
    require_repo_read,
    RepositoryParamResource,
    path_param,
    disallow_for_app_repositories,
    format_date,
    deprecated,
)
from endpoints.exception import NotFound


def image_dict(image):
    parsed_command = None
    if image.command:
        try:
            parsed_command = json.loads(image.command)
        except (ValueError, TypeError):
            parsed_command = {"error": "Could not parse command"}

    image_data = {
        "id": image.docker_image_id,
        "created": format_date(image.created),
        "comment": image.comment,
        "command": parsed_command,
        "size": image.image_size,
        "uploading": False,
        "sort_index": 0,
    }

    image_data["ancestors"] = "/{0}/".format("/".join(image.ancestor_ids))
    return image_data


@resource("/v1/repository/<apirepopath:repository>/image/")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
class RepositoryImageList(RepositoryParamResource):
    """
    Resource for listing repository images.
    """

    @require_repo_read
    @nickname("listRepositoryImages")
    @disallow_for_app_repositories
    @deprecated()
    def get(self, namespace, repository):
        """
        List the images for the specified repository.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        tags = registry_model.list_all_active_repository_tags(repo_ref)
        images_with_tags = defaultdict(list)
        for tag in tags:
            legacy_image_id = tag.manifest.legacy_image_root_id
            if legacy_image_id is not None:
                images_with_tags[legacy_image_id].append(tag)

        # NOTE: This is replicating our older response for this endpoint, but
        # returns empty for the metadata fields. This is to ensure back-compat
        # for callers still using the deprecated API, while not having to load
        # all the manifests from storage.
        return {
            "images": [
                {
                    "id": image_id,
                    "created": format_date(
                        datetime.utcfromtimestamp((min([tag.lifetime_start_ts for tag in tags])))
                    ),
                    "comment": "",
                    "command": "",
                    "size": 0,
                    "uploading": False,
                    "sort_index": 0,
                    "tags": [tag.name for tag in tags],
                    "ancestors": "",
                }
                for image_id, tags in images_with_tags.items()
            ]
        }


@resource("/v1/repository/<apirepopath:repository>/image/<image_id>")
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("image_id", "The Docker image ID")
class RepositoryImage(RepositoryParamResource):
    """
    Resource for handling repository images.
    """

    @require_repo_read
    @nickname("getImage")
    @disallow_for_app_repositories
    @deprecated()
    def get(self, namespace, repository, image_id):
        """
        Get the information available for the specified image.
        """
        repo_ref = registry_model.lookup_repository(namespace, repository)
        if repo_ref is None:
            raise NotFound()

        image = registry_model.get_legacy_image(repo_ref, image_id, storage)
        if image is None:
            raise NotFound()

        return image_dict(image)
