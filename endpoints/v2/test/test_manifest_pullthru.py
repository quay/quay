import unittest
from test.fixtures import *  # noqa: F401, F403
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for

from app import app as realapp
from app import instance_keys
from auth.auth_context_type import ValidatedAuthContext
from data import model
from data.database import (
    ImageStorage,
    ImageStoragePlacement,
    Manifest,
    ManifestBlob,
    ManifestChild,
    Repository,
    Tag,
)
from data.model import oci
from data.registry_model import datatypes, registry_model
from data.registry_model.shared import SyntheticIDHandler
from endpoints.test.shared import conduct_call
from image.docker.schema1 import (
    DOCKER_SCHEMA1_CONTENT_TYPES,
    DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
)
from image.docker.schema2 import (
    DOCKER_SCHEMA2_CONTENT_TYPES,
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.oci import (
    OCI_CONTENT_TYPES,
    OCI_IMAGE_INDEX_CONTENT_TYPE,
    OCI_IMAGE_MANIFEST_CONTENT_TYPE,
)
from image.shared.schemas import parse_manifest_from_bytes
from proxy.fixtures import *  # noqa: F401, F403
from util.bytes import Bytes
from util.security.registry_jwt import build_context_and_subject, generate_bearer_token

BUSYBOX_MANIFEST_JSON = r"""{
   "schemaVersion": 1,
   "name": "library/busybox",
   "tag": "latest",
   "architecture": "amd64",
   "fsLayers": [
      {
         "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
      },
      {
         "blobSum": "sha256:5cc84ad355aaa64f46ea9c7bbcc319a9d808ab15088a27209c9e70ef86e5a2aa"
      }
   ],
   "history": [
      {
         "v1Compatibility": "{\"architecture\":\"amd64\",\"config\":{\"Hostname\":\"\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"sh\"],\"Image\":\"sha256:da658412c37aa24e561eb7e16c61bc82a9711340d8fb5cf1a8f39d8e96d7f723\",\"Volumes\":null,\"WorkingDir\":\"\",\"Entrypoint\":null,\"OnBuild\":null,\"Labels\":null},\"container\":\"a0007fa726185ffbcb68e90f8edabedd79a08949f32f4f0bcc6e5fed713a72c8\",\"container_config\":{\"Hostname\":\"a0007fa72618\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"/bin/sh\",\"-c\",\"#(nop) \",\"CMD [\\\"sh\\\"]\"],\"Image\":\"sha256:da658412c37aa24e561eb7e16c61bc82a9711340d8fb5cf1a8f39d8e96d7f723\",\"Volumes\":null,\"WorkingDir\":\"\",\"Entrypoint\":null,\"OnBuild\":null,\"Labels\":{}},\"created\":\"2021-12-30T19:19:41.006954958Z\",\"docker_version\":\"20.10.7\",\"id\":\"5ab5e1c8a2f040cd0b95f123c82a0853c87e24d278c337666d9119e2cb933fca\",\"os\":\"linux\",\"parent\":\"fb161ec7bbd38b27e660e76a08f3e57c458b94e3586ee7667405e1695a15f792\",\"throwaway\":true}"
      },
      {
         "v1Compatibility": "{\"id\":\"fb161ec7bbd38b27e660e76a08f3e57c458b94e3586ee7667405e1695a15f792\",\"created\":\"2021-12-30T19:19:40.833034683Z\",\"container_config\":{\"Cmd\":[\"/bin/sh -c #(nop) ADD file:6db446a57cbd2b7f4cfde1f280177b458390ed5a6d1b54c6169522bc2c4d838e in / \"]}}"
      }
   ],
   "signatures": [
      {
         "header": {
            "jwk": {
               "crv": "P-256",
               "kid": "LKBE:JGAL:FWCB:NZB4:6YRQ:EKM3:VRLP:WR5K:5ZEY:2Z7D:MORV:GPWY",
               "kty": "EC",
               "x": "NXNObrhsZMN6yF22HhK04KRU1NucufpJUVgH8dNlu5w",
               "y": "xkwdVwwMh88f0ubiRFdy3ewgpsiw55LAijX-IecoVLQ"
            },
            "alg": "ES256"
         },
         "signature": "PTCOkbWvxwJIiO0Ig9icuhMJbXUxdTQKRu7qWd3k1WKdStSLEj0ETetTcIe8eYx_2oWUCWZX5AptZ0dNFSKimA",
         "protected": "eyJmb3JtYXRMZW5ndGgiOjIwODcsImZvcm1hdFRhaWwiOiJDbjAiLCJ0aW1lIjoiMjAyMi0wMi0wMVQwOToyODowOVoifQ"
      }
   ]
}"""  # noqa: E501


HELLO_WORLD_SCHEMA1_MANIFEST_JSON = r"""{
   "schemaVersion": 1,
   "name": "library/hello-world",
   "tag": "latest",
   "architecture": "amd64",
   "fsLayers": [
      {
         "blobSum": "sha256:a3ed95caeb02ffe68cdd9fd84406680ae93d633cb16422d00e8a7c22955b46d4"
      },
      {
         "blobSum": "sha256:2db29710123e3e53a794f2694094b9b4338aa9ee5c40b930cb8063a1be392c54"
      }
   ],
   "history": [
      {
         "v1Compatibility": "{\"architecture\":\"amd64\",\"config\":{\"Hostname\":\"\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"/hello\"],\"Image\":\"sha256:b9935d4e8431fb1a7f0989304ec86b3329a99a25f5efdc7f09f3f8c41434ca6d\",\"Volumes\":null,\"WorkingDir\":\"\",\"Entrypoint\":null,\"OnBuild\":null,\"Labels\":null},\"container\":\"8746661ca3c2f215da94e6d3f7dfdcafaff5ec0b21c9aff6af3dc379a82fbc72\",\"container_config\":{\"Hostname\":\"8746661ca3c2\",\"Domainname\":\"\",\"User\":\"\",\"AttachStdin\":false,\"AttachStdout\":false,\"AttachStderr\":false,\"Tty\":false,\"OpenStdin\":false,\"StdinOnce\":false,\"Env\":[\"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\"],\"Cmd\":[\"/bin/sh\",\"-c\",\"#(nop) \",\"CMD [\\\"/hello\\\"]\"],\"Image\":\"sha256:b9935d4e8431fb1a7f0989304ec86b3329a99a25f5efdc7f09f3f8c41434ca6d\",\"Volumes\":null,\"WorkingDir\":\"\",\"Entrypoint\":null,\"OnBuild\":null,\"Labels\":{}},\"created\":\"2021-09-23T23:47:57.442225064Z\",\"docker_version\":\"20.10.7\",\"id\":\"a1f125167a7f2cffa48b7851ff3f75e983824c16e8da61f20765eb55f7b3a594\",\"os\":\"linux\",\"parent\":\"cd13bf215b21e9bc78460fa5070860a498671e2ac282d86d15042cf0c26e6e8b\",\"throwaway\":true}"
      },
      {
         "v1Compatibility": "{\"id\":\"cd13bf215b21e9bc78460fa5070860a498671e2ac282d86d15042cf0c26e6e8b\",\"created\":\"2021-09-23T23:47:57.098990892Z\",\"container_config\":{\"Cmd\":[\"/bin/sh -c #(nop) COPY file:50563a97010fd7ce1ceebd1fa4f4891ac3decdf428333fb2683696f4358af6c2 in / \"]}}"
      }
   ],
   "signatures": [
      {
         "header": {
            "jwk": {
               "crv": "P-256",
               "kid": "SDXO:UBRC:JIUZ:YE6I:7UX3:RUZY:YS3V:PLXC:RRHC:YPE5:OPJK:AZOW",
               "kty": "EC",
               "x": "rFgPWrZeIWtw2tXhsrpqJ_whMmlcHBvS8s8Lwkj4KtM",
               "y": "ySCfm20HT11HYt9lsuX8W5tr5hJy6umSowlkzAftmSI"
            },
            "alg": "ES256"
         },
         "signature": "Z9IqzHbMxBBt1KJ7nEVLw2d6o4mugYdSrRKuLpvlbLNvNC19U-aTVsO1dS5czeFE9J9z16s5HDWZhRbLY8dYcQ",
         "protected": "eyJmb3JtYXRMZW5ndGgiOjIxMDAsImZvcm1hdFRhaWwiOiJDbjAiLCJ0aW1lIjoiMjAyMi0wMi0xN1QxNTowNzoxOFoifQ"
      }
   ]
}"""  # noqa: E501


HELLO_WORLD_SCHEMA2_MANIFEST_JSON = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 1469,
      "digest": "sha256:feb5d9fea6a5e9606aa995e879d862b825965ba48de054caab5ef356dc6b3412"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 2479,
         "digest": "sha256:2db29710123e3e53a794f2694094b9b4338aa9ee5c40b930cb8063a1be392c54"
      }
   ]
}"""


HELLO_WORLD_OCI_MANIFEST_JSON = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.oci.image.manifest.v1+json",
   "config": {
      "mediaType": "application/vnd.oci.image.config.v1+json",
      "size": 1456,
      "digest": "sha256:ec3f0931a6e6b6855d76b2d7b0be30e81860baccd891b2e243280bf1cd8ad710"
   },
   "layers": [
      {
         "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
         "size": 772795,
         "digest": "sha256:009932687766e1520a47aa9de3bfe97ffdb1b6cad0b08d5078bad60329f13f19"
      }
   ]
}"""


