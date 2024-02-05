import datetime
import json
from contextlib import nullcontext as does_not_raise

import pytest
from dateutil.tz import tzutc

from image.oci import (
    ADDITIONAL_LAYER_CONTENT_TYPES,
    ALLOWED_ARTIFACT_TYPES,
    OCI_IMAGE_CONFIG_CONTENT_TYPE,
    register_artifact_type,
)
from image.oci.config import LayerHistory, MalformedConfig, OCIConfig
from util.bytes import Bytes

SAMPLE_CONFIG = """{
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
        "Cmd": null,
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
        "created_by": "/bin/sh -c #(nop) CMD [\\"sh\\"]",
        "empty_layer": true
      }
    ]
}"""


def test_parse_basic_config():
    config = OCIConfig(Bytes.for_string_or_unicode(SAMPLE_CONFIG))
    assert (
        config.digest == "sha256:c692ed232a0d8a30ba61f3f90e6e3113af36932e0e0ee9d88626f84fe1e348c2"
    )
    assert config.size == 1483

    history = list(config.history)
    assert config.has_empty_layer
    assert len(history) == 2

    expected = [
        LayerHistory(
            created="2015-10-31T22:22:54.690851953Z",
            created_datetime=datetime.datetime(2015, 10, 31, 22, 22, 54, 690851, tzinfo=tzutc()),
            command="/bin/sh -c #(nop) ADD file:a3bc1e842b69636f9df5256c49c5374fb4eef1e281fe3f282c65fb853ee171c5 in /",
            is_empty=False,
            author=None,
            comment=None,
            raw_entry={
                "created_by": "/bin/sh -c #(nop) ADD file:a3bc1e842b69636f9df5256c49c5374fb4eef1e281fe3f282c65fb853ee171c5 in /",
                "created": "2015-10-31T22:22:54.690851953Z",
            },
        ),
        LayerHistory(
            created="2015-10-31T22:22:55.613815829Z",
            created_datetime=datetime.datetime(2015, 10, 31, 22, 22, 55, 613815, tzinfo=tzutc()),
            command='/bin/sh -c #(nop) CMD ["sh"]',
            is_empty=True,
            author=None,
            comment=None,
            raw_entry={
                "empty_layer": True,
                "created_by": '/bin/sh -c #(nop) CMD ["sh"]',
                "created": "2015-10-31T22:22:55.613815829Z",
            },
        ),
    ]
    assert history == expected


def test_config_additional_fields():
    valid_config = json.loads(SAMPLE_CONFIG)
    valid_config["additional_field"] = "boop"
    OCIConfig(Bytes.for_string_or_unicode(json.dumps(valid_config)))


def test_config_missing_required():
    valid_config = json.loads(SAMPLE_CONFIG)
    valid_config.pop("os")

    with pytest.raises(MalformedConfig):
        OCIConfig(Bytes.for_string_or_unicode(json.dumps(valid_config)))


def test_invalid_config():
    with pytest.raises(MalformedConfig):
        OCIConfig(Bytes.for_string_or_unicode('{"config": "invalid"}'))


def test_artifact_registratioon():
    # Register helm
    register_artifact_type("application/vnd.cncf.helm.config.v1+json", ["application/tar+gzip"])
    assert "application/vnd.cncf.helm.config.v1+json" in ALLOWED_ARTIFACT_TYPES
    assert "application/tar+gzip" in ADDITIONAL_LAYER_CONTENT_TYPES

    # Register a new layer type to an existing config type
    register_artifact_type(
        OCI_IMAGE_CONFIG_CONTENT_TYPE, ["application/vnd.oci.image.layer.v1.tar+zstd"]
    )
    assert (
        OCI_IMAGE_CONFIG_CONTENT_TYPE in ALLOWED_ARTIFACT_TYPES
        and ALLOWED_ARTIFACT_TYPES.count(OCI_IMAGE_CONFIG_CONTENT_TYPE) == 1
    )
    assert "application/vnd.oci.image.layer.v1.tar+zstd" in ADDITIONAL_LAYER_CONTENT_TYPES

    # Attempt to register existing helm type
    register_artifact_type("application/vnd.cncf.helm.config.v1+json", ["application/tar+gzip"])
    assert (
        "application/vnd.cncf.helm.config.v1+json" in ALLOWED_ARTIFACT_TYPES
        and ALLOWED_ARTIFACT_TYPES.count("application/vnd.cncf.helm.config.v1+json") == 1
    )
    assert (
        "application/tar+gzip" in ADDITIONAL_LAYER_CONTENT_TYPES
        and ADDITIONAL_LAYER_CONTENT_TYPES.count("application/tar+gzip") == 1
    )


def test_empty_config():
    with does_not_raise(MalformedConfig):
        OCIConfig(Bytes.for_string_or_unicode("{}"))
