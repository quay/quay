"""
schema2 implements pure data transformations according to the Docker Manifest v2.2 Specification.

https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-2.md
"""

# Content Types
DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE = (
    "application/vnd.docker.distribution.manifest.list.v2+json"
)

DOCKER_SCHEMA2_LAYER_CONTENT_TYPE = "application/vnd.docker.image.rootfs.diff.tar.gzip"
DOCKER_SCHEMA2_REMOTE_LAYER_CONTENT_TYPE = (
    "application/vnd.docker.image.rootfs.foreign.diff.tar.gzip"
)

DOCKER_SCHEMA2_CONFIG_CONTENT_TYPE = "application/vnd.docker.container.image.v1+json"

DOCKER_SCHEMA2_CONTENT_TYPES = {
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
}

# The magical digest to be used for "empty" layers.
# https://github.com/docker/distribution/blob/749f6afb4572201e3c37325d0ffedb6f32be8950/manifest/schema1/config_builder.go#L22
EMPTY_LAYER_BLOB_DIGEST = "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
EMPTY_LAYER_SIZE = 32
EMPTY_LAYER_BYTES = bytes(
    bytearray(
        [
            31,
            139,
            8,
            0,
            0,
            9,
            110,
            136,
            0,
            255,
            98,
            24,
            5,
            163,
            96,
            20,
            140,
            88,
            0,
            8,
            0,
            0,
            255,
            255,
            46,
            175,
            181,
            239,
            0,
            4,
            0,
            0,
        ]
    )
)
