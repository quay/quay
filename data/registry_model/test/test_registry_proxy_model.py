from datetime import timedelta
from unittest.mock import MagicMock, patch
import json

import pytest
from playhouse.test_utils import assert_query_count

from app import storage
from data.database import (
    Manifest,
    ManifestChild,
    ManifestBlob,
    ImageStorage,
    ImageStorageLocation,
    Tag,
    get_epoch_timestamp_ms,
)
from data.model import oci, TagDoesNotExist
from data.model.blob import store_blob_record_and_temp_link
from data.model.organization import create_organization
from data.model.proxy_cache import create_proxy_cache_config
from data.model.user import get_user
from data.model.repository import create_repository
from data.model.storage import get_layer_path
from data.model.oci.manifest import get_or_create_manifest
from data.registry_model import registry_model
from data.registry_model.registry_proxy_model import ProxyModel
from data.registry_model.datatypes import Manifest as ManifestType
from data.registry_model.test import testdata
from digest.digest_tools import sha256_digest
from image.docker.schema2 import (
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
)
from image.docker.schema1 import DOCKER_SCHEMA1_MANIFEST_CONTENT_TYPE
from image.shared import ManifestException
from image.shared.schemas import parse_manifest_from_bytes
from image.docker.schema2.manifest import DockerSchema2ManifestBuilder
from test.fixtures import *  # noqa: F401,F403
from proxy.fixtures import proxy_manifest_response  # noqa: F401,F403
from util.bytes import Bytes


UBI8_LATEST_MANIFEST_LIST_DIGEST = (
    "sha256:bd5b5d4f108773d02b2f3aa930feaa08067091e96ecf45f10e98e76383ff7af9"  # noqa: E501
)
UBI8_LATEST_MANIFEST_LIST = r"""{
  "manifests": [
    {
      "digest": "sha256:b69959407d21e8a062e0416bf13405bb2b71ed7a84dde4158ebafacfa06f5578",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "amd64",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:ce06da2e3e24e4ac99f6da067bcab57e3dcc2ea4582da16e5d97003c32a6fa8c",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v5"
      },
      "size": 527
    },
    {
      "digest": "sha256:4bcaeca137ff437584eb96c41b425b4010167a0156f0a9f7bbc26f9a36d536df",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v6"
      },
      "size": 527
    },
    {
      "digest": "sha256:5ca5e3117f6f9bdb803ea67af89203b7e62a28c7456c098809f712a7294ceaaa",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm",
        "os": "linux",
        "variant": "v7"
      },
      "size": 527
    },
    {
      "digest": "sha256:2a64d8b2861154867e526a189eddfc7afaf12c13c9b67a56b7adcd56895818ae",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "arm64",
        "os": "linux",
        "variant": "v8"
      },
      "size": 527
    },
    {
      "digest": "sha256:2d06e13d26ccd313d3029e44f48d69ad4c98d0bf934692befb288dc6404a3ad9",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "386",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:5ff091cdd7eadbe140ac122d166a8f20f346a72d7eea9ababbd0546e0ca73049",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "mips64le",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:3f6c90002d9d31b871ee132953db48422b3dea4815d662d9e54ca389d2366800",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "ppc64le",
        "os": "linux"
      },
      "size": 528
    },
    {
      "digest": "sha256:bb2a26ee650f0f3f49a2676bc50bcc4f44d9f1f6c7c12b7b4acc17beda338af4",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "riscv64",
        "os": "linux"
      },
      "size": 527
    },
    {
      "digest": "sha256:02cdeb6ebe57001c73da6adf199eb94a94b6d8c5ef7a92432928d1b3861ff53c",
      "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
      "platform": {
        "architecture": "s390x",
        "os": "linux"
      },
      "size": 528
    }
  ],
  "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
  "schemaVersion": 2
}"""


