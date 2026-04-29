import base64
import gzip
import io
import json
import tarfile
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
import yaml

from data.database import HelmChartMetadata, Manifest, Repository
from data.model.repository import create_repository
from test.fixtures import *
from workers.helmchartworker.extractor import (
    HELM_CHART_CONFIG_TYPE,
    HELM_CHART_CONTENT_LAYER_TYPES,
    HelmExtractionError,
    _assemble_pullspec,
    _extract_images_from_values,
    _extract_provenance_metadata,
    _is_image_key,
    extract_helm_chart_metadata,
)


@contextmanager
def _mock_blob_storage(mock_storage, blobs):
    """
    Context manager replacing RepositoryContentRetriever-based mocking with
    get_repository_blob_by_digest + storage.get_content.

    Args:
        mock_storage: The MagicMock storage object passed to extract_helm_chart_metadata.
        blobs: One of:
            - bytes: Every call to get_repository_blob_by_digest returns a blob record
              and storage.get_content returns these bytes.
            - None: get_repository_blob_by_digest returns None (blob not found).
            - dict[str, bytes | None]: Maps digest → content.  A None value means
              that specific blob is not found. An Exception value is raised.
            - Exception: get_repository_blob_by_digest raises the exception.
    """
    with (
        patch("workers.helmchartworker.extractor.get_repository_blob_by_digest") as mock_get_blob,
        patch("workers.helmchartworker.extractor.get_layer_path") as mock_get_path,
    ):
        mock_get_path.return_value = "layer/path"

        if blobs is None:
            mock_get_blob.return_value = None
        elif isinstance(blobs, Exception):
            mock_get_blob.side_effect = blobs
        elif isinstance(blobs, bytes):
            blob_record = MagicMock()
            blob_record.image_size = len(blobs)
            blob_record.locations = {"local"}
            mock_get_blob.return_value = blob_record
            mock_storage.get_content.return_value = blobs
        elif isinstance(blobs, dict):
            records = {}
            content_map = {}
            path_counter = [0]
            for digest, data in blobs.items():
                if data is None:
                    records[digest] = None
                elif isinstance(data, Exception):
                    records[digest] = data
                else:
                    path_counter[0] += 1
                    path = f"layer/path/{path_counter[0]}"
                    rec = MagicMock()
                    rec.image_size = len(data)
                    rec.locations = {"local"}
                    records[digest] = rec
                    content_map[id(rec)] = data

            def blob_side_effect(_repo_id, digest):
                val = records.get(digest)
                if isinstance(val, Exception):
                    raise val
                return val

            def content_side_effect(locations, path):
                for rec_id, data in content_map.items():
                    for digest, rec in records.items():
                        if not isinstance(rec, Exception) and rec is not None and id(rec) == rec_id:
                            if mock_get_blob.call_args_list:
                                last_digest = mock_get_blob.call_args_list[-1][0][1]
                                if last_digest == digest:
                                    return data
                return None

            mock_get_blob.side_effect = blob_side_effect
            mock_storage.get_content.side_effect = content_side_effect

        yield mock_get_blob


def _make_chart_yaml(name="testchart", version="1.0.0", api_version="v2", **extra):
    data = {
        "apiVersion": api_version,
        "name": name,
        "version": version,
        "description": "A test Helm chart",
    }
    data.update(extra)
    return yaml.dump(data).encode("utf-8")