HELLO_WORLD_MANIFEST_LIST_JSON = r"""{"manifests":[{"digest":"sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"linux"},"size":525},{"digest":"sha256:7b8b7289d0536a08eabdf71c20246e23f7116641db7e1d278592236ea4dcb30c","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v5"},"size":525},{"digest":"sha256:f130bd2d67e6e9280ac6d0a6c83857bfaf70234e8ef4236876eccfbd30973b1c","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm","os":"linux","variant":"v7"},"size":525},{"digest":"sha256:01433e86a06b752f228e3c17394169a5e21a0995f153268a9b36a16d4f2b2184","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"arm64","os":"linux","variant":"v8"},"size":525},{"digest":"sha256:251bb7a536c7cce3437758971aab3a31c6da52fb43ff0654cff5b167c4486409","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"386","os":"linux"},"size":525},{"digest":"sha256:c2f204d26b4ea353651385001bb6bc371d8c4edcd9daf61d00ad365d927e00c0","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"mips64le","os":"linux"},"size":525},{"digest":"sha256:b836bb24a270b9cc935962d8228517fde0f16990e88893d935efcb1b14c0017a","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"ppc64le","os":"linux"},"size":525},{"digest":"sha256:98c9722322be649df94780d3fbe594fce7996234b259f27eac9428b84050c849","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"riscv64","os":"linux"},"size":525},{"digest":"sha256:c7b6944911848ce39b44ed660d95fb54d69bbd531de724c7ce6fc9f743c0b861","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"s390x","os":"linux"},"size":525},{"digest":"sha256:b3dd41b5fbccbf0e39bee932466d389214cddcb53fa4ad5d02f29ee4172db8c7","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.20348.524"},"size":1125},{"digest":"sha256:fdea2bf76c9a47fc0b81958cb87aa65448012ef36ce051a72a09db398efdf7cc","mediaType":"application\/vnd.docker.distribution.manifest.v2+json","platform":{"architecture":"amd64","os":"windows","os.version":"10.0.17763.2565"},"size":1125}],"mediaType":"application\/vnd.docker.distribution.manifest.list.v2+json","schemaVersion":2}"""  # noqa: E501


