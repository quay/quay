from mock import patch

from app import app as realapp
from data.registry_model import registry_model
from endpoints.api.manifest import RepositoryManifest, _get_modelcard_layer_digest
from endpoints.api.test.shared import conduct_api_call
from endpoints.test.shared import client_with_identity
from features import FeatureNameValue
from image.oci.manifest import OCIManifest
from test.fixtures import *
from util.bytes import Bytes


def test_repository_manifest(app):
    with client_with_identity("devtable", app) as cl:
        repo_ref = registry_model.lookup_repository("devtable", "simple")
        tags = registry_model.list_all_active_repository_tags(repo_ref)
        for tag in tags:
            manifest_digest = tag.manifest_digest
            if manifest_digest is None:
                continue

            params = {
                "repository": "devtable/simple",
                "manifestref": manifest_digest,
            }
            result = conduct_api_call(cl, RepositoryManifest, "GET", params, None, 200).json
            assert result["digest"] == manifest_digest
            assert result["manifest_data"]


ARTIFACT_MANIFEST = """{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "artifactType": "application/vnd.example+type",
  "config": {
    "mediaType": "application/vnd.oci.empty.v1+json",
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "size": 2
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar",
      "digest": "sha256:d2a84f4b8b650937ec8f73cd8be2c74add5a911ba64df27458ed8229da804a26",
      "size": 12,
      "annotations": {
        "org.opencontainers.image.title": "hello.txt"
      }
    }
  ],
  "annotations": {
    "org.opencontainers.image.created": "2023-08-03T00:21:51Z"
  }
}"""


IMAGE_MANIFEST = """{
  "schemaVersion": 2,
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a",
    "size": 2,
    "annotations": {
      "hello": "world"
    }
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar",
      "digest": "sha256:22af0898315a239117308d39acd80636326c4987510b0ec6848e58eb584ba82e",
      "size": 6,
      "annotations": {
        "fun": "more cream",
        "org.opencontainers.image.title": "cake.txt"
      }
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar",
      "digest": "sha256:be6fe11876282442bead98e8b24aca07f8972a763cd366c56b4b5f7bcdd23eac",
      "size": 7,
      "annotations": {
        "org.opencontainers.image.title": "juice.txt"
      }
    }
  ],
  "annotations": {
    "foo": "bar"
  }
}"""


def test_modelcar_layer(app):
    manifest1 = OCIManifest(Bytes.for_string_or_unicode(ARTIFACT_MANIFEST))
    manifest2 = OCIManifest(Bytes.for_string_or_unicode(IMAGE_MANIFEST))

    realapp.config["UI_MODELCARD_ANNOTATION"] = {"foo": "bar"}
    realapp.config["UI_MODELCARD_LAYER_ANNOTATION"] = {"org.opencontainers.image.title": "cake.txt"}
    realapp.config["UI_MODELCARD_ARTIFACT_TYPE"] = "application/vnd.example+type"

    with patch("features.UI_MODELCARD", FeatureNameValue("UI_MODELCARD", True)):
        layer_digest1 = _get_modelcard_layer_digest(manifest1)
        assert (
            layer_digest1
            == "sha256:d2a84f4b8b650937ec8f73cd8be2c74add5a911ba64df27458ed8229da804a26"
        )

        layer_digest2 = _get_modelcard_layer_digest(manifest2)
        assert (
            layer_digest2
            == "sha256:22af0898315a239117308d39acd80636326c4987510b0ec6848e58eb584ba82e"
        )
