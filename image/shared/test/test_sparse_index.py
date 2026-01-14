"""
Unit tests for sparse manifest index functionality in LazyManifestLoader.

Tests the FEATURE_SPARSE_INDEX and SPARSE_INDEX_REQUIRED_ARCHS configuration options
which allow manifest lists/indexes to have optional architectures that can be missing.
"""

import json
import logging
from unittest.mock import patch

import pytest

from image.docker.schema2 import DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE
from image.docker.schema2.list import DockerSchema2ManifestList
from image.docker.schema2.manifest import DockerSchema2Manifest
from image.oci import OCI_IMAGE_INDEX_CONTENT_TYPE, OCI_IMAGE_MANIFEST_CONTENT_TYPE
from image.oci.index import OCIIndex
from image.oci.manifest import OCIManifest
from image.shared import ManifestException
from image.shared.schemautil import ContentRetrieverForTesting, LazyManifestLoader
from util.bytes import Bytes

# Docker Schema2 manifest bytes for testing (defined locally to avoid import chain)
DOCKER_SCHEMA2_MANIFEST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {
            "mediaType": "application/vnd.docker.container.image.v1+json",
            "size": 1234,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 1234,
                "digest": "sha256:ec4b8955958665577945c89419d1af06b5f7636b4ac3da7f12184802ad867736",
            },
            {
                "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                "size": 32654,
                "digest": "sha256:e692418e4cbaf90ca69d05a66403747baa33ee08806650b51fab815ad7fc331f",
            },
        ],
    }
).encode("utf-8")

# OCI manifest bytes for testing
OCI_MANIFEST_BYTES = json.dumps(
    {
        "schemaVersion": 2,
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "size": 7023,
            "digest": "sha256:b5b2b2c507a0944348e0303114d8d93aaaa081732b86451d9bce1f432a537bc7",
        },
        "layers": [
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 32654,
                "digest": "sha256:9834876dcfb05cb167a5c24953eba58c4ac89b1adf57f28f2f9d09af107ee8f0",
            },
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "size": 16724,
                "digest": "sha256:3c3a4604a545cdc127456d94e421cd355bca5b528f4a9c1905b15da2eb4a4c6b",
            },
        ],
    }
).encode("utf-8")


# Sample manifest data for testing
def create_manifest_data(
    digest="sha256:abc123",
    size=946,
    media_type=DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
    architecture=None,
    os="linux",
):
    """Create manifest data dict with optional platform info."""
    data = {
        "digest": digest,
        "size": size,
        "mediaType": media_type,
    }
    if architecture is not None:
        data["platform"] = {
            "architecture": architecture,
            "os": os,
        }
    return data


# Supported types for testing
SUPPORTED_TYPES = {
    DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE: DockerSchema2Manifest,
    OCI_IMAGE_MANIFEST_CONTENT_TYPE: OCIManifest,
}


class TestLazyManifestLoaderArchitecture:
    """Tests for the architecture property of LazyManifestLoader."""

    def test_architecture_with_platform_data(self):
        """Test architecture extraction when platform data is present."""
        manifest_data = create_manifest_data(architecture="amd64")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        assert loader.architecture == "amd64"

    def test_architecture_without_platform_data(self):
        """Test architecture returns None when no platform data exists."""
        manifest_data = create_manifest_data()  # No architecture
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        assert loader.architecture is None

    def test_architecture_with_empty_platform(self):
        """Test architecture returns None when platform dict is empty."""
        manifest_data = {
            "digest": "sha256:abc123",
            "size": 946,
            "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
            "platform": {},
        }
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        assert loader.architecture is None

    @pytest.mark.parametrize(
        "arch",
        [
            pytest.param("amd64", id="amd64"),
            pytest.param("arm64", id="arm64"),
            pytest.param("ppc64le", id="ppc64le"),
            pytest.param("s390x", id="s390x"),
            pytest.param("386", id="386"),
        ],
    )
    def test_architecture_various_values(self, arch):
        """Test architecture extraction for various architecture values."""
        manifest_data = create_manifest_data(architecture=arch)
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        assert loader.architecture == arch


