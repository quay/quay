"""
Implements validation and conversion for the OCI config JSON.

See: https://github.com/opencontainers/image-spec/blob/master/config.md

Example:
{
    "created": "2015-10-31T22:22:56.015925234Z",
    "author": "Alyssa P. Hacker <alyspdev@example.com>",
    "architecture": "amd64",
    "os": "linux",
    "config": {
        "User": "alice",
        "ExposedPorts": {
            "8080/tcp": {}
        },
        "Env": [
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "FOO=oci_is_a",
            "BAR=well_written_spec"
        ],
        "Entrypoint": [
            "/bin/my-app-binary"
        ],
        "Cmd": [
            "--foreground",
            "--config",
            "/etc/my-app.d/default.cfg"
        ],
        "Volumes": {
            "/var/job-result-data": {},
            "/var/log/my-app-logs": {}
        },
        "WorkingDir": "/home/alice",
        "Labels": {
            "com.example.project.git.url": "https://example.com/project.git",
            "com.example.project.git.commit": "45a939b2999782a3f005621a8d0f29aa387e1d6b"
        }
    },
    "rootfs": {
      "diff_ids": [
        "sha256:c6f988f4874bb0add23a778f753c65efe992244e148a1d2ec2a8b664fb66bbd1",
        "sha256:5f70bf18a086007016e948b04aed3b82103a36bea41755b6cddfaf10ace3c6ef"
      ],
      "type": "layers"
    },
    "history": [
      {
        "created": "2015-10-31T22:22:54.690851953Z",
        "created_by": "/bin/sh -c #(nop) ADD file:a3bc1e842b69636f9df5256c49c5374fb4eef1e281fe3f282c65fb853ee171c5 in /"
      },
      {
        "created": "2015-10-31T22:22:55.613815829Z",
        "created_by": "/bin/sh -c #(nop) CMD [\"sh\"]",
        "empty_layer": true
      }
    ]
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


CONFIG_HISTORY_KEY = "history"
CONFIG_ROOTFS_KEY = "rootfs"
CONFIG_CREATED_KEY = "created"
CONFIG_CREATED_BY_KEY = "created_by"
CONFIG_COMMENT_KEY = "comment"
CONFIG_AUTHOR_KEY = "author"
CONFIG_EMPTY_LAYER_KEY = "empty_layer"
CONFIG_TYPE_KEY = "type"
CONFIG_ARCHITECTURE_KEY = "architecture"
CONFIG_OS_KEY = "os"
CONFIG_CONFIG_KEY = "config"
CONFIG_DIFF_IDS_KEY = "diff_ids"


LayerHistory = namedtuple(
    "LayerHistory",
    ["created", "created_datetime", "command", "is_empty", "author", "comment", "raw_entry"],
)


class MalformedConfig(ManifestException):
    """
    Raised when a config fails an assertion that should be true according to the
    OCI Config Specification.
    """

    pass


class OCIConfig(object):
    METASCHEMA = {
        "type": "object",
        "description": "The container configuration found in an OCI manifest",
        "required": [CONFIG_ROOTFS_KEY, CONFIG_ARCHITECTURE_KEY, CONFIG_OS_KEY],
        "properties": {
            CONFIG_CREATED_KEY: {
                "type": "string",
                "description": "An combined date and time at which the image was created, formatted as defined by RFC 3339, section 5.6.",
            },
            CONFIG_AUTHOR_KEY: {
                "type": "string",
                "description": "Gives the name and/or email address of the person or entity which created and is responsible for maintaining the image.",
            },
            CONFIG_ARCHITECTURE_KEY: {
                "type": "string",
                "description": "The CPU architecture which the binaries in this image are built to run on. Configurations SHOULD use, and implementations SHOULD understand, values listed in the Go Language document for GOARCH.",
            },
            CONFIG_OS_KEY: {
                "type": "string",
                "description": "The name of the operating system which the image is built to run on. Configurations SHOULD use, and implementations SHOULD understand, values listed in the Go Language document for GOOS.",
            },
            CONFIG_CONFIG_KEY: {
                "type": ["object", "null"],
                "description": "The execution parameters which SHOULD be used as a base when running a container using the image",
                "properties": {
                    "User": {"type": "string"},
                    "ExposedPorts": {"type": "object"},
                    "Env": {"type": "array"},
                    "Entrypoint": {"type": "array"},
                    "Cmd": {"type": "array"},
                    "Volumes": {"type": "object"},
                    "WorkingDir": {"type": "string"},
                    "Labels": {"type": "object"},
                    "StopSignal": {"type": "string"},
                },
                "additionalProperties": True,
            },
            CONFIG_ROOTFS_KEY: {
                "type": "object",
                "description": "Describes the root filesystem for this image",
                "properties": {
                    CONFIG_TYPE_KEY: {
                        "type": "string",
                        "description": "MUST be set to layers.",
                        "enum": ["layers"],
                    },
                    CONFIG_DIFF_IDS_KEY: {
                        "type": "array",
                        "description": "An array of layer content hashes (DiffIDs), in order from first to last.",
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "required": [CONFIG_TYPE_KEY, CONFIG_DIFF_IDS_KEY],
                "additionalProperties": True,
            },
            CONFIG_HISTORY_KEY: {
                "type": "array",
                "description": "Describes the history of each layer. The array is ordered from first to last",
                "items": {
                    "type": "object",
                    "properties": {
                        CONFIG_EMPTY_LAYER_KEY: {
                            "type": "boolean",
                            "description": "If present, this layer is empty",
                        },
                        CONFIG_CREATED_KEY: {
                            "type": "string",
                            "description": "The date/time that the layer was created",
                            "format": "date-time",
                            "x-example": "2018-04-03T18:37:09.284840891Z",
                        },
                        CONFIG_CREATED_BY_KEY: {
                            "type": "string",
                            "description": "The command used to create the layer",
                            "x-example": "\/bin\/sh -c #(nop) ADD file:somesha in /",
                        },
                        CONFIG_COMMENT_KEY: {
                            "type": "string",
                            "description": "Comment describing the layer",
                        },
                        CONFIG_AUTHOR_KEY: {
                            "type": "string",
                            "description": "The author of the layer",
                        },
                    },
                    "additionalProperties": True,
                },
            },
        },
        "additionalProperties": True,
    }

    def __init__(self, config_bytes):
        assert isinstance(config_bytes, Bytes)

        self._config_bytes = config_bytes

        try:
            self._parsed = json.loads(config_bytes.as_unicode())
        except ValueError as ve:
            raise MalformedConfig("malformed config data: %s" % ve)

        try:
            validate_schema(self._parsed, OCIConfig.METASCHEMA)
        except ValidationError as ve:
            raise MalformedConfig("config data does not match schema: %s" % ve)

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
        history = self._parsed.get(CONFIG_HISTORY_KEY) or []
        for history_entry in history:
            if history_entry.get(CONFIG_EMPTY_LAYER_KEY, False):
                return True

        return False

    @property
    def history(self):
        """
        Returns the history of the image, started at the base layer.
        """
        history = self._parsed.get(CONFIG_HISTORY_KEY) or []
        for history_entry in history:
            created_datetime_str = history_entry.get(CONFIG_CREATED_KEY)
            created_datetime = parse_date(created_datetime_str) if created_datetime_str else None
            yield LayerHistory(
                created_datetime=created_datetime,
                created=history_entry.get(CONFIG_CREATED_KEY),
                command=history_entry.get(CONFIG_CREATED_BY_KEY),
                author=history_entry.get(CONFIG_AUTHOR_KEY),
                comment=history_entry.get(CONFIG_COMMENT_KEY),
                is_empty=history_entry.get(CONFIG_EMPTY_LAYER_KEY, False),
                raw_entry=history_entry,
            )

    @property
    def synthesized_history(self):
        created_datetime_str = self._parsed.get(CONFIG_CREATED_KEY)
        created_datetime = parse_date(created_datetime_str) if created_datetime_str else None
        config = self._parsed.get(CONFIG_CONFIG_KEY) or {}

        return LayerHistory(
            created_datetime=created_datetime,
            created=created_datetime_str,
            command=config.get("Cmd", None),
            author=self._parsed.get(CONFIG_AUTHOR_KEY, None),
            comment=None,
            is_empty=False,
            raw_entry=None,
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

        if history is not None:
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

        # The history and rootfs keys are OCI-config specific.
        v1_compatibility.pop(CONFIG_HISTORY_KEY, None)
        v1_compatibility.pop(CONFIG_ROOTFS_KEY, None)
        return v1_compatibility
