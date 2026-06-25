import json

import pytest

from workers.repomirrorworker.manifest_utils import (
    DEFAULT_MAX_MANIFEST_ENTRIES,
    DEFAULT_MAX_MANIFEST_LIST_SIZE,
    ManifestSizeLimitExceeded,
    _check_manifest_size,
    filter_manifests_by_architecture,
    get_available_architectures,
    get_manifest_media_type,
    is_manifest_list,
)

SAMPLE_DOCKER_MANIFEST_LIST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
        "manifests": [
            {
                "digest": "sha256:amd64digest",
                "size": 1234,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            {
                "digest": "sha256:arm64digest",
                "size": 1234,
                "platform": {"architecture": "arm64", "os": "linux"},
            },
            {
                "digest": "sha256:ppc64ledigest",
                "size": 1234,
                "platform": {"architecture": "ppc64le", "os": "linux"},
            },
        ],
    }
)

SAMPLE_OCI_IMAGE_INDEX = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.index.v1+json",
        "manifests": [
            {
                "digest": "sha256:ociAmd64",
                "size": 1000,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
            {
                "digest": "sha256:ociArm64",
                "size": 1000,
                "platform": {"architecture": "arm64", "os": "linux"},
            },
        ],
    }
)

SAMPLE_OCI_INDEX_WITHOUT_MEDIATYPE = json.dumps(
    {
        "schemaVersion": 2,
        "manifests": [
            {
                "digest": "sha256:noMediaTypeAmd64",
                "size": 500,
                "platform": {"architecture": "amd64", "os": "linux"},
            },
        ],
    }
)

SAMPLE_SINGLE_MANIFEST = json.dumps(
    {
        "schemaVersion": 2,
        "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
        "config": {"mediaType": "application/vnd.docker.container.image.v1+json"},
        "layers": [],
    }
)


class TestIsManifestList:
    def test_docker_manifest_list(self):
        assert is_manifest_list(SAMPLE_DOCKER_MANIFEST_LIST) is True

    def test_oci_image_index(self):
        assert is_manifest_list(SAMPLE_OCI_IMAGE_INDEX) is True

    def test_oci_index_without_mediatype(self):
        """OCI index may not have mediaType but has manifests array."""
        assert is_manifest_list(SAMPLE_OCI_INDEX_WITHOUT_MEDIATYPE) is True

    def test_single_manifest(self):
        assert is_manifest_list(SAMPLE_SINGLE_MANIFEST) is False

    def test_invalid_json(self):
        assert is_manifest_list("not valid json") is False

    def test_empty_string(self):
        assert is_manifest_list("") is False

    def test_none_value(self):
        with pytest.raises(ValueError):
            is_manifest_list(None)


class TestGetManifestMediaType:
    def test_docker_manifest_list(self):
        result = get_manifest_media_type(SAMPLE_DOCKER_MANIFEST_LIST)
        assert result == "application/vnd.docker.distribution.manifest.list.v2+json"

    def test_oci_image_index(self):
        result = get_manifest_media_type(SAMPLE_OCI_IMAGE_INDEX)
        assert result == "application/vnd.oci.image.index.v1+json"

    def test_single_manifest(self):
        result = get_manifest_media_type(SAMPLE_SINGLE_MANIFEST)
        assert result == "application/vnd.docker.distribution.manifest.v2+json"

    def test_no_mediatype(self):
        result = get_manifest_media_type(SAMPLE_OCI_INDEX_WITHOUT_MEDIATYPE)
        assert result is None

    def test_invalid_json(self):
        result = get_manifest_media_type("not valid json")
        assert result is None


class TestFilterManifestsByArchitecture:
    def test_filter_single_architecture(self):
        filtered = filter_manifests_by_architecture(SAMPLE_DOCKER_MANIFEST_LIST, ["amd64"])
        assert len(filtered) == 1
        assert filtered[0]["digest"] == "sha256:amd64digest"
        assert filtered[0]["platform"]["architecture"] == "amd64"

    def test_filter_multiple_architectures(self):
        filtered = filter_manifests_by_architecture(SAMPLE_DOCKER_MANIFEST_LIST, ["amd64", "arm64"])
        assert len(filtered) == 2
        archs = [m["platform"]["architecture"] for m in filtered]
        assert "amd64" in archs
        assert "arm64" in archs
        assert "ppc64le" not in archs

    def test_filter_all_architectures(self):
        filtered = filter_manifests_by_architecture(
            SAMPLE_DOCKER_MANIFEST_LIST, ["amd64", "arm64", "ppc64le"]
        )
        assert len(filtered) == 3

    def test_filter_nonexistent_architecture(self):
        filtered = filter_manifests_by_architecture(SAMPLE_DOCKER_MANIFEST_LIST, ["s390x"])
        assert len(filtered) == 0

    def test_filter_mixed_existing_nonexistent(self):
        filtered = filter_manifests_by_architecture(
            SAMPLE_DOCKER_MANIFEST_LIST, ["amd64", "s390x", "arm64"]
        )
        assert len(filtered) == 2
        archs = [m["platform"]["architecture"] for m in filtered]
        assert set(archs) == {"amd64", "arm64"}

    def test_filter_empty_architectures_list(self):
        filtered = filter_manifests_by_architecture(SAMPLE_DOCKER_MANIFEST_LIST, [])
        assert len(filtered) == 0

    def test_filter_invalid_json(self):
        filtered = filter_manifests_by_architecture("not valid json", ["amd64"])
        assert len(filtered) == 0

    def test_filter_oci_index(self):
        filtered = filter_manifests_by_architecture(SAMPLE_OCI_IMAGE_INDEX, ["arm64"])
        assert len(filtered) == 1
        assert filtered[0]["digest"] == "sha256:ociArm64"