HELLO_WORLD_CONFIG_BLOB = """{
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
      "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ],
    "Cmd": [
      "/hello"
    ],
    "Image": "sha256:b9935d4e8431fb1a7f0989304ec86b3329a99a25f5efdc7f09f3f8c41434ca6d",
    "Volumes": null,
    "WorkingDir": "",
    "Entrypoint": null,
    "OnBuild": null,
    "Labels": null
  },
  "container": "8746661ca3c2f215da94e6d3f7dfdcafaff5ec0b21c9aff6af3dc379a82fbc72",
  "container_config": {
    "Hostname": "8746661ca3c2",
    "Domainname": "",
    "User": "",
    "AttachStdin": false,
    "AttachStdout": false,
    "AttachStderr": false,
    "Tty": false,
    "OpenStdin": false,
    "StdinOnce": false,
    "Env": [
      "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ],
    "Cmd": [
      "/bin/sh",
      "-c",
      "#(nop) ",
      "CMD [\"/hello\"]"
    ],
    "Image": "sha256:b9935d4e8431fb1a7f0989304ec86b3329a99a25f5efdc7f09f3f8c41434ca6d",
    "Volumes": null,
    "WorkingDir": "",
    "Entrypoint": null,
    "OnBuild": null,
    "Labels": {}
  },
  "created": "2021-09-23T23:47:57.442225064Z",
  "docker_version": "20.10.7",
  "history": [
    {
      "created": "2021-09-23T23:47:57.098990892Z",
      "created_by": "/bin/sh -c #(nop) COPY file:50563a97010fd7ce1ceebd1fa4f4891ac3decdf428333fb2683696f4358af6c2 in / "
    },
    {
      "created": "2021-09-23T23:47:57.442225064Z",
      "created_by": "/bin/sh -c #(nop)  CMD [\"/hello\"]",
      "empty_layer": true
    }
  ],
  "os": "linux",
  "rootfs": {
    "type": "layers",
    "diff_ids": [
      "sha256:e07ee1baac5fae6a26f30cabfe54a36d3402f96afda318fe0a96cec4ca393359"
    ]
  }
}"""  # noqa: E501