class TestSparseIndexDisabled:
    """Tests for behavior when FEATURE_SPARSE_INDEX is disabled (default)."""

    def test_missing_manifest_raises_exception(self):
        """When sparse index is disabled, missing manifest raises exception."""
        manifest_data = create_manifest_data(architecture="amd64")
        retriever = ContentRetrieverForTesting()  # Empty - manifest not available

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={"FEATURE_SPARSE_INDEX": False},
        )

        with pytest.raises(ManifestException) as exc_info:
            _ = loader.manifest_obj

        assert "manifest not found" in str(exc_info.value)

    def test_missing_manifest_raises_without_config(self):
        """When config is not set, missing manifest raises exception (default behavior)."""
        manifest_data = create_manifest_data(architecture="arm64")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={},
        )

        with pytest.raises(ManifestException) as exc_info:
            _ = loader.manifest_obj

        assert "manifest not found" in str(exc_info.value)


class TestSparseIndexEnabled:
    """Tests for behavior when FEATURE_SPARSE_INDEX is enabled."""

    def test_optional_architecture_returns_none(self):
        """Optional architecture missing returns None instead of raising."""
        manifest_data = create_manifest_data(
            digest="sha256:missing",
            architecture="arm64",
        )
        retriever = ContentRetrieverForTesting()  # Empty

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],  # arm64 is optional
            },
        )

        result = loader.manifest_obj
        assert result is None

    def test_required_architecture_raises_exception(self):
        """Required architecture missing still raises exception."""
        manifest_data = create_manifest_data(
            digest="sha256:missing",
            architecture="amd64",
        )
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64", "arm64"],
            },
        )

        with pytest.raises(ManifestException) as exc_info:
            _ = loader.manifest_obj

        assert "manifest not found" in str(exc_info.value)
        assert "Required architectures:" in str(exc_info.value)

    def test_empty_required_archs_treats_all_as_required(self):
        """When SPARSE_INDEX_REQUIRED_ARCHS is empty, all architectures are required."""
        manifest_data = create_manifest_data(
            digest="sha256:missing",
            architecture="arm64",
        )
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": [],  # Empty list = all required
            },
        )

        with pytest.raises(ManifestException):
            _ = loader.manifest_obj

    def test_no_architecture_in_manifest_treats_as_required(self):
        """When manifest has no architecture specified, treat as required."""
        manifest_data = create_manifest_data()  # No architecture
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
            },
        )

        with pytest.raises(ManifestException):
            _ = loader.manifest_obj

    @pytest.mark.parametrize(
        "required_archs,manifest_arch,should_skip",
        [
            pytest.param(["amd64"], "arm64", True, id="arm64_optional_when_amd64_required"),
            pytest.param(["amd64"], "ppc64le", True, id="ppc64le_optional_when_amd64_required"),
            pytest.param(
                ["amd64", "arm64"], "s390x", True, id="s390x_optional_when_amd64_arm64_required"
            ),
            pytest.param(["amd64"], "amd64", False, id="amd64_required"),
            pytest.param(["arm64"], "arm64", False, id="arm64_required"),
            pytest.param(
                ["amd64", "arm64", "ppc64le"], "ppc64le", False, id="ppc64le_in_required_list"
            ),
        ],
    )
    def test_architecture_required_matrix(self, required_archs, manifest_arch, should_skip):
        """Test various combinations of required architectures and manifest architectures."""
        manifest_data = create_manifest_data(
            digest="sha256:missing",
            architecture=manifest_arch,
        )
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": required_archs,
            },
        )

        if should_skip:
            result = loader.manifest_obj
            assert result is None
        else:
            with pytest.raises(ManifestException):
                _ = loader.manifest_obj