def _make_tar_gz(files):
    """
    Create a tar.gz archive in memory from a dict of {path: bytes_content}.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            info = tarfile.TarInfo(name=path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def _make_manifest_json(chart_layer_digest, chart_layer_size, provenance_digest=None):
    layers = [
        {
            "mediaType": "application/vnd.cncf.helm.chart.content.v1.tar+gzip",
            "digest": chart_layer_digest,
            "size": chart_layer_size,
        }
    ]
    if provenance_digest:
        layers.append(
            {
                "mediaType": "application/vnd.cncf.helm.chart.provenance.v1.prov",
                "digest": provenance_digest,
                "size": 100,
            }
        )
    return json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": HELM_CHART_CONFIG_TYPE,
                "digest": "sha256:abc123",
                "size": 100,
            },
            "layers": layers,
        }
    )


def _create_test_manifest(initialized_db, manifest_bytes):
    """Create a real Manifest row in the test DB."""
    repo = create_repository("devtable", "helmtestrepo", None)
    manifest_row = Manifest.create(
        repository=repo,
        digest="sha256:fakedigest0001",
        media_type=Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        ),
        manifest_bytes=manifest_bytes,
        config_media_type=HELM_CHART_CONFIG_TYPE,
        layers_compressed_size=0,
    )
    return repo, manifest_row


class TestExtractHelmChartMetadata:
    def test_valid_minimal_chart(self, initialized_db):
        """A chart with only Chart.yaml produces a completed row."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer001", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.chart_name == "testchart"
        assert row.chart_version == "1.0.0"
        assert row.api_version == "v2"
        assert row.readme is None
        assert row.values_yaml is None
        assert row.extraction_error is None

    def test_valid_full_chart(self, initialized_db):
        """A chart with all optional files populates all fields."""
        chart_yaml = _make_chart_yaml(
            appVersion="2.0.0",
            keywords=["web", "proxy"],
            maintainers=[{"name": "Test User", "email": "test@example.com"}],
            dependencies=[
                {"name": "common", "version": "1.x", "repository": "https://charts.example.com"}
            ],
            sources=["https://github.com/example/chart"],
            home="https://example.com",
            kubeVersion=">=1.20.0",
            type="application",
        )
        values_yaml = b"replicaCount: 1\nimage:\n  repository: nginx\n  tag: latest\n"
        readme = b"# My Chart\n\nA test chart for testing.\n"
        values_schema = json.dumps(
            {"type": "object", "properties": {"replicaCount": {"type": "integer"}}}
        ).encode("utf-8")
        template = b"apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - image: '{{ .Values.image.repository }}:{{ .Values.image.tag }}'\n"

        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
                "testchart/README.md": readme,
                "testchart/values.schema.json": values_schema,
                "testchart/templates/deployment.yaml": template,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer002", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.chart_name == "testchart"
        assert row.app_version == "2.0.0"
        assert row.readme is not None
        assert "My Chart" in row.readme
        assert row.values_yaml is not None
        assert "replicaCount" in row.values_yaml
        assert row.values_schema_json is not None
        assert row.kube_version == ">=1.20.0"
        assert row.chart_type == "application"
        assert row.home == "https://example.com"
        assert len(row.keywords) == 2
        assert len(row.maintainers) == 1
        assert len(row.chart_dependencies) == 1
        assert len(row.sources) == 1
        assert len(row.file_tree) == 5
        assert any(ref["image"] == "nginx:latest" for ref in row.image_references)

    def test_missing_chart_yaml(self, initialized_db):
        """A tar without Chart.yaml writes a failed row."""
        tar_data = _make_tar_gz({"testchart/values.yaml": b"key: value\n"})
        manifest_bytes = _make_manifest_json("sha256:chartlayer003", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "Chart.yaml not found" in row.extraction_error

    def test_oversized_layer(self, initialized_db):
        """A layer exceeding HELM_CHART_MAX_LAYER_SIZE writes a failed row."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer004", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.app") as mock_app,
        ):
            mock_app.config.get.side_effect = lambda key, default=None: (
                10 if key == "HELM_CHART_MAX_LAYER_SIZE" else default
            )
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "exceeds limit" in row.extraction_error

    def test_corrupt_archive(self, initialized_db):
        """Invalid gzip data writes a failed row, no exception propagated."""
        corrupt_data = b"this is not a tar.gz file at all"
        manifest_bytes = _make_manifest_json("sha256:chartlayer005", len(corrupt_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, corrupt_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "corrupt" in row.extraction_error or "invalid" in row.extraction_error

    def test_invalid_chart_yaml(self, initialized_db):
        """Chart.yaml with missing mandatory fields writes a failed row."""
        bad_chart = yaml.dump({"name": "test"}).encode("utf-8")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": bad_chart})
        manifest_bytes = _make_manifest_json("sha256:chartlayer006", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "missing mandatory field" in row.extraction_error

    def test_icon_download_failure_does_not_fail_extraction(self, initialized_db):
        """A failed icon download leaves icon_data null but extraction succeeds."""
        chart_yaml = _make_chart_yaml(icon="https://example.com/icon.png")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer007", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.validate_external_registry_url"),
            patch("workers.helmchartworker.extractor.requests.get") as mock_get,
        ):
            mock_get.side_effect = Exception("connection timeout")
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.icon_data is None
        assert row.icon_media_type is None
        assert row.icon_url == "https://example.com/icon.png"

    def test_successful_icon_download(self, initialized_db):
        """A successful icon download stores base64 data."""
        chart_yaml = _make_chart_yaml(icon="https://example.com/icon.png")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer008", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        icon_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.iter_content.return_value = [icon_bytes]
        mock_response.raise_for_status = MagicMock()
        mock_response.is_redirect = False
        mock_response.is_permanent_redirect = False

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.validate_external_registry_url"),
            patch("workers.helmchartworker.extractor.requests.get") as mock_get,
        ):
            mock_get.return_value = mock_response
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.icon_data == base64.b64encode(icon_bytes).decode("ascii")
        assert row.icon_media_type == "image/png"

    def test_provenance_layer(self, initialized_db):
        """Provenance layer content is stored when present."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        prov_content = b"-----BEGIN PGP SIGNED MESSAGE-----\nhash: SHA256\nchart content\n"
        manifest_bytes = _make_manifest_json(
            "sha256:chartlayer009", len(tar_data), provenance_digest="sha256:provlayer001"
        )
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(
            mock_storage,
            {
                "sha256:chartlayer009": tar_data,
                "sha256:provlayer001": prov_content,
            },
        ):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.provenance is not None
        assert "PGP SIGNED" in row.provenance

    def test_blob_not_found(self, initialized_db):
        """Missing blob in storage writes a failed row."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer010", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, None):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "not found" in row.extraction_error

    def test_file_tree_construction(self, initialized_db):
        """File tree contains correct paths and sizes."""
        chart_yaml = _make_chart_yaml()
        values = b"key: value\n"
        template = b"apiVersion: v1\nkind: ConfigMap\n"
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values,
                "testchart/templates/configmap.yaml": template,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer011", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        paths = [f["path"] for f in row.file_tree]
        assert "testchart/Chart.yaml" in paths
        assert "testchart/values.yaml" in paths
        assert "testchart/templates/configmap.yaml" in paths

    def test_idempotency(self, initialized_db):
        """Running extraction twice does not create duplicate rows."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer012", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        count = (
            HelmChartMetadata.select().where(HelmChartMetadata.manifest == manifest_row.id).count()
        )
        assert count == 1

    def test_path_traversal_rejected(self, initialized_db):
        """Tar entries with path traversal are rejected with a failed row."""
        chart_yaml = _make_chart_yaml()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="testchart/Chart.yaml")
            info.size = len(chart_yaml)
            tar.addfile(info, io.BytesIO(chart_yaml))
            malicious = b"malicious"
            info2 = tarfile.TarInfo(name="../../../etc/passwd")
            info2.size = len(malicious)
            tar.addfile(info2, io.BytesIO(malicious))
        tar_data = buf.getvalue()

        manifest_bytes = _make_manifest_json("sha256:chartlayer013", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "path traversal" in row.extraction_error

    def test_unexpected_exception_writes_failed_row(self, initialized_db):
        """An unexpected exception during extraction still writes a failed row."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer014", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, RuntimeError("db exploded")):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "unexpected error" in row.extraction_error

    def test_oversized_optional_file_skipped(self, initialized_db):
        """An oversized optional file (README) is skipped, extraction still succeeds."""
        chart_yaml = _make_chart_yaml()
        huge_readme = b"x" * 2048
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/README.md": huge_readme,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer015", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.app") as mock_app,
        ):
            mock_app.config.get.side_effect = lambda key, default=None: (
                1024 if key == "HELM_CHART_MAX_EXTRACTED_FILE_SIZE" else default
            )
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.readme is None

    def test_image_extraction_structured(self, initialized_db):
        """Image references are extracted from structured values.yaml entries."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "image": {
                    "registry": "registry.example.com",
                    "repository": "myapp",
                    "tag": "v1.2.3",
                },
                "sidecar": {
                    "image": {
                        "registry": "docker.io",
                        "repository": "library/busybox",
                        "tag": "latest",
                    }
                },
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer016", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert "registry.example.com/myapp:v1.2.3" in images
        assert "docker.io/library/busybox:latest" in images

    def test_image_extraction_pullspec_string(self, initialized_db):
        """Full pull-spec strings under image keys are detected."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "image": "quay.io/organization/myrepo:v2.0.0",
                "initImage": "gcr.io/project/init-container:1.0",
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer017", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert "quay.io/organization/myrepo:v2.0.0" in images
        assert "gcr.io/project/init-container:1.0" in images

    def test_image_extraction_digest_reference(self, initialized_db):
        """Digest-based image references are extracted correctly."""
        digest = "sha256:" + "a" * 64
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "image": {
                    "registry": "quay.io",
                    "repository": "org/app",
                    "digest": digest,
                },
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer018", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert f"quay.io/org/app@{digest}" in images

    def test_image_extraction_pullspec_with_digest(self, initialized_db):
        """Full pull-spec string with digest reference is detected."""
        digest = "sha256:" + "b" * 64
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "image": f"registry.example.com/org/repo@{digest}",
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer019", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert f"registry.example.com/org/repo@{digest}" in images

    def test_image_extraction_nested_components(self, initialized_db):
        """Images under deeply nested component keys are found."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "frontend": {
                    "deployment": {
                        "image": {
                            "repository": "nginx",
                            "tag": "1.25-alpine",
                        }
                    }
                },
                "backend": {
                    "image": {
                        "registry": "ghcr.io",
                        "repository": "org/backend/api",
                        "tag": "v3.1",
                    }
                },
                "global": {
                    "image": {
                        "registry": "quay.io",
                        "repository": "org/sidecar",
                        "tag": "latest",
                    }
                },
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer020", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert "nginx:1.25-alpine" in images
        assert "ghcr.io/org/backend/api:v3.1" in images
        assert "quay.io/org/sidecar:latest" in images

    def test_image_extraction_no_values(self, initialized_db):
        """Charts without values.yaml produce an empty image list."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer021", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.image_references == []

    def test_image_extraction_deduplication(self, initialized_db):
        """Duplicate image references are deduplicated."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "primary": {
                    "image": {
                        "registry": "docker.io",
                        "repository": "library/nginx",
                        "tag": "1.25",
                    }
                },
                "secondary": {
                    "image": {
                        "registry": "docker.io",
                        "repository": "library/nginx",
                        "tag": "1.25",
                    }
                },
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer022", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert images.count("docker.io/library/nginx:1.25") == 1

    def test_image_extraction_multi_path_repo(self, initialized_db):
        """Repository paths with multiple separators are handled."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "image": "us-docker.pkg.dev/project/team/subdir/app:v1.0",
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer023", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        images = [ref["image"] for ref in row.image_references]
        assert "us-docker.pkg.dev/project/team/subdir/app:v1.0" in images

    def test_image_extraction_source_path(self, initialized_db):
        """Image references include the dotted YAML path as source."""
        chart_yaml = _make_chart_yaml()
        values_yaml = yaml.dump(
            {
                "web": {
                    "image": {
                        "repository": "nginx",
                        "tag": "stable",
                    }
                }
            }
        ).encode("utf-8")
        tar_data = _make_tar_gz(
            {
                "testchart/Chart.yaml": chart_yaml,
                "testchart/values.yaml": values_yaml,
            }
        )
        manifest_bytes = _make_manifest_json("sha256:chartlayer024", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        ref = next(r for r in row.image_references if r["image"] == "nginx:stable")
        assert ref["source"] == "web.image"

    def test_manifest_not_found(self, initialized_db):
        """Extraction for a non-existent manifest ID does not raise."""
        mock_storage = MagicMock()
        # Should not raise -- the function handles the error internally.
        # The failed row write itself may fail due to FK constraint, which is
        # also caught by the top-level exception handler.
        extract_helm_chart_metadata(999999, 1, mock_storage)
        count = HelmChartMetadata.select().where(HelmChartMetadata.manifest == 999999).count()
        # Row may or may not exist depending on FK enforcement; the key
        # assertion is that no exception propagates to the caller.
        assert count <= 1

    def test_cache_invalidation_on_success(self, initialized_db):
        """Successful extraction invalidates the helm repo index cache."""
        import features

        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayercache01", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        mock_cache = MagicMock()
        mock_cache.cache_config = {}

        original = features.HELM_REPO_INDEX
        try:
            features.HELM_REPO_INDEX = True
            with (
                _mock_blob_storage(mock_storage, tar_data),
                patch("app.model_cache", mock_cache),
            ):
                extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)
        finally:
            features.HELM_REPO_INDEX = original

        mock_cache.invalidate.assert_called_once()
        cache_key_arg = mock_cache.invalidate.call_args[0][0]
        assert f"helm_repo_index__{repo.id}" in cache_key_arg.key

    def test_cache_invalidation_on_failure(self, initialized_db):
        """Failed extraction also invalidates the cache (status row changed)."""
        import features

        tar_data = _make_tar_gz({"testchart/values.yaml": b"key: value\n"})
        manifest_bytes = _make_manifest_json("sha256:chartlayercache02", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        mock_cache = MagicMock()
        mock_cache.cache_config = {}

        original = features.HELM_REPO_INDEX
        try:
            features.HELM_REPO_INDEX = True
            with (
                _mock_blob_storage(mock_storage, tar_data),
                patch("app.model_cache", mock_cache),
            ):
                extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)
        finally:
            features.HELM_REPO_INDEX = original

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        mock_cache.invalidate.assert_called_once()

    def test_icon_unsupported_content_type(self, initialized_db):
        """An icon with an unsupported content-type is silently skipped."""
        chart_yaml = _make_chart_yaml(icon="https://example.com/icon.svg")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer_iconct", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.raise_for_status = MagicMock()
        mock_response.is_redirect = False
        mock_response.is_permanent_redirect = False

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.validate_external_registry_url"),
            patch("workers.helmchartworker.extractor.requests.get") as mock_get,
        ):
            mock_get.return_value = mock_response
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.icon_data is None
        assert row.icon_media_type is None

    def test_icon_exceeds_max_size(self, initialized_db):
        """An icon that exceeds the size limit mid-stream is silently skipped."""
        chart_yaml = _make_chart_yaml(icon="https://example.com/huge-icon.png")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer_iconbig", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.raise_for_status = MagicMock()
        mock_response.is_redirect = False
        mock_response.is_permanent_redirect = False
        mock_response.iter_content.return_value = [b"x" * 2048]

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(mock_storage, tar_data),
            patch("workers.helmchartworker.extractor.validate_external_registry_url"),
            patch("workers.helmchartworker.extractor.requests.get") as mock_get,
            patch("workers.helmchartworker.extractor.app") as mock_app,
        ):
            mock_app.config.get.side_effect = lambda key, default=None: (
                1024 if key == "HELM_CHART_MAX_ICON_SIZE" else default
            )
            mock_get.return_value = mock_response
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.icon_data is None
        assert row.icon_media_type is None

    def test_no_helm_content_layer(self, initialized_db):
        """A manifest with only non-chart layers writes a failed row."""
        manifest_json = json.dumps(
            {
                "schemaVersion": 2,
                "config": {
                    "mediaType": HELM_CHART_CONFIG_TYPE,
                    "digest": "sha256:abc123",
                    "size": 100,
                },
                "layers": [
                    {
                        "mediaType": "application/vnd.cncf.helm.chart.provenance.v1.prov",
                        "digest": "sha256:provonly001",
                        "size": 50,
                    }
                ],
            }
        )
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_json)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, b""):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "no Helm chart content layer" in row.extraction_error

    def test_oversized_provenance_layer_skipped(self, initialized_db):
        """A provenance layer exceeding max_file_size is skipped; extraction succeeds."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json(
            "sha256:chartlayer_provbig", len(tar_data), provenance_digest="sha256:bigprov001"
        )
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        huge_prov = b"x" * 2048

        mock_storage = MagicMock()
        with (
            _mock_blob_storage(
                mock_storage,
                {
                    "sha256:chartlayer_provbig": tar_data,
                    "sha256:bigprov001": huge_prov,
                },
            ),
            patch("workers.helmchartworker.extractor.app") as mock_app,
        ):
            mock_app.config.get.side_effect = lambda key, default=None: (
                1024 if key == "HELM_CHART_MAX_EXTRACTED_FILE_SIZE" else default
            )
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.provenance is None

    def test_provenance_read_failure_skipped(self, initialized_db):
        """An exception reading the provenance blob is caught; extraction succeeds."""
        chart_yaml = _make_chart_yaml()
        tar_data = _make_tar_gz({"testchart/Chart.yaml": chart_yaml})
        manifest_bytes = _make_manifest_json(
            "sha256:chartlayer_proverr", len(tar_data), provenance_digest="sha256:errprov001"
        )
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(
            mock_storage,
            {
                "sha256:chartlayer_proverr": tar_data,
                "sha256:errprov001": IOError("storage read failure"),
            },
        ):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        assert row.provenance is None

    def test_symlinks_in_tar_skipped(self, initialized_db):
        """Symlinks in the tar archive are silently skipped."""
        chart_yaml = _make_chart_yaml()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo(name="testchart/Chart.yaml")
            info.size = len(chart_yaml)
            tar.addfile(info, io.BytesIO(chart_yaml))

            link_info = tarfile.TarInfo(name="testchart/link-to-values")
            link_info.type = tarfile.SYMTYPE
            link_info.linkname = "values.yaml"
            tar.addfile(link_info)
        tar_data = buf.getvalue()

        manifest_bytes = _make_manifest_json("sha256:chartlayer_symlink", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "completed"
        paths = [f["path"] for f in row.file_tree]
        assert "testchart/link-to-values" not in paths
        assert "testchart/Chart.yaml" in paths

    def test_chart_yaml_root_is_list(self, initialized_db):
        """Chart.yaml containing a YAML list (not a dict) writes a failed row."""
        list_yaml = yaml.dump(["item1", "item2"]).encode("utf-8")
        tar_data = _make_tar_gz({"testchart/Chart.yaml": list_yaml})
        manifest_bytes = _make_manifest_json("sha256:chartlayer_listroot", len(tar_data))
        repo, manifest_row = _create_test_manifest(initialized_db, manifest_bytes)

        mock_storage = MagicMock()
        with _mock_blob_storage(mock_storage, tar_data):
            extract_helm_chart_metadata(manifest_row.id, repo.id, mock_storage)

        row = HelmChartMetadata.get(HelmChartMetadata.manifest == manifest_row.id)
        assert row.extraction_status == "failed"
        assert "not a mapping" in row.extraction_error


class TestAssemblePullspec:
    """Unit tests for _assemble_pullspec (no DB needed)."""

    def test_repository_and_tag(self):
        assert _assemble_pullspec({"repository": "nginx", "tag": "1.25"}) == "nginx:1.25"

    def test_registry_repository_tag(self):
        result = _assemble_pullspec(
            {"registry": "docker.io", "repository": "library/nginx", "tag": "latest"}
        )
        assert result == "docker.io/library/nginx:latest"

    def test_repository_and_digest(self):
        digest = "sha256:" + "a" * 64
        result = _assemble_pullspec({"repository": "myapp", "digest": digest})
        assert result == f"myapp@{digest}"

    def test_digest_without_prefix(self):
        raw = "a" * 64
        result = _assemble_pullspec({"repository": "myapp", "digest": raw})
        assert result == f"myapp@sha256:{raw}"

    def test_registry_repository_digest(self):
        digest = "sha256:" + "c" * 64
        result = _assemble_pullspec(
            {"registry": "quay.io", "repository": "org/sub/repo", "digest": digest}
        )
        assert result == f"quay.io/org/sub/repo@{digest}"

    def test_repository_only(self):
        assert _assemble_pullspec({"repository": "nginx"}) == "nginx"

    def test_numeric_tag(self):
        result = _assemble_pullspec({"repository": "postgres", "tag": 15})
        assert result == "postgres:15"

    def test_missing_repository(self):
        assert _assemble_pullspec({"tag": "latest"}) is None

    def test_empty_repository(self):
        assert _assemble_pullspec({"repository": "", "tag": "latest"}) is None

    def test_non_string_repository(self):
        assert _assemble_pullspec({"repository": 123, "tag": "latest"}) is None


class TestIsImageKey:
    """Unit tests for _is_image_key (no DB needed)."""

    def test_exact_image(self):
        assert _is_image_key("image") is True

    def test_init_image(self):
        assert _is_image_key("initimage") is True

    def test_sidecar_image(self):
        assert _is_image_key("sidecarimage") is True

    def test_suffix_image(self):
        assert _is_image_key("backupimage") is True

    def test_suffix_image_ref(self):
        assert _is_image_key("proxyimageref") is True

    def test_underscore_variant(self):
        assert _is_image_key("init_image") is True

    def test_hyphen_variant(self):
        assert _is_image_key("sidecar-image") is True

    def test_unrelated_key(self):
        assert _is_image_key("replicas") is False

    def test_contains_image_not_suffix(self):
        assert _is_image_key("imagePullPolicy") is False


class TestExtractImagesFromValues:
    """Unit tests for _extract_images_from_values (no DB needed)."""

    def test_none_content(self):
        assert _extract_images_from_values(None) == []

    def test_empty_string(self):
        assert _extract_images_from_values("") == []

    def test_invalid_yaml(self):
        assert _extract_images_from_values(":::invalid") == []

    def test_non_dict_yaml(self):
        assert _extract_images_from_values("- item1\n- item2\n") == []

    def test_structured_image(self):
        content = yaml.dump({"image": {"repository": "nginx", "tag": "1.25"}})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == "nginx:1.25"
        assert refs[0]["source"] == "image"

    def test_pullspec_string(self):
        content = yaml.dump({"image": "quay.io/myorg/myrepo:v1"})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == "quay.io/myorg/myrepo:v1"

    def test_pullspec_with_digest(self):
        digest = "sha256:" + "d" * 64
        content = yaml.dump({"image": f"registry.example.com/org/repo@{digest}"})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == f"registry.example.com/org/repo@{digest}"

    def test_pullspec_multi_slash_repo(self):
        content = yaml.dump({"image": "us-docker.pkg.dev/proj/team/sub/app:v1"})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == "us-docker.pkg.dev/proj/team/sub/app:v1"

    def test_no_image_keys(self):
        content = yaml.dump({"replicas": 3, "port": 8080})
        refs = _extract_images_from_values(content)
        assert refs == []

    def test_deeply_nested(self):
        content = yaml.dump({"a": {"b": {"c": {"image": {"repository": "deep", "tag": "v1"}}}}})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["source"] == "a.b.c.image"

    def test_list_with_images(self):
        content = yaml.dump(
            {
                "containers": [
                    {"image": "ghcr.io/org/app1:v1"},
                    {"image": "ghcr.io/org/app2:v2"},
                ]
            }
        )
        refs = _extract_images_from_values(content)
        assert len(refs) == 2

    def test_custom_image_key_suffix(self):
        content = yaml.dump({"proxy_image": "quay.io/org/proxy:v1"})
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == "quay.io/org/proxy:v1"

    def test_repository_key_without_image_parent(self):
        """A dict with 'repository' key is detected even without an 'image' parent key."""
        content = yaml.dump(
            {
                "nginx": {
                    "registry": "docker.io",
                    "repository": "library/nginx",
                    "tag": "stable",
                }
            }
        )
        refs = _extract_images_from_values(content)
        assert len(refs) == 1
        assert refs[0]["image"] == "docker.io/library/nginx:stable"


class TestExtractProvenanceMetadata:
    SAMPLE_PROV = """\
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA512

name: my-awesome-chart
version: 1.2.3
description: A test chart
files:
  my-awesome-chart-1.2.3.tgz: sha256:d2a84f4b8b1234567890
-----BEGIN PGP SIGNATURE-----

iQIzBAABCgAdFiEEabcdef1234567890ABCDEFGHIJ0123456789kl
-----END PGP SIGNATURE-----"""

    def test_none_input(self):
        result = _extract_provenance_metadata(None)
        assert result["key_id"] is None
        assert result["hash_algorithm"] is None
        assert result["signature_date"] is None

    def test_empty_string(self):
        result = _extract_provenance_metadata("")
        assert result["key_id"] is None
        assert result["hash_algorithm"] is None
        assert result["signature_date"] is None

    def test_hash_algorithm_sha512(self):
        result = _extract_provenance_metadata(self.SAMPLE_PROV)
        assert result["hash_algorithm"] == "SHA512"

    def test_hash_algorithm_sha256(self):
        prov = self.SAMPLE_PROV.replace("SHA512", "SHA256")
        result = _extract_provenance_metadata(prov)
        assert result["hash_algorithm"] == "SHA256"

    def test_hash_algorithm_sha384(self):
        prov = self.SAMPLE_PROV.replace("SHA512", "SHA384")
        result = _extract_provenance_metadata(prov)
        assert result["hash_algorithm"] == "SHA384"

    def test_no_hash_header(self):
        prov = "-----BEGIN PGP SIGNED MESSAGE-----\n\nsome data\n"
        result = _extract_provenance_metadata(prov)
        assert result["hash_algorithm"] is None

    def test_garbage_input(self):
        result = _extract_provenance_metadata("this is not a PGP message at all")
        assert result["key_id"] is None
        assert result["hash_algorithm"] is None
        assert result["signature_date"] is None

    def test_result_keys_always_present(self):
        result = _extract_provenance_metadata("random content")
        assert "key_id" in result
        assert "hash_algorithm" in result
        assert "signature_date" in result

    def test_gpg_binary_not_found_graceful(self):
        """If the gpg binary is not installed, extraction still returns hash from regex."""
        with patch(
            "workers.helmchartworker.extractor.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = _extract_provenance_metadata(self.SAMPLE_PROV)
        assert result["hash_algorithm"] == "SHA512"
        assert result["key_id"] is None
        assert result["signature_date"] is None

    def test_gpg_timeout_graceful(self):
        """If gpg hangs, extraction still returns hash from regex."""
        import subprocess

        with patch(
            "workers.helmchartworker.extractor.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="gpg", timeout=30),
        ):
            result = _extract_provenance_metadata(self.SAMPLE_PROV)
        assert result["hash_algorithm"] == "SHA512"
        assert result["key_id"] is None
        assert result["signature_date"] is None

    def test_errsig_parsing(self):
        """Verify key_id and signature_date are extracted from ERRSIG status line."""
        errsig_output = (
            b"[GNUPG:] NEWSIG\n"
            b"[GNUPG:] ERRSIG 0011223344556677 1 10 00 1700000000 9\n"
            b"[GNUPG:] NO_PUBKEY 0011223344556677\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = errsig_output
        mock_result.stderr = b""

        with patch(
            "workers.helmchartworker.extractor.subprocess.run",
            return_value=mock_result,
        ):
            result = _extract_provenance_metadata(self.SAMPLE_PROV)

        assert result["hash_algorithm"] == "SHA512"
        assert result["key_id"] == "0011223344556677"
        assert result["signature_date"] == "2023-11-14T22:13:20+00:00"

    def test_validsig_parsing(self):
        """Verify VALIDSIG overrides ERRSIG when key is known."""
        status_output = (
            b"[GNUPG:] NEWSIG\n"
            b"[GNUPG:] GOODSIG 0011223344556677 Test User\n"
            b"[GNUPG:] VALIDSIG AABBCCDDEE0011223344556677889900AABBCCDD "
            b"2023-11-14 1700000000 0 4 0 1 10 00 "
            b"AABBCCDDEE0011223344556677889900AABBCCDD\n"
        )
        mock_result = MagicMock()
        mock_result.stdout = status_output
        mock_result.stderr = b""

        with patch(
            "workers.helmchartworker.extractor.subprocess.run",
            return_value=mock_result,
        ):
            result = _extract_provenance_metadata(self.SAMPLE_PROV)

        assert result["hash_algorithm"] == "SHA512"
        assert result["key_id"] == "77889900AABBCCDD"
        assert result["signature_date"] == "2023-11-14T22:13:20+00:00"