def _get_auth_headers(subject, context, repository):
    access = [
        {
            "type": "repository",
            "name": repository,
            "actions": ["pull"],
        }
    ]
    token = generate_bearer_token(
        realapp.config["SERVER_HOSTNAME"],
        subject,
        context,
        access,
        600,
        instance_keys,
    )
    return {
        "Authorization": "Bearer %s" % token,
    }


# builds a dictionary to make pytest generated test names more readable
# when running tests with -v.
storage_test_cases = {
    "busybox_schema1_by_tag": {
        "view_name": "v2.fetch_manifest_by_tagname",
        "image_name": "busybox",
        "manifest_ref": "latest",
        "manifest_json": BUSYBOX_MANIFEST_JSON,
        "manifest_type": DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
        "ref_type": "tag",
    },
    "busybox_schema1_by_digest": {
        "view_name": "v2.fetch_manifest_by_digest",
        "image_name": "busybox",
        "manifest_ref": "sha256:a582d7abe236f9cd151664535f5fde901fb714ab43bd476f6d27c9ef9a12b83d",
        "manifest_json": BUSYBOX_MANIFEST_JSON,
        "manifest_type": DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE,
        "ref_type": "digest",
    },
    "hello_world_schema2_by_tag": {
        "view_name": "v2.fetch_manifest_by_tagname",
        "image_name": "hello-world",
        "manifest_ref": "latest",
        "manifest_json": HELLO_WORLD_SCHEMA2_MANIFEST_JSON,
        "manifest_type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        "ref_type": "tag",
    },
    "hello_world_schema2_by_digest": {
        "view_name": "v2.fetch_manifest_by_digest",
        "image_name": "hello-world",
        "manifest_ref": "sha256:f54a58bc1aac5ea1a25d796ae155dc228b3f0e11d046ae276b39c4bf2f13d8c4",
        "manifest_json": HELLO_WORLD_SCHEMA2_MANIFEST_JSON,
        "manifest_type": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        "ref_type": "digest",
    },
    "hello_world_oci_by_tag": {
        "view_name": "v2.fetch_manifest_by_tagname",
        "image_name": "hello-world",
        "manifest_ref": "latest",
        "manifest_json": HELLO_WORLD_OCI_MANIFEST_JSON,
        "manifest_type": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
        "ref_type": "tag",
    },
    "hello_world_oci_by_digest": {
        "view_name": "v2.fetch_manifest_by_digest",
        "image_name": "hello-world",
        "manifest_ref": "sha256:5bc9917d1e7c0cb694c8e24f5b49b22bc61b97a17f34064173144e20b42a62c9",
        "manifest_json": HELLO_WORLD_OCI_MANIFEST_JSON,
        "manifest_type": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
        "ref_type": "digest",
    },
    "hello_world_multi_arch_by_tag": {
        "view_name": "v2.fetch_manifest_by_tagname",
        "image_name": "hello-world",
        "manifest_ref": "latest",
        "manifest_json": HELLO_WORLD_MANIFEST_LIST_JSON,
        "manifest_type": DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
        "ref_type": "tag",
    },
}