class TestManifestLoadingCaching:
    """Tests for manifest loading caching behavior."""

    def test_manifest_obj_cached_after_first_load(self):
        """Test that manifest_obj is cached after first access."""
        manifest_data = create_manifest_data(
            digest="sha256:e6",
            size=len(DOCKER_SCHEMA2_MANIFEST_BYTES),
        )
        retriever = ContentRetrieverForTesting({"sha256:e6": DOCKER_SCHEMA2_MANIFEST_BYTES})

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        # First access
        manifest1 = loader.manifest_obj
        assert manifest1 is not None
        assert isinstance(manifest1, DockerSchema2Manifest)

        # Second access should return same object
        manifest2 = loader.manifest_obj
        assert manifest1 is manifest2

    def test_none_manifest_cached(self):
        """Test that None result is cached for optional architectures."""
        manifest_data = create_manifest_data(
            digest="sha256:missing",
            architecture="arm64",
        )
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
            },
        )

        # First access
        result1 = loader.manifest_obj
        assert result1 is None
        assert loader._load_attempted is True

        # Second access should not re-attempt loading
        result2 = loader.manifest_obj
        assert result2 is None

    def test_load_attempted_flag_set(self):
        """Test that _load_attempted flag is set after first access."""
        manifest_data = create_manifest_data(
            digest="sha256:e6",
            size=len(DOCKER_SCHEMA2_MANIFEST_BYTES),
        )
        retriever = ContentRetrieverForTesting({"sha256:e6": DOCKER_SCHEMA2_MANIFEST_BYTES})

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        assert loader._load_attempted is False
        _ = loader.manifest_obj
        assert loader._load_attempted is True


class TestManifestLoadingSuccess:
    """Tests for successful manifest loading scenarios."""

    def test_load_manifest_successfully(self):
        """Test successful manifest loading."""
        manifest_data = create_manifest_data(
            digest="sha256:e6",
            size=len(DOCKER_SCHEMA2_MANIFEST_BYTES),
            architecture="amd64",
        )
        retriever = ContentRetrieverForTesting({"sha256:e6": DOCKER_SCHEMA2_MANIFEST_BYTES})

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        manifest = loader.manifest_obj
        assert manifest is not None
        assert isinstance(manifest, DockerSchema2Manifest)
        assert manifest.schema_version == 2

    def test_load_manifest_size_mismatch_raises(self):
        """Test that size mismatch raises exception."""
        manifest_data = create_manifest_data(
            digest="sha256:e6",
            size=100,  # Wrong size
            architecture="amd64",
        )
        retriever = ContentRetrieverForTesting({"sha256:e6": DOCKER_SCHEMA2_MANIFEST_BYTES})

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        with pytest.raises(ManifestException) as exc_info:
            _ = loader.manifest_obj

        assert "Size of manifest does not match" in str(exc_info.value)

    def test_load_manifest_unsupported_media_type_raises(self):
        """Test that unsupported media type raises exception."""
        manifest_data = create_manifest_data(
            digest="sha256:e6",
            size=len(DOCKER_SCHEMA2_MANIFEST_BYTES),
            media_type="application/vnd.unknown.manifest+json",
        )
        retriever = ContentRetrieverForTesting({"sha256:e6": DOCKER_SCHEMA2_MANIFEST_BYTES})

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
        )

        with pytest.raises(ManifestException) as exc_info:
            _ = loader.manifest_obj

        assert "Unknown or unsupported manifest media type" in str(exc_info.value)


def create_docker_manifest_list_bytes():
    """Create a Docker Schema2 manifest list with multiple architectures."""
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
            "manifests": [
                {
                    "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                    "size": len(DOCKER_SCHEMA2_MANIFEST_BYTES),
                    "digest": "sha256:amd64manifest",
                    "platform": {
                        "architecture": "amd64",
                        "os": "linux",
                    },
                },
                {
                    "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                    "size": len(DOCKER_SCHEMA2_MANIFEST_BYTES),
                    "digest": "sha256:arm64manifest",
                    "platform": {
                        "architecture": "arm64",
                        "os": "linux",
                    },
                },
                {
                    "mediaType": DOCKER_SCHEMA2_MANIFEST_CONTENT_TYPE,
                    "size": len(DOCKER_SCHEMA2_MANIFEST_BYTES),
                    "digest": "sha256:ppc64lemanifest",
                    "platform": {
                        "architecture": "ppc64le",
                        "os": "linux",
                    },
                },
            ],
        }
    ).encode("utf-8")


