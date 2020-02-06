"""
v1 implements pure data transformations according to the Docker Image Specification v1.1.

https://github.com/docker/docker/blob/master/image/spec/v1.1.md
"""

from collections import namedtuple


class DockerV1Metadata(
    namedtuple(
        "DockerV1Metadata",
        [
            "namespace_name",
            "repo_name",
            "image_id",
            "checksum",
            "content_checksum",
            "created",
            "comment",
            "command",
            "author",
            "parent_image_id",
            "compat_json",
        ],
    )
):
    """
    DockerV1Metadata represents all of the metadata for a given Docker v1 Image.

    The original form of the metadata is stored in the compat_json field.
    """