@pytest.mark.parametrize(
    "test_name",
    storage_test_cases.keys(),
)
class TestManifestPullThroughStorage:
    orgname = "cache-library"
    registry = "docker.io/library"
    config = None
    org = None
    ctx = None
    sub = None

    @pytest.fixture(autouse=True)
    def setup(self, client, app):
        self.client = client

        self.user = model.user.get_user("devtable")
        context, subject = build_context_and_subject(ValidatedAuthContext(user=self.user))
        self.ctx = context
        self.sub = subject

        if self.org is None:
            self.org = model.organization.create_organization(
                self.orgname, "{self.orgname}@devtable.com", self.user
            )
            self.org.save()
            self.config = model.proxy_cache.create_proxy_cache_config(
                org_name=self.orgname,
                upstream_registry=self.registry,
                expiration_s=3600,
            )

    def test_creates_repo_on_first_pull(self, test_name, proxy_manifest_response):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )
        repo = model.repository.get_repository(self.orgname, test_params["image_name"])
        assert repo is not None
        assert repo.visibility.name == "private"

    def test_does_not_create_repo_when_upstream_repo_does_not_exist(
        self, test_name, proxy_manifest_response
    ):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=404,
                headers=headers,
            )
        count = Repository.filter(
            Repository.name == test_params["image_name"], Repository.namespace_user == self.org.id
        ).count()
        assert count == 0

    def test_does_not_create_repo_when_already_exists(self, test_name, proxy_manifest_response):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        r = model.repository.create_repository(self.orgname, test_params["image_name"], self.user)
        assert r is not None
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        count = Repository.filter(
            Repository.name == test_params["image_name"], Repository.namespace_user == self.org.id
        ).count()
        assert count == 1

    def test_creates_manifest_on_first_pull(self, test_name, proxy_manifest_response):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        repository_ref = registry_model.lookup_repository(self.orgname, test_params["image_name"])
        assert repository_ref is not None
        tag = registry_model.get_repo_tag(repository_ref, test_params["manifest_ref"])

        # when testing the fetch_manifest_by_digest view the tag created is temporary,
        # and it does not refer to the manifest digest (manifest_ref), so we need to
        # fetch it by its link to the repository instead.
        if test_params["ref_type"] == "digest":
            tag = Tag.filter(Tag.repository_id == repository_ref.id).get()
            # get_manifest_for_tag returns a tag of datatypes.Tag, so we convert
            # the one we have to that type.
            tag = datatypes.Tag.for_tag(tag, SyntheticIDHandler())

        assert tag is not None
        manifest = registry_model.get_manifest_for_tag(tag)
        assert manifest is not None

        output_manifest = manifest.get_parsed_manifest()
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )
        assert output_manifest.schema_version == input_manifest.schema_version
        assert output_manifest.media_type == input_manifest.media_type
        assert output_manifest.is_manifest_list == input_manifest.is_manifest_list
        assert output_manifest.digest == input_manifest.digest
        assert output_manifest.manifest_dict == input_manifest.manifest_dict

    def test_does_not_pull_from_upstream_when_manifest_already_exists(
        self, test_name, proxy_manifest_response
    ):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }

        r = model.repository.create_repository(self.orgname, test_params["image_name"], self.user)
        assert r is not None
        manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )
        m = oci.manifest.create_manifest(r.id, manifest)
        assert m is not None

        if test_params["ref_type"] == "digest":
            oci.tag.create_temporary_tag_if_necessary(m, 300)
        else:
            oci.tag.retarget_tag(test_params["manifest_ref"], m.id)

        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        assert proxy_mock.manifest_exists.call_count == 1
        assert proxy_mock.get_manifest.call_count == 0

    def test_create_manifest_config_blob(self, test_name, proxy_manifest_response):
        test_params = storage_test_cases[test_name]
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )
        if manifest.schema_version == 2 and not manifest.is_manifest_list:
            q = ImageStorage.filter(ImageStorage.content_checksum == manifest.config.digest)
            assert q.count() == 1

    def test_manifest_list_create_manifest_with_sub_manifests_and_connect_them(
        self, test_name, proxy_manifest_response
    ):
        test_params = storage_test_cases[test_name]
        if test_params["manifest_type"] not in [
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            OCI_IMAGE_INDEX_CONTENT_TYPE,
        ]:
            pytest.skip("regular manifest detected, skipping manifest list specific test.")

        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        manifest_list = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )
        try:
            manifest = Manifest.filter(Manifest.digest == manifest_list.digest).get()
        except Manifest.DoesNotExist:
            assert False, "failed to create manifest list"

        input_digests = [
            manifest["digest"] for manifest in manifest_list.manifest_dict["manifests"]
        ]
        manifest_links = ManifestChild.select(ManifestChild.child_manifest).where(
            ManifestChild.manifest == manifest
        )
        sub_digests = [ml.child_manifest.digest for ml in manifest_links]
        assert input_digests == sub_digests

        for link in manifest_links:
            mbytes = link.child_manifest.manifest_bytes
            assert mbytes == "", f"child manifest bytes expected empty, but got {mbytes}"

    def test_pull_placeholder_manifest_updates_manifest_bytes(
        self, test_name, proxy_manifest_response
    ):
        """
        it's not possible to connect a sub-manifest to a manifest list on a subsequent pull,
        since a regular manifest request has no pointer to the manifest list it belongs to.
        to connect the sub-manifests with the manifest list being at pull time, we create a
        placeholder manifest.
        placeholder manifests are caracterized by having an empty manifest_bytes.
        """
        test_params = storage_test_cases[test_name]
        if test_params["manifest_type"] in [
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            OCI_IMAGE_INDEX_CONTENT_TYPE,
        ]:
            pytest.skip("manifest list detected, skipping 'flat' manifest specific test.")

        # we only have the manifest list json for the hello-world
        # (because it's significantly smaller).
        if test_params["image_name"] == "busybox":
            pytest.skip("skipping test for busybox image - we do not have its manifest list json.")

        if test_params["manifest_type"] == OCI_IMAGE_MANIFEST_CONTENT_TYPE:
            pytest.skip("skipping OCI content type - manifest list specifies docker schema v2.")

        if test_params["ref_type"] == "tag":
            pytest.skip(
                "skipping manifest fetch by tag - pull for a specific "
                "architecture is made by digest",
            )

        parsed = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(HELLO_WORLD_MANIFEST_LIST_JSON),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            sparse_manifest_support=True,
        )

        # first create the manifest list and its placeholders
        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": parsed.digest,
        }
        proxy_mock = proxy_manifest_response(
            parsed.digest,
            HELLO_WORLD_MANIFEST_LIST_JSON,
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        # now fetch one of the sub manifests from the manifest list
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }
        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"],
            test_params["manifest_json"],
            test_params["manifest_type"],
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        sub_manifest = Manifest.filter(Manifest.digest == test_params["manifest_ref"]).get()
        assert sub_manifest.manifest_bytes != ""

        output_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(sub_manifest.manifest_bytes),
            sub_manifest.media_type.name,
            sparse_manifest_support=True,
        )
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )

        assert output_manifest.schema_version == input_manifest.schema_version
        assert output_manifest.media_type == input_manifest.media_type
        assert output_manifest.is_manifest_list == input_manifest.is_manifest_list
        assert output_manifest.digest == input_manifest.digest
        assert output_manifest.manifest_dict == input_manifest.manifest_dict

    def test_create_placeholder_blobs_on_first_pull(self, test_name, proxy_manifest_response):
        test_params = storage_test_cases[test_name]
        # no blob placeholders are created for manifest lists - we don't have
        # the sub-manifests at manifest list creation time, so there's no way
        # to know which blobs the sub-manifest has.
        if test_params["manifest_type"] in [
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            OCI_IMAGE_INDEX_CONTENT_TYPE,
        ]:
            pytest.skip("manifest list detected - skipping blob placeholder test")

        repo = f"{self.orgname}/{test_params['image_name']}"
        params = {
            "repository": repo,
            "manifest_ref": test_params["manifest_ref"],
        }

        proxy_mock = proxy_manifest_response(
            test_params["manifest_ref"], test_params["manifest_json"], test_params["manifest_type"]
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            headers = _get_auth_headers(self.sub, self.ctx, repo)
            headers["Accept"] = ", ".join(
                DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                    DOCKER_SCHEMA1_CONTENT_TYPES
                )
            )
            conduct_call(
                self.client,
                test_params["view_name"],
                url_for,
                "GET",
                params,
                expected_code=200,
                headers=headers,
            )

        parsed = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(test_params["manifest_json"]),
            test_params["manifest_type"],
            sparse_manifest_support=True,
        )
        manifest = Manifest.filter(Manifest.digest == parsed.digest).get()
        mdict = parsed.manifest_dict
        layers = mdict.get("layers", mdict.get("fsLayers"))
        mblobs = ManifestBlob.filter(ManifestBlob.manifest == manifest)

        expected_count = len(layers)

        # schema 2 manifests have an extra config blob which we need to take into
        # consideration in the total count
        config_digest = ""
        if parsed.schema_version == 2:
            config_digest = parsed.config.digest
            expected_count += 1

        assert mblobs.count() == expected_count

        for mblob in mblobs:
            blob = None
            layer = None

            # don't assert if digest belongs to a config blob
            if mblob.blob.content_checksum == config_digest:
                continue

            for layer in layers:
                digest = layer.get("digest", layer.get("blobSum"))
                if mblob.blob.content_checksum == digest:
                    blob = mblob.blob
                    layer = layer
                    break

            assert blob is not None
            assert blob.image_size == layer.get("size", None)

            # the absence of an image storage placement for a blob indicates that it's
            # a placeholder blob, not yet downloaded from the upstream registry.
            placements = ImageStoragePlacement.filter(ImageStoragePlacement.storage == blob)
            assert placements.count() == 0