def create_oci_index_bytes():
    """Create an OCI index with multiple architectures."""
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": OCI_IMAGE_INDEX_CONTENT_TYPE,
            "manifests": [
                {
                    "mediaType": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
                    "size": len(OCI_MANIFEST_BYTES),
                    "digest": "sha256:amd64manifest",
                    "platform": {
                        "architecture": "amd64",
                        "os": "linux",
                    },
                },
                {
                    "mediaType": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
                    "size": len(OCI_MANIFEST_BYTES),
                    "digest": "sha256:arm64manifest",
                    "platform": {
                        "architecture": "arm64",
                        "os": "linux",
                    },
                },
                {
                    "mediaType": OCI_IMAGE_MANIFEST_CONTENT_TYPE,
                    "size": len(OCI_MANIFEST_BYTES),
                    "digest": "sha256:ppc64lemanifest",
                    "platform": {
                        "architecture": "ppc64le",
                        "os": "linux",
                    },
                },
            ],
        }
    ).encode("utf-8")


class TestManifestListIndex:
    """Unit tests for sparse index with DockerSchema2ManifestList and OCIIndex."""

    @pytest.fixture(
        params=[
            pytest.param(
                (
                    DockerSchema2ManifestList,
                    create_docker_manifest_list_bytes,
                    DockerSchema2Manifest,
                    DOCKER_SCHEMA2_MANIFEST_BYTES,
                ),
                id="docker_schema2_manifest_list",
            ),
            pytest.param(
                (OCIIndex, create_oci_index_bytes, OCIManifest, OCI_MANIFEST_BYTES),
                id="oci_index",
            ),
        ]
    )
    def manifest_list_config(self, request):
        """Provide manifest list class, bytes factory, expected manifest type, and child manifest bytes."""
        return request.param

    def test_manifest_list_all_present(self, manifest_list_config):
        """Test manifest list/index when all manifests are present."""
        list_class, bytes_factory, manifest_class, child_manifest_bytes = manifest_list_config
        manifest_list_bytes = bytes_factory()

        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": child_manifest_bytes,
                "sha256:arm64manifest": child_manifest_bytes,
                "sha256:ppc64lemanifest": child_manifest_bytes,
            }
        )

        manifest_list = list_class(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        # Explicitly test with sparse index disabled (default behavior)
        with patch.object(model_config, "app_config", {"FEATURE_SPARSE_INDEX": False}):
            manifests = manifest_list.manifests(retriever)

            assert len(manifests) == 3
            for manifest in manifests:
                assert manifest.manifest_obj is not None

    def test_manifest_list_with_missing_optional_arch(self, manifest_list_config):
        """Test manifest list/index with sparse index allowing missing optional architectures."""
        list_class, bytes_factory, manifest_class, child_manifest_bytes = manifest_list_config
        manifest_list_bytes = bytes_factory()

        # Only provide amd64, arm64 and ppc64le are missing
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": child_manifest_bytes,
            }
        )

        manifest_list = list_class(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],  # Only amd64 is required
        }
        with patch.object(model_config, "app_config", app_config):
            manifests = manifest_list.manifests(retriever)
            assert len(manifests) == 3

            # Count loaded and skipped manifests
            loaded = [m for m in manifests if m.manifest_obj is not None]
            skipped = [m for m in manifests if m.manifest_obj is None]

            assert len(loaded) == 1  # amd64
            assert len(skipped) == 2  # arm64, ppc64le

    def test_manifest_list_missing_required_arch_raises(self, manifest_list_config):
        """Test that missing required architecture raises exception."""
        list_class, bytes_factory, manifest_class, child_manifest_bytes = manifest_list_config
        manifest_list_bytes = bytes_factory()

        # Only provide arm64, but amd64 is required
        retriever = ContentRetrieverForTesting(
            {
                "sha256:arm64manifest": child_manifest_bytes,
            }
        )

        manifest_list = list_class(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
        }
        with patch.object(model_config, "app_config", app_config):
            manifests = manifest_list.manifests(retriever)

            # Should raise when accessing the amd64 manifest
            with pytest.raises(ManifestException):
                for m in manifests:
                    if m.architecture == "amd64":
                        _ = m.manifest_obj

    def test_manifest_list_validate_skips_none_manifests(self, manifest_list_config):
        """Test that validation skips None manifests from sparse index."""
        list_class, bytes_factory, manifest_class, child_manifest_bytes = manifest_list_config
        manifest_list_bytes = bytes_factory()

        # Only provide amd64
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": child_manifest_bytes,
            }
        )

        manifest_list = list_class(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
        }
        with patch.object(model_config, "app_config", app_config):
            # Validation should not raise even though some manifests are None
            manifest_list.validate(retriever)