UBI8_LATEST_DIGEST = "sha256:b69959407d21e8a062e0416bf13405bb2b71ed7a84dde4158ebafacfa06f5578"
UBI8_LATEST_MANIFEST_SCHEMA2 = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 1456,
      "digest": "sha256:ec3f0931a6e6b6855d76b2d7b0be30e81860baccd891b2e243280bf1cd8ad710"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 772795,
         "digest": "sha256:009932687766e1520a47aa9de3bfe97ffdb1b6cad0b08d5078bad60329f13f19"
      }
   ]
}"""


UBI8_8_5_DIGEST = "sha256:8ee9d7bbcfc19d383f9044316a5c5fbcbe2df6be3c97f6c7a5422527b29bdede"
UBI8_8_5_MANIFEST_SCHEMA2 = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 4365,
      "digest": "sha256:cc0656847854310306093b3dc1a7d9e7fc06399da46853e0c921cd5ec1906bfd"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 81428527,
         "digest": "sha256:ce3c6836540f978b55c511d236429e26b7a45f5a6f1204ab8d4378afaf77332f"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 1792,
         "digest": "sha256:63f9f4c31162a6a5dacd999a0dc65007e15b2ca6b2d9360a1234c27de12e7f38"
      }
   ]
}"""


UBI8_8_4_DIGEST = "sha256:5e334d76fc059f7b44ee8fc2da6a2e8b240582d0214364c8c88596d20b33d7f1"
UBI8_8_4_MANIFEST_SCHEMA2 = r"""{
   "schemaVersion": 2,
   "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
   "config": {
      "mediaType": "application/vnd.docker.container.image.v1+json",
      "size": 4366,
      "digest": "sha256:53ce4390f2adb1681eb1a90ec8b48c49c015e0a8d336c197637e7f65e365fa9e"
   },
   "layers": [
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 83368932,
         "digest": "sha256:262268b65bd5f33784d6a61514964887bc18bc00c60c588bc62bfae7edca46f1"
      },
      {
         "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
         "size": 1795,
         "digest": "sha256:06038631a24a25348b51d1bfc7d0a0ee555552a8998f8328f9b657d02dd4c64c"
      }
   ]
}"""


@pytest.fixture
def create_repo():
    def _create_repo(orgname, reponame, user):
        r = create_repository(orgname, reponame, user)
        assert r is not None
        repo_ref = registry_model.lookup_repository(orgname, reponame)
        assert repo_ref is not None
        return repo_ref

    return _create_repo


@patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
def test_registry_proxy_model_init_only_query_db_once(initialized_db):
    orgname = "testorg"
    user = get_user("devtable")
    org = create_organization(orgname, "{self.orgname}@devtable.com", user)
    org.save()
    create_proxy_cache_config(
        org_name=orgname,
        upstream_registry="quay.io",
        expiration_s=3600,
    )
    with assert_query_count(1):
        ProxyModel(
            orgname,
            "app-sre/ubi8-ubi",
            user,
        )


class TestRegistryProxyModelGetSchema1ParsedManifest:
    upstream_registry = "quay.io"
    upstream_repository = "app-sre/ubi8-ubi"
    orgname = "quayio-cache"
    repository = f"{orgname}/{upstream_repository}"
    tag = "8.4"

    @pytest.fixture(autouse=True)
    def setup(self, app, create_repo):
        self.user = get_user("devtable")
        self.org = create_organization(self.orgname, "{self.orgname}@devtable.com", self.user)
        self.org.save()
        self.config = create_proxy_cache_config(
            org_name=self.orgname,
            upstream_registry=self.upstream_registry,
            expiration_s=3600,
        )
        self.repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_raises_exception_with_manifest_list(self):
        manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_LIST),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        with pytest.raises(ManifestException):
            proxy_model.get_schema1_parsed_manifest(
                manifest,
                self.orgname,
                self.upstream_repository,
                self.tag,
                storage,
                raise_on_error=True,
            )

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_raises_exception_with_docker_v2_manifest_to_v1(self):
        def get_blob(layer):
            content = Bytes.for_string_or_unicode(layer).as_encoded_str()
            digest = str(sha256_digest(content))
            blob = store_blob_record_and_temp_link(
                self.orgname,
                self.upstream_repository,
                digest,
                ImageStorageLocation.get(name="local_us"),
                len(content),
                120,
            )
            storage.put_content(["local_us"], get_layer_path(blob), content)
            return blob, digest

        layer1 = json.dumps(
            {
                "config": {},
                "rootfs": {"type": "layers", "diff_ids": []},
                "history": [{}],
            }
        )
        _, config_digest = get_blob(layer1)
        layer2 = "hello world"
        _, blob_digest = get_blob(layer2)
        builder = DockerSchema2ManifestBuilder()
        builder.set_config_digest(config_digest, len(layer1.encode("utf-8")))
        builder.add_layer(blob_digest, len(layer2.encode("utf-8")))
        manifest = builder.build()
        created_manifest = get_or_create_manifest(self.repo_ref.id, manifest, storage)
        assert created_manifest is not None

        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        m = ManifestType.for_manifest(created_manifest.manifest, MagicMock())
        with pytest.raises(ManifestException):
            proxy_model.get_schema1_parsed_manifest(
                m,
                self.orgname,
                self.upstream_repository,
                self.tag,
                storage,
                raise_on_error=True,
            )