@pytest.mark.e2e
class TestManifestPullThroughProxyDockerHub(unittest.TestCase):
    org = "cache"
    org2 = "cache-library"
    registry = "docker.io"
    repository = f"{org}/library/postgres"
    repository2 = f"{org2}/postgres"
    tag = "14"
    ctx = None
    sub = None

    @pytest.fixture(autouse=True)
    def setup(self, client, app):
        self.client = client

        self.user = model.user.get_user("devtable")
        context, subject = build_context_and_subject(ValidatedAuthContext(user=self.user))
        self.ctx = context
        self.sub = subject

        try:
            model.organization.get(self.org)
        except Exception:
            org = model.organization.create_organization(self.org, "cache@devtable.com", self.user)
            org.save()

        try:
            model.organization.get(self.org2)
        except Exception:
            org = model.organization.create_organization(
                self.org2,
                "cache-library@devtable.com",
                self.user,
            )
            org.save()

        try:
            model.proxy_cache.get_proxy_cache_config_for_org(self.org)
        except Exception:
            model.proxy_cache.create_proxy_cache_config(
                org_name=self.org,
                upstream_registry=self.registry,
            )

        try:
            model.proxy_cache.get_proxy_cache_config_for_org(self.org2)
        except Exception:
            model.proxy_cache.create_proxy_cache_config(
                org_name=self.org2,
                upstream_registry=self.registry + "/library",
            )

    def _get_auth_headers(self, repository):
        access = [
            {
                "type": "repository",
                "name": repository,
                "actions": ["pull"],
            }
        ]
        token = generate_bearer_token(
            realapp.config["SERVER_HOSTNAME"],
            self.sub,
            self.ctx,
            access,
            600,
            instance_keys,
        )
        return {
            "Authorization": "Bearer %s" % token,
        }

    def test_pull_proxy_whole_dockerhub(self):
        params = {
            "repository": self.repository,
            "manifest_ref": self.tag,
        }
        headers = self._get_auth_headers(self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_pull_proxy_single_namespace_dockerhub(self):
        params = {
            "repository": self.repository2,
            "manifest_ref": self.tag,
        }
        headers = self._get_auth_headers(self.repository2)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_pull_proxy_whole_dockerhub_404(self):
        params = {
            "repository": self.repository,
            "manifest_ref": "666",
        }
        headers = self._get_auth_headers(self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=404,
            headers=headers,
        )

    def test_pull_from_dockerhub_by_digest(self):
        digest = "sha256:f329d076a8806c0ce014ce5e554ca70f4ae9407a16bb03baa7fef287ee6371f1"
        params = {
            "repository": self.repository,
            "manifest_ref": digest,
        }
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=self._get_auth_headers(self.repository),
        )

    def test_check_manifest_exists_from_dockerhub_by_tag(self):
        params = {
            "repository": self.repository,
            "manifest_ref": self.tag,
        }
        headers = self._get_auth_headers(self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "HEAD",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_check_manifest_exists_from_dockerhub_by_tag_404(self):
        params = {
            "repository": self.repository,
            "manifest_ref": "666",
        }
        headers = self._get_auth_headers(self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "HEAD",
            params,
            expected_code=404,
            headers=headers,
        )


@pytest.mark.e2e
class TestManifestPullThroughProxy(unittest.TestCase):
    org = "cache"
    org2 = "cache-library"
    registry = "docker.io"
    repository = f"{org}/library/postgres"
    repository2 = f"{org2}/postgres"
    tag = "14"
    ctx = None
    sub = None

    @pytest.fixture(autouse=True)
    def setup(self, client, app):
        self.client = client

        self.user = model.user.get_user("devtable")
        context, sub = build_context_and_subject(ValidatedAuthContext(user=self.user))
        self.ctx = context
        self.sub = sub

        try:
            model.organization.get(self.org)
        except Exception:
            org = model.organization.create_organization(self.org, "cache@devtable.com", self.user)
            org.save()

        try:
            model.organization.get(self.org2)
        except Exception:
            org = model.organization.create_organization(
                self.org2,
                "cache-library@devtable.com",
                self.user,
            )
            org.save()

        try:
            model.proxy_cache.get_proxy_cache_config_for_org(self.org)
        except Exception:
            model.proxy_cache.create_proxy_cache_config(
                org_name=self.org,
                upstream_registry=self.registry,
                expiration_s=3600,
            )

        try:
            model.proxy_cache.get_proxy_cache_config_for_org(self.org2)
        except Exception:
            model.proxy_cache.create_proxy_cache_config(
                org_name=self.org2,
                upstream_registry=self.registry + "/library",
                expiration_s=3600,
            )

    def _get_auth_headers(self, repository):
        access = [
            {
                "type": "repository",
                "name": repository,
                "actions": ["pull"],
            }
        ]
        token = generate_bearer_token(
            realapp.config["SERVER_HOSTNAME"],
            self.sub,
            self.ctx,
            access,
            600,
            instance_keys,
        )
        return {
            "Authorization": "Bearer %s" % token,
        }

    def test_pull_proxy_whole_registry(self):
        params = {
            "repository": self.repository,
            "manifest_ref": self.tag,
        }
        headers = _get_auth_headers(self.sub, self.ctx, self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_pull_proxy_single_namespace(self):
        params = {
            "repository": self.repository2,
            "manifest_ref": self.tag,
        }
        headers = _get_auth_headers(self.sub, self.ctx, self.repository2)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_pull_proxy_whole_registry_404(self):
        params = {
            "repository": self.repository,
            "manifest_ref": "666",
        }
        headers = _get_auth_headers(self.sub, self.ctx, self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "GET",
            params,
            expected_code=404,
            headers=headers,
        )

    def test_pull_by_digest(self):
        digest = "sha256:f329d076a8806c0ce014ce5e554ca70f4ae9407a16bb03baa7fef287ee6371f1"
        params = {
            "repository": self.repository,
            "manifest_ref": digest,
        }
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_digest",
            url_for,
            "GET",
            params,
            expected_code=200,
            headers=_get_auth_headers(self.sub, self.ctx, self.repository),
        )

    def test_check_manifest_exists_by_tag(self):
        params = {
            "repository": self.repository,
            "manifest_ref": self.tag,
        }
        headers = _get_auth_headers(self.sub, self.ctx, self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "HEAD",
            params,
            expected_code=200,
            headers=headers,
        )

    def test_check_manifest_exists_by_tag_404(self):
        params = {
            "repository": self.repository,
            "manifest_ref": "666",
        }
        headers = _get_auth_headers(self.sub, self.ctx, self.repository)
        headers["Accept"] = ", ".join(
            DOCKER_SCHEMA2_CONTENT_TYPES.union(OCI_CONTENT_TYPES).union(
                DOCKER_SCHEMA1_CONTENT_TYPES
            )
        )
        conduct_call(
            self.client,
            "v2.fetch_manifest_by_tagname",
            url_for,
            "HEAD",
            params,
            expected_code=404,
            headers=headers,
        )