class TestGetAvailableArchitectures:
    def test_docker_manifest_list(self):
        archs = get_available_architectures(SAMPLE_DOCKER_MANIFEST_LIST)
        assert set(archs) == {"amd64", "arm64", "ppc64le"}

    def test_oci_image_index(self):
        archs = get_available_architectures(SAMPLE_OCI_IMAGE_INDEX)
        assert set(archs) == {"amd64", "arm64"}

    def test_single_manifest(self):
        """Single manifests have no architectures array."""
        archs = get_available_architectures(SAMPLE_SINGLE_MANIFEST)
        assert archs == []

    def test_invalid_json(self):
        archs = get_available_architectures("not valid json")
        assert archs == []

    def test_empty_manifests_array(self):
        empty_list = json.dumps(
            {
                "schemaVersion": 2,
                "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
                "manifests": [],
            }
        )
        archs = get_available_architectures(empty_list)
        assert archs == []


def _make_manifest_list(num_entries):
    """Helper to create a manifest list JSON string with N entries."""
    manifests = [
        {
            "digest": f"sha256:{i:064x}",
            "size": 1234,
            "platform": {"architecture": f"arch{i}", "os": "linux"},
        }
        for i in range(num_entries)
    ]
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.list.v2+json",
            "manifests": manifests,
        }
    )


class TestManifestSizeValidation:
    def test_is_manifest_list_raises_on_oversized(self):
        """is_manifest_list raises ManifestSizeLimitExceeded when manifest exceeds max_size."""
        with pytest.raises(ManifestSizeLimitExceeded):
            is_manifest_list(SAMPLE_DOCKER_MANIFEST_LIST, max_size=10)

    def test_is_manifest_list_accepts_within_limit(self):
        size = len(SAMPLE_DOCKER_MANIFEST_LIST)
        assert is_manifest_list(SAMPLE_DOCKER_MANIFEST_LIST, max_size=size) is True

    def test_filter_raises_on_oversized_manifest(self):
        with pytest.raises(ManifestSizeLimitExceeded):
            filter_manifests_by_architecture(SAMPLE_DOCKER_MANIFEST_LIST, ["amd64"], max_size=10)

    def test_filter_accepts_within_size_limit(self):
        size = len(SAMPLE_DOCKER_MANIFEST_LIST)
        result = filter_manifests_by_architecture(
            SAMPLE_DOCKER_MANIFEST_LIST, ["amd64"], max_size=size
        )
        assert len(result) == 1

    def test_get_available_architectures_raises_on_oversized(self):
        with pytest.raises(ManifestSizeLimitExceeded):
            get_available_architectures(SAMPLE_DOCKER_MANIFEST_LIST, max_size=10)

    def test_get_available_architectures_accepts_within_limit(self):
        size = len(SAMPLE_DOCKER_MANIFEST_LIST)
        result = get_available_architectures(SAMPLE_DOCKER_MANIFEST_LIST, max_size=size)
        assert set(result) == {"amd64", "arm64", "ppc64le"}


class TestManifestEntryCountValidation:
    def test_filter_truncates_excess_entries(self):
        manifest = _make_manifest_list(10)
        # Request all architectures but limit to 3 entries
        all_archs = [f"arch{i}" for i in range(10)]
        result = filter_manifests_by_architecture(manifest, all_archs, max_entries=3)
        assert len(result) == 3

    def test_filter_allows_entries_at_limit(self):
        manifest = _make_manifest_list(5)
        all_archs = [f"arch{i}" for i in range(5)]
        result = filter_manifests_by_architecture(manifest, all_archs, max_entries=5)
        assert len(result) == 5

    def test_get_available_architectures_truncates_excess(self):
        manifest = _make_manifest_list(10)
        result = get_available_architectures(manifest, max_entries=3)
        assert len(result) == 3

    def test_get_available_architectures_at_limit(self):
        manifest = _make_manifest_list(5)
        result = get_available_architectures(manifest, max_entries=5)
        assert len(result) == 5

    def test_default_constants_are_sensible(self):
        assert DEFAULT_MAX_MANIFEST_LIST_SIZE == 10 * 1024 * 1024
        assert DEFAULT_MAX_MANIFEST_ENTRIES == 1000


class TestCheckManifestSize:
    def test_uses_character_length_not_utf8_bytes(self):
        """_check_manifest_size uses len(str) (character count), not UTF-8 byte length."""
        # Multi-byte chars: each is 3 UTF-8 bytes but 1 character
        payload = "\u2603" * 10  # 10 chars, 30 UTF-8 bytes
        # Should pass with a limit of 10 (character count)
        _check_manifest_size(payload, max_size=10)
        # Should raise with a limit of 9
        with pytest.raises(ManifestSizeLimitExceeded):
            _check_manifest_size(payload, max_size=9)

    def test_raises_value_error_on_none(self):
        with pytest.raises(ValueError):
            _check_manifest_size(None, max_size=100)

    def test_raises_on_oversized(self):
        with pytest.raises(ManifestSizeLimitExceeded):
            _check_manifest_size("x" * 100, max_size=10)

    def test_passes_within_limit(self):
        _check_manifest_size("x" * 10, max_size=10)
