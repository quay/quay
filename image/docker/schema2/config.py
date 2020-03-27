"""
Implements validation and conversion for the Schema2 config JSON.

Example:
{
  "architecture": "amd64",
  "config": {
    "Hostname": "",
    "Domainname": "",
    "User": "",
    "AttachStdin": false,
    "AttachStdout": false,
    "AttachStderr": false,
    "Tty": false,
    "OpenStdin": false,
    "StdinOnce": false,
    "Env": [
      "HTTP_PROXY=http:\/\/localhost:8080",
      "http_proxy=http:\/\/localhost:8080",
      "PATH=\/usr\/local\/sbin:\/usr\/local\/bin:\/usr\/sbin:\/usr\/bin:\/sbin:\/bin"
    ],
    "Cmd": [
      "sh"
    ],
    "Image": "",
    "Volumes": null,
    "WorkingDir": "",
    "Entrypoint": null,
    "OnBuild": null,
    "Labels": {

    }
  },
  "container": "b7a43694b435c8e9932615643f61f975a9213e453b15cd6c2a386f144a2d2de9",
  "container_config": {
    "Hostname": "b7a43694b435",
    "Domainname": "",
    "User": "",
    "AttachStdin": true,
    "AttachStdout": true,
    "AttachStderr": true,
    "Tty": true,
    "OpenStdin": true,
    "StdinOnce": true,
    "Env": [
      "HTTP_PROXY=http:\/\/localhost:8080",
      "http_proxy=http:\/\/localhost:8080",
      "PATH=\/usr\/local\/sbin:\/usr\/local\/bin:\/usr\/sbin:\/usr\/bin:\/sbin:\/bin"
    ],
    "Cmd": [
      "sh"
    ],
    "Image": "somenamespace\/somerepo",
    "Volumes": null,
    "WorkingDir": "",
    "Entrypoint": null,
    "OnBuild": null,
    "Labels": {

    }
  },
  "created": "2018-04-16T10:41:19.079522722Z",
  "docker_version": "17.09.0-ce",
  "history": [
    {
      "created": "2018-04-03T18:37:09.284840891Z",
      "created_by": "\/bin\/sh -c #(nop) ADD file:9e4ca21cbd24dc05b454b6be21c7c639216ae66559b21ba24af0d665c62620dc in \/ "
    },
    {
      "created": "2018-04-03T18:37:09.613317719Z",
      "created_by": "\/bin\/sh -c #(nop)  CMD [\"sh\"]",
      "empty_layer": true
    },
    {
      "created": "2018-04-16T10:37:44.418262777Z",
      "created_by": "sh"
    },
    {
      "created": "2018-04-16T10:41:19.079522722Z",
      "created_by": "sh"
    }
  ],
  "os": "linux",
  "rootfs": {
    "type": "layers",
    "diff_ids": [
      "sha256:3e596351c689c8827a3c9635bc1083cff17fa4a174f84f0584bd0ae6f384195b",
      "sha256:4552be273c71275a88de0b8c8853dcac18cb74d5790f5383d9b38d4ac55062d5",
      "sha256:1319c76152ca37fbeb7fb71e0ffa7239bc19ffbe3b95c00417ece39d89d06e6e"
    ]
  }
}
"""

import copy
import json
import hashlib

from collections import namedtuple
from jsonschema import validate as validate_schema, ValidationError
from dateutil.parser import parse as parse_date

from digest import digest_tools
from image.shared import ManifestException
from util.bytes import Bytes


DOCKER_SCHEMA2_CONFIG_HISTORY_KEY = "history"
DOCKER_SCHEMA2_CONFIG_ROOTFS_KEY = "rootfs"
DOCKER_SCHEMA2_CONFIG_CREATED_KEY = "created"
DOCKER_SCHEMA2_CONFIG_CREATED_BY_KEY = "created_by"
DOCKER_SCHEMA2_CONFIG_COMMENT_KEY = "comment"
DOCKER_SCHEMA2_CONFIG_AUTHOR_KEY = "author"
DOCKER_SCHEMA2_CONFIG_EMPTY_LAYER_KEY = "empty_layer"
DOCKER_SCHEMA2_CONFIG_TYPE_KEY = "type"


LayerHistory = namedtuple(
    "LayerHistory",
    ["created", "created_datetime", "command", "is_empty", "author", "comment", "raw_entry"],
)


class MalformedSchema2Config(ManifestException):
    """
    Raised when a config fails an assertion that should be true according to the Docker Manifest
    v2.2 Config Specification.
    """

    pass


