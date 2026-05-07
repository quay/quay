from unittest.mock import MagicMock, patch

import pytest

from data.database import (
    HelmChartMetadata,
    HelmRepoIndexConfig,
    Manifest,
    Repository,
    Tag,
    TagKind,
)
from data.model.oci.helmrepoindex import generate_helm_repo_index
from data.model.repository import create_repository
from test.fixtures import *  # noqa: F401,F403


class TestGenerateHelmRepoIndex:
    """Tests for index.yaml generation from HelmChartMetadata rows."""

    def _create_chart_metadata(self, repo, manifest, chart_name, chart_version, app_version=None):
        """Helper to create a completed HelmChartMetadata row."""
        return HelmChartMetadata.create(
            manifest=manifest,
            repository=repo,
            chart_name=chart_name,
            chart_version=chart_version,
            app_version=app_version,
            api_version="v2",
            chart_yaml=f"name: {chart_name}\nversion: {chart_version}",
            extraction_status="completed",
        )

    def test_empty_repo(self, initialized_db):
        """A repository with no Helm charts produces a valid empty index."""
        repo = create_repository("devtable", "helm-empty-test", None)
        result = generate_helm_repo_index(repo.id, "quay.example.com", "testorg", "testrepo")

        assert result["apiVersion"] == "v1"
        assert "generated" in result
        assert result["entries"] == {}

    def test_single_chart(self, initialized_db):
        """A single completed chart appears in the index entries with a versioned OCI URL."""
        repo = create_repository("devtable", "helm-single-chart-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:singlechart001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        self._create_chart_metadata(repo, manifest, "mychart", "1.0.0", "2.0.0")
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "helm-single-chart-test"
        )

        assert "mychart" in result["entries"]
        entries = result["entries"]["mychart"]
        assert len(entries) == 1
        entry = entries[0]
        assert entry["name"] == "mychart"
        assert entry["version"] == "1.0.0"
        assert entry["appVersion"] == "2.0.0"
        assert entry["apiVersion"] == "v2"
        assert entry["urls"] == ["oci://quay.example.com/testorg/helm-single-chart-test:1.0.0"]

    def test_excludes_failed_extractions(self, initialized_db):
        """Failed extractions are not included in the index even when a tag exists."""
        repo = create_repository("devtable", "helm-failed-extraction-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:failedextraction001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="0.0.1",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        HelmChartMetadata.create(
            manifest=manifest,
            repository=repo,
            chart_name="badchart",
            chart_version="0.0.1",
            api_version="v2",
            chart_yaml="",
            extraction_status="failed",
            extraction_error="corrupt archive",
        )

        result = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "helm-failed-extraction-test"
        )
        assert "badchart" not in result["entries"]

    def test_tag_pattern_filtering(self, initialized_db):
        """Only tags matching the pattern are included."""
        repo = create_repository("devtable", "helm-pattern-filter-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:patternfilter001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        self._create_chart_metadata(repo, manifest, "mychart", "1.0.0")
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result_match = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "testrepo", tag_pattern="1.0.0"
        )
        result_nomatch = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "testrepo", tag_pattern="^impossible-pattern$"
        )

        assert "mychart" in result_match["entries"]
        assert len(result_match["entries"]["mychart"]) == 1
        assert "mychart" not in result_nomatch["entries"]

    def test_invalid_pattern_includes_all(self, initialized_db):
        """An invalid regex pattern is ignored and all tags are included."""
        repo = create_repository("devtable", "helm-invalid-pattern-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:invalidpatterntest001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        self._create_chart_metadata(repo, manifest, "patternchart", "1.0.0")
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result_no_pattern = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "helm-invalid-pattern-test"
        )
        result_invalid = generate_helm_repo_index(
            repo.id,
            "quay.example.com",
            "testorg",
            "helm-invalid-pattern-test",
            tag_pattern="[invalid",
        )

        assert result_invalid["apiVersion"] == "v1"
        assert result_invalid["entries"] == result_no_pattern["entries"]

    def test_api_version_always_v1(self, initialized_db):
        """The top-level apiVersion is always v1."""
        repo = Repository.select().first()
        result = generate_helm_repo_index(repo.id, "quay.example.com", "testorg", "testrepo")
        assert result["apiVersion"] == "v1"

    def test_tag_pattern_selectively_filters(self, initialized_db):
        """A tag pattern controls whether the version tag's entry appears in the index.

        Creates one Helm manifest with four tags: 1.0.0 (version tag), v1.0.0,
        latest, v2.0.0-rc1. Without a filter, the version tag lets the entry
        appear. With pattern ^\\d+\\.\\d+\\.\\d+$, the version tag 1.0.0 matches.
        With a v-prefixed pattern that doesn't match the version tag, no entry appears.
        """
        repo = create_repository("devtable", "helm-filter-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:filtertest001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        self._create_chart_metadata(repo, manifest, "filterchart", "1.0.0")

        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )
        Tag.create(
            name="v1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )
        Tag.create(
            name="latest",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )
        Tag.create(
            name="v2.0.0-rc1",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result_no_filter = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "helm-filter-test"
        )
        assert "filterchart" in result_no_filter["entries"]
        assert len(result_no_filter["entries"]["filterchart"]) == 1

        result_filtered = generate_helm_repo_index(
            repo.id,
            "quay.example.com",
            "testorg",
            "helm-filter-test",
            tag_pattern=r"^\d+\.\d+\.\d+$",
        )
        assert "filterchart" in result_filtered["entries"]
        assert len(result_filtered["entries"]["filterchart"]) == 1

        result_v_prefix = generate_helm_repo_index(
            repo.id,
            "quay.example.com",
            "testorg",
            "helm-filter-test",
            tag_pattern=r"^v\d+\.\d+\.\d+$",
        )
        assert "filterchart" not in result_v_prefix["entries"]

        result_impossible = generate_helm_repo_index(
            repo.id,
            "quay.example.com",
            "testorg",
            "helm-filter-test",
            tag_pattern=r"^impossible$",
        )
        assert "filterchart" not in result_impossible["entries"]

    def test_chart_with_all_optional_fields(self, initialized_db):
        """All optional metadata fields (home, icon, deprecated, kubeVersion,
        sources, maintainers, keywords, dependencies) appear in the index entry."""
        repo = create_repository("devtable", "helm-full-meta-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:fullmeta001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )

        HelmChartMetadata.create(
            manifest=manifest,
            repository=repo,
            chart_name="fullchart",
            chart_version="2.0.0",
            app_version="3.1.0",
            api_version="v2",
            description="A fully populated chart",
            kube_version=">=1.22.0",
            chart_type="library",
            home="https://example.com/fullchart",
            icon_url="https://example.com/icon.png",
            deprecated=True,
            sources=["https://github.com/example/fullchart"],
            maintainers=[{"name": "Alice", "email": "alice@example.com"}],
            keywords=["full", "test", "coverage"],
            chart_dependencies=[
                {"name": "common", "version": "1.x", "repository": "https://charts.example.com"}
            ],
            chart_yaml="name: fullchart\nversion: 2.0.0",
            extraction_status="completed",
        )

        Tag.create(
            name="2.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result = generate_helm_repo_index(
            repo.id, "quay.example.com", "testorg", "helm-full-meta-test"
        )

        assert "fullchart" in result["entries"]
        entry = result["entries"]["fullchart"][0]
        assert entry["name"] == "fullchart"
        assert entry["version"] == "2.0.0"
        assert entry["appVersion"] == "3.1.0"
        assert entry["type"] == "library"
        assert entry["home"] == "https://example.com/fullchart"
        assert entry["icon"] == "https://example.com/icon.png"
        assert entry["deprecated"] is True
        assert entry["kubeVersion"] == ">=1.22.0"
        assert entry["sources"] == ["https://github.com/example/fullchart"]
        assert len(entry["maintainers"]) == 1
        assert entry["maintainers"][0]["name"] == "Alice"
        assert entry["keywords"] == ["full", "test", "coverage"]
        assert len(entry["dependencies"]) == 1
        assert entry["dependencies"][0]["name"] == "common"

    def test_mixed_content_excludes_non_helm_manifests(self, initialized_db):
        """Only manifests with HelmChartMetadata appear in the index; regular images are excluded.

        Creates a repo with three manifests and tags:
        - A Helm chart manifest (with HelmChartMetadata) tagged "1.0.0"
        - A Docker image manifest (no HelmChartMetadata) tagged "latest"
        - An OCI image manifest (no HelmChartMetadata) tagged "v2-app"
        Only the Helm chart should appear in the generated index.
        """
        repo = create_repository("devtable", "helm-mixed-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        helm_manifest = Manifest.create(
            repository=repo,
            digest="sha256:mixedhelm001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        self._create_chart_metadata(repo, helm_manifest, "my-helm-chart", "1.0.0")
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=helm_manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        docker_manifest = Manifest.create(
            repository=repo,
            digest="sha256:mixeddocker001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.docker.container.image.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="latest",
            repository=repo,
            manifest=docker_manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        oci_manifest = Manifest.create(
            repository=repo,
            digest="sha256:mixedoci001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.oci.image.config.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="v2-app",
            repository=repo,
            manifest=oci_manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        result = generate_helm_repo_index(repo.id, "quay.example.com", "testorg", "helm-mixed-test")

        assert "my-helm-chart" in result["entries"]
        assert len(result["entries"]) == 1
        assert len(result["entries"]["my-helm-chart"]) == 1


class TestInvalidateHelmRepoIndexCache:
    """Tests for the invalidate_helm_repo_index_cache helper function."""

    def test_calls_model_cache_invalidate(self):
        """The helper constructs the correct cache key and calls invalidate."""
        import features
        from data.model.oci.helmrepoindex import invalidate_helm_repo_index_cache

        mock_model_cache = MagicMock()
        mock_model_cache.cache_config = {"helm_repo_index_cache_ttl": "300s"}

        mock_app = MagicMock()
        mock_app.model_cache = mock_model_cache

        original = features.HELM_REPO_INDEX
        try:
            features.HELM_REPO_INDEX = True
            with patch.dict("sys.modules", {"app": mock_app}):
                invalidate_helm_repo_index_cache(42)
        finally:
            features.HELM_REPO_INDEX = original

        mock_model_cache.invalidate.assert_called_once()
        cache_key_arg = mock_model_cache.invalidate.call_args[0][0]
        assert "helm_repo_index__42" in cache_key_arg.key

    def test_silently_handles_import_error(self):
        """If app import fails, the helper does not raise."""
        import features
        from data.model.oci.helmrepoindex import invalidate_helm_repo_index_cache

        original = features.HELM_REPO_INDEX
        try:
            features.HELM_REPO_INDEX = True
            with patch.dict("sys.modules", {"app": None}):
                invalidate_helm_repo_index_cache(999)
        finally:
            features.HELM_REPO_INDEX = original

    def test_noop_when_feature_disabled(self):
        """When FEATURE_HELM_REPO_INDEX is off, invalidation is skipped entirely."""
        import sys

        import features
        from data.model.oci.helmrepoindex import invalidate_helm_repo_index_cache

        mock_app = MagicMock()
        original = features.HELM_REPO_INDEX
        original_app = sys.modules.get("app")
        try:
            features.HELM_REPO_INDEX = False
            sys.modules["app"] = mock_app
            invalidate_helm_repo_index_cache(42)
            mock_app.model_cache.invalidate.assert_not_called()
        finally:
            features.HELM_REPO_INDEX = original
            if original_app is not None:
                sys.modules["app"] = original_app
            else:
                sys.modules.pop("app", None)


class TestCacheInvalidationOnTagDelete:
    """Verify that tag lifecycle operations in registry_oci_model invalidate the helm index cache."""

    def _create_repo_with_tag(self, repo_name):
        """Create an isolated repo with a manifest and tag for invalidation tests."""
        repo = create_repository("devtable", repo_name, None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")
        manifest = Manifest.create(
            repository=repo,
            digest=f"sha256:{repo_name}001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )
        return repo

    def test_delete_tag_invalidates_cache(self, initialized_db):
        """registry_oci_model.delete_tag calls invalidate_helm_repo_index_cache."""
        from data.registry_model import registry_model

        self._create_repo_with_tag("helm-delete-tag-test")
        repo_ref = registry_model.lookup_repository("devtable", "helm-delete-tag-test")

        mock_cache = MagicMock()
        mock_cache.cache_config = {}

        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            registry_model.delete_tag(mock_cache, repo_ref, "1.0.0")
            mock_invalidate.assert_called_once_with(repo_ref._db_id)

    def test_delete_tags_for_manifest_invalidates_cache(self, initialized_db):
        """registry_oci_model.delete_tags_for_manifest calls invalidate_helm_repo_index_cache."""
        from data.registry_model import registry_model

        self._create_repo_with_tag("helm-delete-tags-manifest-test")
        repo_ref = registry_model.lookup_repository("devtable", "helm-delete-tags-manifest-test")

        tags = list(registry_model.list_all_active_repository_tags(repo_ref))
        manifest = registry_model.get_manifest_for_tag(tags[0])

        mock_cache = MagicMock()
        mock_cache.cache_config = {}

        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            registry_model.delete_tags_for_manifest(mock_cache, manifest)
            mock_invalidate.assert_called_once_with(manifest.repository.id)


class TestCacheInvalidationOnTagExpiration:
    """Verify that tag expiration changes invalidate the helm index cache."""

    def test_change_tag_expiration_invalidates_cache(self, initialized_db):
        """registry_oci_model.change_repository_tag_expiration invalidates the cache."""
        from datetime import datetime, timedelta

        from data.registry_model import registry_model

        repo = create_repository("devtable", "helm-expiration-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")
        manifest = Manifest.create(
            repository=repo,
            digest="sha256:expirationtest001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        repo_ref = registry_model.lookup_repository("devtable", "helm-expiration-test")
        tags = list(registry_model.list_all_active_repository_tags(repo_ref))

        future = datetime.utcnow() + timedelta(days=30)
        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            registry_model.change_repository_tag_expiration(tags[0], future)
            mock_invalidate.assert_called_once()


class TestCacheInvalidationOnGC:
    """Verify that GC invalidates the helm index cache when tags are collected."""

    def test_gc_invalidates_cache_when_tags_purged(self, initialized_db):
        """garbage_collect_repo calls invalidate when expired tags are collected."""
        from data.model.gc import garbage_collect_repo

        repo = create_repository("devtable", "helm-gc-expire-test", None)
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:gcexpiretest001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        Tag.create(
            name="expired-tag",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
            lifetime_end_ms=1,
        )

        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            garbage_collect_repo(repo)
            mock_invalidate.assert_called_once_with(repo.id)

    def test_gc_skips_invalidation_when_no_changes(self, initialized_db):
        """garbage_collect_repo does not call invalidate when no tags are collected."""
        from data.model.gc import garbage_collect_repo

        repo = create_repository("devtable", "helm-gc-empty-test", None)
        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            had_changes = garbage_collect_repo(repo)

            assert had_changes is False
            mock_invalidate.assert_not_called()


class TestCacheInvalidationOnAutoprune:
    """Verify that autoprune invalidates the helm index cache."""

    def test_prune_tags_invalidates_cache(self, initialized_db):
        """prune_tags calls invalidate after successfully deleting tags."""
        from data.model.autoprune import prune_tags

        repo = create_repository("devtable", "helm-prune-test", None)
        namespace = repo.namespace_user
        media_type = Manifest.media_type.rel_model.get(
            Manifest.media_type.rel_model.name == "application/vnd.oci.image.manifest.v1+json"
        )
        tag_kind = TagKind.get(TagKind.name == "tag")

        manifest = Manifest.create(
            repository=repo,
            digest="sha256:prunetest001",
            media_type=media_type,
            manifest_bytes="{}",
            config_media_type="application/vnd.cncf.helm.config.v1+json",
            layers_compressed_size=0,
        )
        tag = Tag.create(
            name="1.0.0",
            repository=repo,
            manifest=manifest,
            tag_kind=tag_kind,
            reversion=False,
        )

        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            prune_tags([tag], repo, namespace)
            mock_invalidate.assert_called_once_with(repo.id)

    def test_prune_tags_skips_invalidation_when_no_deletes(self, initialized_db):
        """prune_tags does not invalidate if no tags were actually deleted."""
        from data.model.autoprune import prune_tags

        repo = create_repository("devtable", "helm-prune-empty-test", None)
        namespace = repo.namespace_user

        fake_tag = MagicMock()
        fake_tag.name = "nonexistent-tag"

        with patch(
            "data.model.oci.helmrepoindex.invalidate_helm_repo_index_cache"
        ) as mock_invalidate:
            prune_tags([fake_tag], repo, namespace)
            mock_invalidate.assert_not_called()


class TestHelmRepoIndexConfig:
    """Tests for the HelmRepoIndexConfig database model."""

    def test_create_config(self, initialized_db):
        repo = Repository.select().first()
        config = HelmRepoIndexConfig.create(repository=repo, enabled=True, tag_pattern="^v.*")

        assert config.enabled is True
        assert config.tag_pattern == "^v.*"

    def test_default_disabled(self, initialized_db):
        repo = Repository.select().first()
        config = HelmRepoIndexConfig.create(repository=repo)

        assert config.enabled is False
        assert config.tag_pattern is None

    def test_unique_per_repository(self, initialized_db):
        repo = Repository.select().first()
        HelmRepoIndexConfig.create(repository=repo, enabled=True)

        with pytest.raises(Exception):
            HelmRepoIndexConfig.create(repository=repo, enabled=False)
