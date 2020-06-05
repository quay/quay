import datetime
import json

from dateutil.tz import tzutc

import pytest

from image.oci.config import OCIConfig, MalformedConfig, LayerHistory
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
        "created_by": "/bin/sh -c #(nop) CMD [\\"sh\\"]",
        "empty_layer": true
      }
    ]
}"""


def test_parse_basic_config():
    config = OCIConfig(Bytes.for_string_or_unicode(SAMPLE_CONFIG))
    assert (
        config.digest == "sha256:b8410e43166c4e6b11cc0db4ede89539f206d5c9bb43d31d5b37f509b78d3f01"
    )
    assert config.size == 1582

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


def test_config_missing_required():
    valid_config = json.loads(SAMPLE_CONFIG)
    valid_config.pop("os")

    with pytest.raises(MalformedConfig):
        OCIConfig(Bytes.for_string_or_unicode(json.dumps(valid_config)))


def test_invalid_config():
    with pytest.raises(MalformedConfig):
        OCIConfig(Bytes.for_string_or_unicode("{}"))