class DockerSchema2Config(object):
    METASCHEMA = {
        "type": "object",
        "description": "The container configuration found in a schema 2 manifest",
        "required": [DOCKER_SCHEMA2_CONFIG_HISTORY_KEY, DOCKER_SCHEMA2_CONFIG_ROOTFS_KEY],
        "properties": {
            DOCKER_SCHEMA2_CONFIG_HISTORY_KEY: {
                "type": "array",
                "description": "The history used to create the container image",
                "items": {
                    "type": "object",
                    "properties": {
                        DOCKER_SCHEMA2_CONFIG_EMPTY_LAYER_KEY: {
                            "type": "boolean",
                            "description": "If present, this layer is empty",
                        },
                        DOCKER_SCHEMA2_CONFIG_CREATED_KEY: {
                            "type": "string",
                            "description": "The date/time that the layer was created",
                            "format": "date-time",
                            "x-example": "2018-04-03T18:37:09.284840891Z",
                        },
                        DOCKER_SCHEMA2_CONFIG_CREATED_BY_KEY: {
                            "type": "string",
                            "description": "The command used to create the layer",
                            "x-example": "\/bin\/sh -c #(nop) ADD file:somesha in /",
                        },
                        DOCKER_SCHEMA2_CONFIG_COMMENT_KEY: {
                            "type": "string",
                            "description": "Comment describing the layer",
                        },
                        DOCKER_SCHEMA2_CONFIG_AUTHOR_KEY: {
                            "type": "string",
                            "description": "The author of the layer",
                        },
                    },
                    "additionalProperties": True,
                },
            },
            DOCKER_SCHEMA2_CONFIG_ROOTFS_KEY: {
                "type": "object",
                "description": "Describes the root filesystem for this image",
                "properties": {
                    DOCKER_SCHEMA2_CONFIG_TYPE_KEY: {
                        "type": "string",
                        "description": "The type of the root file system entries",
                    },
                },
                "required": [DOCKER_SCHEMA2_CONFIG_TYPE_KEY],
                "additionalProperties": True,
            },
        },
        "additionalProperties": True,
    }

    def __init__(self, config_bytes, skip_validation_for_testing=False):
        assert isinstance(config_bytes, Bytes)

        self._config_bytes = config_bytes

        try:
            self._parsed = json.loads(config_bytes.as_unicode())
        except ValueError as ve:
            raise MalformedSchema2Config("malformed config data: %s" % ve)

        if not skip_validation_for_testing:
            try:
                validate_schema(self._parsed, DockerSchema2Config.METASCHEMA)
            except ValidationError as ve:
                raise MalformedSchema2Config("config data does not match schema: %s" % ve)

    @property
    def digest(self):
        """
        Returns the digest of this config object.
        """
        return digest_tools.sha256_digest(self._config_bytes.as_encoded_str())

    @property
    def size(self):
        """
        Returns the size of this config object.
        """
        return len(self._config_bytes.as_encoded_str())

    @property
    def bytes(self):
        """
        Returns the bytes of this config object.
        """
        return self._config_bytes

    @property
    def labels(self):
        """
        Returns a dictionary of all the labels defined in this configuration.
        """
        return self._parsed.get("config", {}).get("Labels", {}) or {}

    @property
    def has_empty_layer(self):
        """
        Returns whether this config contains an empty layer.
        """
        for history_entry in self._parsed[DOCKER_SCHEMA2_CONFIG_HISTORY_KEY]:
            if history_entry.get(DOCKER_SCHEMA2_CONFIG_EMPTY_LAYER_KEY, False):
                return True

        return False

    @property
    def history(self):
        """
        Returns the history of the image, started at the base layer.
        """
        for history_entry in self._parsed[DOCKER_SCHEMA2_CONFIG_HISTORY_KEY]:
            created_datetime_str = history_entry.get(DOCKER_SCHEMA2_CONFIG_CREATED_KEY)
            created_datetime = parse_date(created_datetime_str) if created_datetime_str else None
            yield LayerHistory(
                created_datetime=created_datetime,
                created=history_entry.get(DOCKER_SCHEMA2_CONFIG_CREATED_KEY),
                command=history_entry.get(DOCKER_SCHEMA2_CONFIG_CREATED_BY_KEY),
                author=history_entry.get(DOCKER_SCHEMA2_CONFIG_AUTHOR_KEY),
                comment=history_entry.get(DOCKER_SCHEMA2_CONFIG_COMMENT_KEY),
                is_empty=history_entry.get(DOCKER_SCHEMA2_CONFIG_EMPTY_LAYER_KEY, False),
                raw_entry=history_entry,
            )

    def build_v1_compatibility(self, history, v1_id, v1_parent_id, is_leaf, compressed_size=None):
        """
        Builds the V1 compatibility block for the given layer.
        """
        # If the layer is the leaf, it gets the full config (minus 2 fields). Otherwise, it gets only
        # IDs.
        v1_compatibility = copy.deepcopy(self._parsed) if is_leaf else {}
        v1_compatibility["id"] = v1_id
        if v1_parent_id is not None:
            v1_compatibility["parent"] = v1_parent_id

        if "created" not in v1_compatibility and history.created:
            v1_compatibility["created"] = history.created

        if "author" not in v1_compatibility and history.author:
            v1_compatibility["author"] = history.author

        if "comment" not in v1_compatibility and history.comment:
            v1_compatibility["comment"] = history.comment

        if "throwaway" not in v1_compatibility and history.is_empty:
            v1_compatibility["throwaway"] = True

        if "container_config" not in v1_compatibility:
            v1_compatibility["container_config"] = {
                "Cmd": [history.command],
            }

        if compressed_size is not None:
            v1_compatibility["Size"] = compressed_size

        # The history and rootfs keys are schema2-config specific.
        v1_compatibility.pop(DOCKER_SCHEMA2_CONFIG_HISTORY_KEY, None)
        v1_compatibility.pop(DOCKER_SCHEMA2_CONFIG_ROOTFS_KEY, None)
        return v1_compatibility