class TestIsArchitectureRequiredMethod:
    """Tests for the _is_architecture_required method."""

    def test_returns_true_when_sparse_disabled(self):
        """Returns True when FEATURE_SPARSE_INDEX is disabled."""
        manifest_data = create_manifest_data(architecture="arm64")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={"FEATURE_SPARSE_INDEX": False},
        )

        assert loader._is_architecture_required() is True

    def test_returns_true_when_no_required_archs(self):
        """Returns True when SPARSE_INDEX_REQUIRED_ARCHS is empty."""
        manifest_data = create_manifest_data(architecture="arm64")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": [],
            },
        )

        assert loader._is_architecture_required() is True

    def test_returns_true_when_no_architecture(self):
        """Returns True when manifest has no architecture specified."""
        manifest_data = create_manifest_data()  # No architecture
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
            },
        )

        assert loader._is_architecture_required() is True

    def test_returns_true_when_in_required_list(self):
        """Returns True when architecture is in required list."""
        manifest_data = create_manifest_data(architecture="amd64")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64", "arm64"],
            },
        )

        assert loader._is_architecture_required() is True

    def test_returns_false_when_not_in_required_list(self):
        """Returns False when architecture is not in required list."""
        manifest_data = create_manifest_data(architecture="ppc64le")
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64", "arm64"],
            },
        )

        assert loader._is_architecture_required() is False


class TestDebugLogging:
    """Tests for debug logging behavior."""

    def test_logs_debug_message_for_skipped_manifest(self, caplog):
        """Test that debug message is logged when manifest is skipped."""
        manifest_data = create_manifest_data(
            digest="sha256:testdigest",
            architecture="arm64",
        )
        retriever = ContentRetrieverForTesting()

        loader = LazyManifestLoader(
            manifest_data,
            retriever,
            SUPPORTED_TYPES,
            digest_key="digest",
            size_key="size",
            media_type_key="mediaType",
            app_config={
                "FEATURE_SPARSE_INDEX": True,
                "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
            },
        )

        with caplog.at_level(logging.DEBUG, logger="image.shared.schemautil"):
            result = loader.manifest_obj
            assert result is None

        assert "Skipping manifest with digest" in caplog.text
        assert "sha256:testdigest" in caplog.text
        assert "arm64" in caplog.text


