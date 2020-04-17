import json

import pytest

from image.oci.index import OCIIndex, MalformedIndex
from util.bytes import Bytes

SAMPLE_INDEX = """{
  "schemaVersion": 2,
  "manifests": [
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7143,
      "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
      "platform": {
        "architecture": "ppc64le",
        "os": "linux"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.manifest.v1+json",
      "size": 7682,
      "digest": "sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      }
    }
  ],
  "annotations": {
    "com.example.key1": "value1",
    "com.example.key2": "value2"
  }
}"""


def test_parse_basic_index():
    index = OCIIndex(Bytes.for_string_or_unicode(SAMPLE_INDEX))
    assert index.is_manifest_list
    assert index.digest == "sha256:b1a216e8ed6a267bd3f0234d0d096c04658b28cb08b2b16bf812cf72694d7d04"
    assert index.local_blob_digests == []
    assert index.child_manifest_digests() == [
        u"sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
        u"sha256:5b0bcabd1ed22e9fb1310cf6c2dec7cdef19f0ad69efa1f392e94a4333501270",
    ]


def test_config_missing_required():
    valid_index = json.loads(SAMPLE_INDEX)
    valid_index.pop("schemaVersion")

    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode(json.dumps(valid_index)))


def test_invalid_index():
    with pytest.raises(MalformedIndex):
        OCIIndex(Bytes.for_string_or_unicode("{}"))