class TestRegistryProxyModelCreateManifestAndRetargetTag:
    upstream_registry = "quay.io"
    upstream_repository = "app-sre/ubi8-ubi"
    orgname = "quayio-cache"
    repository = f"{orgname}/{upstream_repository}"
    tag = "8.4"

    @pytest.fixture(autouse=True)
    def setup(self, app):
        self.user = get_user("devtable")
        self.org = create_organization(self.orgname, "{self.orgname}@devtable.com", self.user)
        self.org.save()
        self.config = create_proxy_cache_config(
            org_name=self.orgname,
            upstream_registry=self.upstream_registry,
            expiration_s=3600,
        )

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_create_manifest_and_temp_tag_when_they_dont_exist(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_8_4_MANIFEST_SCHEMA2),
            DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        manifest, tag = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_manifest, self.tag
        )
        assert manifest is not None
        assert tag is not None
        assert manifest.internal_manifest_bytes.as_unicode() == UBI8_8_4_MANIFEST_SCHEMA2
        assert manifest.digest == UBI8_8_4_DIGEST

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_create_8_4_tag_for_existing_manifest(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_8_4_MANIFEST_SCHEMA2),
            DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        # first create the manifest with a temp tag
        first_manifest, _ = proxy_model._create_manifest_with_temp_tag(repo_ref, input_manifest)
        # now try to create it again, but using the actual tag
        manifest, tag = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_manifest, self.tag
        )
        assert first_manifest is not None
        assert manifest is not None
        assert tag is not None
        assert manifest.internal_manifest_bytes.as_unicode() == UBI8_8_4_MANIFEST_SCHEMA2
        assert manifest.digest == UBI8_8_4_DIGEST
        assert manifest.id == first_manifest.id

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_create_placeholder_blobs_for_new_manifest(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_8_4_MANIFEST_SCHEMA2),
            DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        manifest, _ = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_manifest, self.tag
        )
        assert manifest is not None
        blob_count = 1  # schema 2 manifests have one extra config blob
        blob_count += len(input_manifest.manifest_dict["layers"])
        mblobs = ManifestBlob.select().where(ManifestBlob.manifest == manifest.id)
        assert blob_count == mblobs.count()
        expected_digests = [layer["digest"] for layer in input_manifest.manifest_dict["layers"]]
        expected_digests.append(input_manifest.config.digest)
        created_digests = [mblob.blob.content_checksum for mblob in mblobs]
        assert sorted(expected_digests) == sorted(created_digests)

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_connect_existing_blobs_to_new_manifest(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_8_4_MANIFEST_SCHEMA2),
            DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        )
        layer = input_manifest.manifest_dict["layers"][0]
        blob = ImageStorage.create(
            image_size=layer["size"],
            uncompressed_size=layer["size"],
            content_checksum=layer["digest"],
        )

        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        proxy_model._create_manifest_and_retarget_tag(repo_ref, input_manifest, self.tag)
        blob_count = (
            ImageStorage.select()
            .where(ImageStorage.content_checksum == blob.content_checksum)
            .count()
        )
        assert blob_count == 1

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_create_sub_manifests_for_manifest_list(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_LIST),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            sparse_manifest_support=True,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        manifest, _ = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_manifest, self.tag
        )
        mchildren = ManifestChild.select().where(ManifestChild.manifest == manifest.id)
        created_count = mchildren.count()
        expected_count = len(list(input_manifest.child_manifests(content_retriever=None)))
        assert expected_count == created_count

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_create_temp_tags_for_newly_created_sub_manifests_on_manifest_list(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_LIST),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            sparse_manifest_support=True,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        manifest, _ = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_manifest, self.tag
        )
        mchildren = ManifestChild.select(ManifestChild.child_manifest_id).where(
            ManifestChild.manifest == manifest.id
        )
        tags = Tag.select().join(
            ManifestChild, on=(Tag.manifest_id == ManifestChild.child_manifest_id)
        )
        assert mchildren.count() == tags.count()
        assert all([t.hidden for t in tags]), "all sub manifest tags must be hidden"
        assert all(
            [t.name != self.tag for t in tags]
        ), "sub manifest tags must have temp tag name, not parent manifest name"

    @patch("data.registry_model.registry_proxy_model.Proxy", MagicMock())
    def test_connect_existing_manifest_to_manifest_list(self, create_repo):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_manifest = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_SCHEMA2),
            DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
        )
        proxy_model = ProxyModel(
            self.orgname,
            self.upstream_repository,
            self.user,
        )
        manifest, _ = proxy_model._create_manifest_with_temp_tag(repo_ref, input_manifest)
        assert manifest is not None

        input_list = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_LIST),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            sparse_manifest_support=True,
        )
        manifest_list, _ = proxy_model._create_manifest_and_retarget_tag(
            repo_ref, input_list, self.tag
        )
        assert manifest_list is not None
        conn_count = (
            ManifestChild.select()
            .where(
                ManifestChild.manifest == manifest_list.id,
                ManifestChild.child_manifest == manifest.id,
            )
            .count()
        )
        assert conn_count == 1