class TestSparsePushScenarios:
    """Tests for sparse manifest push acceptance scenarios."""

    def test_sparse_manifest_push_accepted_when_enabled(self):
        """Test manifest list push succeeds with missing optional architectures when enabled."""
        manifest_list_bytes = create_docker_manifest_list_bytes()

        # Only provide amd64, arm64 and ppc64le are missing
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": DOCKER_SCHEMA2_MANIFEST_BYTES,
            }
        )

        manifest_list = DockerSchema2ManifestList(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
        }
        with patch.object(model_config, "app_config", app_config):
            # Validation should succeed (simulates push acceptance)
            manifest_list.validate(retriever)

            # Check that we can access all manifests without error
            manifests = manifest_list.manifests(retriever)
            assert len(manifests) == 3

            # amd64 should be loaded, arm64/ppc64le should be None
            for m in manifests:
                if m.architecture == "amd64":
                    assert m.manifest_obj is not None
                else:
                    assert m.manifest_obj is None

    def test_sparse_manifest_push_rejected_when_disabled(self):
        """Test manifest list push fails with missing architectures when disabled."""
        manifest_list_bytes = create_docker_manifest_list_bytes()

        # Only provide amd64, arm64 and ppc64le are missing
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": DOCKER_SCHEMA2_MANIFEST_BYTES,
            }
        )

        manifest_list = DockerSchema2ManifestList(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": False,
        }
        with patch.object(model_config, "app_config", app_config):
            # Accessing manifests should fail because arm64/ppc64le are missing
            # and all are required when sparse index is disabled
            manifests = manifest_list.manifests(retriever)
            with pytest.raises(ManifestException) as exc_info:
                for m in manifests:
                    _ = m.manifest_obj  # This triggers the load

            assert "manifest not found" in str(exc_info.value)

    def test_required_architecture_must_exist(self):
        """Test push fails when required architecture is missing."""
        manifest_list_bytes = create_docker_manifest_list_bytes()

        # Provide arm64 and ppc64le, but NOT amd64 (required)
        retriever = ContentRetrieverForTesting(
            {
                "sha256:arm64manifest": DOCKER_SCHEMA2_MANIFEST_BYTES,
                "sha256:ppc64lemanifest": DOCKER_SCHEMA2_MANIFEST_BYTES,
            }
        )

        manifest_list = DockerSchema2ManifestList(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],  # amd64 is required but missing
        }
        with patch.object(model_config, "app_config", app_config):
            # Accessing manifests should fail because amd64 is required but missing
            manifests = manifest_list.manifests(retriever)
            with pytest.raises(ManifestException) as exc_info:
                for m in manifests:
                    _ = m.manifest_obj  # This triggers the load

            assert "amd64" in str(exc_info.value)
            assert "manifest not found" in str(exc_info.value)

    def test_digest_preserved_for_sparse_manifest(self):
        """Test manifest list digest matches original after sparse push."""
        manifest_list_bytes = create_docker_manifest_list_bytes()

        # Only provide amd64
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": DOCKER_SCHEMA2_MANIFEST_BYTES,
            }
        )

        manifest_list = DockerSchema2ManifestList(Bytes.for_string_or_unicode(manifest_list_bytes))

        # Record the original digest before any operations
        original_digest = manifest_list.digest

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
        }
        with patch.object(model_config, "app_config", app_config):
            # Validate (simulates push acceptance)
            manifest_list.validate(retriever)

            # Access manifests to trigger loading
            manifests = manifest_list.manifests(retriever)
            for m in manifests:
                _ = m.manifest_obj

            # Verify digest is unchanged after accessing manifests
            assert manifest_list.digest == original_digest

            # Verify bytes are unchanged
            assert manifest_list.bytes.as_encoded_str() == manifest_list_bytes

    def test_oci_sparse_index_push_accepted_when_enabled(self):
        """Test OCI index push succeeds with missing optional architectures when enabled."""
        oci_index_bytes = create_oci_index_bytes()

        # Only provide amd64
        retriever = ContentRetrieverForTesting(
            {
                "sha256:amd64manifest": OCI_MANIFEST_BYTES,
            }
        )

        oci_index = OCIIndex(Bytes.for_string_or_unicode(oci_index_bytes))

        # Import the config module before patching
        from data.model import config as model_config

        app_config = {
            "FEATURE_SPARSE_INDEX": True,
            "SPARSE_INDEX_REQUIRED_ARCHS": ["amd64"],
        }
        with patch.object(model_config, "app_config", app_config):
            # Validation should succeed
            oci_index.validate(retriever)

            # Check manifests
            manifests = oci_index.manifests(retriever)
            assert len(manifests) == 3

            # amd64 should be loaded, others should be None
            loaded = [m for m in manifests if m.manifest_obj is not None]
            skipped = [m for m in manifests if m.manifest_obj is None]
            assert len(loaded) == 1
            assert len(skipped) == 2
