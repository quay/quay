"""
List and lookup repository images.
"""
import json

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


def image_dict(image, with_history=False, with_tags=False):
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
        "sort_index": len(image.parents),
    }

    if with_tags:
        image_data["tags"] = [tag.name for tag in image.tags]

    if with_history:
        image_data["history"] = [image_dict(parent) for parent in image.parents]

    # Calculate the ancestors string, with the DBID's replaced with the docker IDs.
    parent_docker_ids = [parent_image.docker_image_id for parent_image in image.parents]
    image_data["ancestors"] = "/{0}/".format("/".join(parent_docker_ids))
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

        images = registry_model.get_legacy_images(repo_ref)
        return {"images": [image_dict(image, with_tags=True) for image in images]}


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

        image = registry_model.get_legacy_image(repo_ref, image_id, include_parents=True)
        if image is None:
            raise NotFound()

        return image_dict(image, with_history=True)