class TestRegistryProxyModelLookupManifestByDigest:
    upstream_registry = "quay.io"
    upstream_repository = "app-sre/ubi8-ubi"
    orgname = "quayio-cache"
    repository = f"{orgname}/{upstream_repository}"
    digest = UBI8_8_4_DIGEST

    @pytest.fixture(autouse=True)
    def setup(self, app):
        self.user = get_user("devtable")
        self.org = create_organization(self.orgname, "{self.orgname}@devtable.com", self.user)
        self.org.save()
        self.config = create_proxy_cache_config(
            org_name=self.orgname,
            upstream_registry=self.upstream_registry,
            expiration_s=3600,
        )

    def test_returns_cached_manifest_when_it_exists_upstream(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        assert manifest.digest == UBI8_8_4_DIGEST
        first_manifest = manifest

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)

        assert manifest is not None
        assert manifest.id == first_manifest.id
        assert manifest.digest == first_manifest.digest

        # one for each lookup_manifest_by_digest call
        assert proxy_mock.manifest_exists.call_count == 2

        # single call from first call to lookup_manifest_by_digest
        assert proxy_mock.get_manifest.call_count == 1

    def test_renew_tag_when_manifest_is_cached_and_exists_upstream(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        first_tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest.id)

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest.id)
        assert tag.lifetime_end_ms > first_tag.lifetime_end_ms

    def test_renew_manifest_and_parent_tags_when_manifest_has_multiple_parents(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        with patch(
            "data.registry_model.registry_proxy_model.Proxy",
            MagicMock(
                return_value=proxy_manifest_response(
                    "bullseye",
                    testdata.PYTHON_BULLSEYE["manifest"],
                    testdata.PYTHON_BULLSEYE["content-type"],
                )
            ),
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            bullseye = proxy_model.get_repo_tag(repo_ref, "bullseye")
        assert bullseye is not None

        with patch(
            "data.registry_model.registry_proxy_model.Proxy",
            MagicMock(
                return_value=proxy_manifest_response(
                    "latest",
                    testdata.PYTHON_LATEST["manifest"],
                    testdata.PYTHON_LATEST["content-type"],
                )
            ),
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            latest = proxy_model.get_repo_tag(repo_ref, "latest")
        assert latest is not None

        with patch(
            "data.registry_model.registry_proxy_model.Proxy",
            MagicMock(
                return_value=proxy_manifest_response(
                    testdata.PYTHON_ec43d7["digest"],
                    testdata.PYTHON_ec43d7["manifest"],
                    testdata.PYTHON_ec43d7["content-type"],
                )
            ),
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(
                repo_ref, testdata.PYTHON_ec43d7["digest"]
            )
        assert manifest is not None

        updated_bullseye = oci.tag.get_tag_by_manifest_id(repo_ref.id, bullseye.manifest.id)
        updated_latest = oci.tag.get_tag_by_manifest_id(repo_ref.id, latest.manifest.id)
        assert updated_bullseye.lifetime_end_ms > bullseye.lifetime_end_ms
        assert updated_latest.lifetime_end_ms > latest.lifetime_end_ms

    def test_renew_manifest_and_parent_tag_when_manifest_is_child_of_manifest_list(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        input_list = parse_manifest_from_bytes(
            Bytes.for_string_or_unicode(UBI8_LATEST_MANIFEST_LIST),
            DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE,
            sparse_manifest_support=True,
        )
        with patch("data.registry_model.registry_proxy_model.Proxy", MagicMock()):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest_list, tag = proxy_model._create_manifest_and_retarget_tag(
                repo_ref, input_list, "latest"
            )

        assert manifest_list is not None
        child = (
            ManifestChild.select(ManifestChild.child_manifest_id)
            .join(Manifest, on=(ManifestChild.child_manifest_id == Manifest.id))
            .where(
                (ManifestChild.manifest_id == manifest_list.id)
                & (Manifest.digest == UBI8_LATEST_DIGEST)
            )
        )
        manifest_tag = Tag.select().where(Tag.manifest == child).get()
        manifest_list_tag = tag

        proxy_mock = proxy_manifest_response(
            UBI8_LATEST_DIGEST, UBI8_LATEST_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_LATEST_DIGEST)

        updated_tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest.id)
        updated_list_tag = oci.tag.get_tag_by_manifest_id(repo_ref.id, manifest_list.id)

        assert updated_tag.id == manifest_tag.id
        assert updated_list_tag.id == manifest_list_tag.id
        assert updated_tag.lifetime_end_ms > manifest_tag.lifetime_end_ms
        assert updated_list_tag.lifetime_end_ms > manifest_list_tag.lifetime_end_ms

    def test_update_relevant_manifest_fields_when_manifest_is_placeholder(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            "latest", UBI8_LATEST_MANIFEST_LIST, DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, "latest")
        assert tag is not None
        assert tag.manifest.digest == UBI8_LATEST_MANIFEST_LIST_DIGEST
        assert tag.manifest.is_manifest_list

        proxy_mock = proxy_manifest_response(
            UBI8_LATEST_DIGEST, UBI8_LATEST_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_LATEST_DIGEST)
        mbytes = manifest.internal_manifest_bytes.as_unicode()
        assert mbytes != ""
        assert manifest.digest == UBI8_LATEST_DIGEST
        assert manifest.layers_compressed_size == 772795

    def test_renew_tag_when_cache_is_expired_and_manifest_is_up_to_date_with_upstream(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None

        before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        ).where(Tag.manifest == manifest.id).execute()

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        tag = Tag.get(manifest_id=manifest.id)
        now_ms = get_epoch_timestamp_ms()
        assert tag.lifetime_end_ms > now_ms

    def test_return_None_when_local_cache_is_expired_and_manifest_no_longer_exists_upstream(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None

        # expire the tag by setting start and end time to the past
        before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        ).where(Tag.manifest == manifest.id).execute()

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is None

    def test_return_None_when_manifest_is_placeholder_and_upstream_is_down(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            "latest", UBI8_LATEST_MANIFEST_LIST, DOCKER_SCHEMA2_MANIFESTLIST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, "latest")
        assert tag is not None
        assert tag.manifest is not None

        proxy_mock = proxy_manifest_response("does-not-exist", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_LATEST_DIGEST)
        assert manifest is None

    def test_returns_cached_manifest_when_upstream_errors_and_cache_is_not_expired(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        assert manifest.digest == UBI8_8_4_DIGEST
        first_manifest = manifest

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        assert manifest.id == first_manifest.id
        assert manifest.digest == first_manifest.digest
        assert proxy_mock.manifest_exists.call_count == 1
        assert proxy_mock.get_manifest.call_count == 0

    def test_does_not_bump_tag_expiration_when_manifest_is_cached_and_upstream_errors(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            UBI8_8_4_DIGEST, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        first_tag = Tag.get(manifest_id=manifest.id)

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            manifest = proxy_model.lookup_manifest_by_digest(repo_ref, UBI8_8_4_DIGEST)
        assert manifest is not None
        tag = Tag.get(manifest_id=manifest.id)
        assert tag.id == first_tag.id
        assert tag.lifetime_end_ms == first_tag.lifetime_end_ms


class TestRegistryProxyModelGetRepoTag:
    upstream_registry = "quay.io"  # alternatively, use quay.io/someorg
    upstream_repository = "app-sre/ubi8-ubi"
    orgname = "quayio-cache"
    repository = f"{orgname}/{upstream_repository}"
    tag = "latest"

    @pytest.fixture(autouse=True)
    def setup(self, app):
        self.user = get_user("devtable")
        self.org = create_organization(self.orgname, "{self.orgname}@devtable.com", self.user)
        self.org.save()
        self.config = create_proxy_cache_config(
            org_name=self.orgname,
            upstream_registry=self.upstream_registry,
            expiration_s=3600,
        )

    def test_caches_manifest_on_first_pull(self, create_repo, proxy_manifest_response):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.manifest is not None
        assert tag.manifest.internal_manifest_bytes.as_unicode() == UBI8_8_4_MANIFEST_SCHEMA2

    def test_updates_manifest_and_bumps_tag_expiration_when_upstream_manifest_changed(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_4_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.name == self.tag

        first_manifest = tag.manifest

        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.name == self.tag
        assert tag.manifest.id != first_manifest.id
        assert tag.manifest.digest == UBI8_8_5_DIGEST

    def test_renews_expired_tag_when_manifest_is_up_to_date_with_upstream(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.name == self.tag

        # expire the tag by setting start and end time to the past
        before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        ).where(Tag.id == tag.id).execute()

        expired_tag = tag

        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert expired_tag.id == tag.id
        assert expired_tag.manifest.id == tag.manifest.id
        assert not tag.expired
        new_expiration_ms = get_epoch_timestamp_ms() + self.config.expiration_s * 1000
        # subtract a some milliseconds so the test doesn't flake
        assert tag.lifetime_end_ms >= new_expiration_ms - 500

    def test_passes_through_upstream_error_when_image_isnt_cached(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            with pytest.raises(TagDoesNotExist):
                proxy_model.get_repo_tag(repo_ref, self.tag)

    def test_passes_through_upstream_error_when_local_cache_is_expired(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is not None

        # expire the tag by setting start and end time to the past
        before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        ).where(Tag.id == tag.id).execute()

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is None

    def test_returns_None_when_manifest_no_longer_exists_upstream_and_local_cache_is_expired(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is not None

        # expire the tag by setting start and end time to the past
        before_ms = get_epoch_timestamp_ms() - timedelta(hours=24).total_seconds() * 1000
        Tag.update(
            lifetime_start_ms=before_ms,
            lifetime_end_ms=before_ms + 5,
        ).where(Tag.id == tag.id).execute()

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is None

    def test_bumps_tag_expiration_when_upstream_is_alive_and_cache_is_up_to_date(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.name == self.tag

        first_tag = tag
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)

        assert tag is not None
        assert tag.lifetime_end_ms > first_tag.lifetime_end_ms

    def test_doesnt_bump_tag_expiration_when_upstream_is_dead(
        self, create_repo, proxy_manifest_response
    ):
        repo_ref = create_repo(self.orgname, self.upstream_repository, self.user)
        proxy_mock = proxy_manifest_response(
            self.tag, UBI8_8_5_MANIFEST_SCHEMA2, DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
        )
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is not None
        first_tag = tag

        proxy_mock = proxy_manifest_response("not-existing-ref", "", "")
        with patch(
            "data.registry_model.registry_proxy_model.Proxy", MagicMock(return_value=proxy_mock)
        ):
            proxy_model = ProxyModel(
                self.orgname,
                self.upstream_repository,
                self.user,
            )
            tag = proxy_model.get_repo_tag(repo_ref, self.tag)
        assert tag is not None
        assert tag.lifetime_end_ms == first_tag.lifetime_end_ms
