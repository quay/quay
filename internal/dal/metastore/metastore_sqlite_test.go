package metastore_test

import (
	"context"
	"database/sql"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

func setupStore(t *testing.T) oci.MetadataStore {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	store, err := metastore.NewSQLiteStore(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func setupStoreWithConfig(t *testing.T, cfg metastore.StoreConfig) *metastore.SQLiteStore {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	store, err := metastore.NewSQLiteStore(t.Context(), db, cfg)
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func TestEnsureRepository(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	id1, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if id1 == 0 {
		t.Fatal("expected non-zero repo ID")
	}

	// Idempotent: same name returns same ID.
	id2, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if id1 != id2 {
		t.Errorf("expected idempotent ID %d, got %d", id1, id2)
	}

	// Different repo returns different ID.
	id3, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "alpine"})
	if err != nil {
		t.Fatal(err)
	}
	if id3 == id1 {
		t.Error("expected different ID for different repo")
	}
}

func TestEnsureRepository_MultipleNamespaces(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	id1, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "namespace1", Name: "repo"})
	if err != nil {
		t.Fatal(err)
	}

	// Second namespace must not fail (catches UNIQUE email constraint on empty string).
	id2, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "namespace2", Name: "repo"})
	if err != nil {
		t.Fatal(err)
	}
	if id1 == id2 {
		t.Error("expected different repo IDs for different namespaces")
	}
}

func TestEnsureRepository_DefaultNamespace(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	// Single-component name defaults to "library" namespace.
	id, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if id == 0 {
		t.Fatal("expected non-zero repo ID")
	}
}

func TestPutBlob(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	dgst := digest.FromString("blob-content")
	id1, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: 42})
	if err != nil {
		t.Fatal(err)
	}
	if id1 == 0 {
		t.Fatal("expected non-zero blob ID")
	}

	// Idempotent: same digest returns same ID.
	id2, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: 42})
	if err != nil {
		t.Fatal(err)
	}
	if id1 != id2 {
		t.Errorf("expected idempotent ID %d, got %d", id1, id2)
	}
}

func TestPutManifest_Simple(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	blobDgst := digest.FromString("layer-data")
	manifestDgst := digest.FromString("manifest-content")
	content := []byte(`{"schemaVersion":2}`)

	mid, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    manifestDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   content,
		BlobDigests: []oci.BlobRef{
			{Digest: blobDgst, Size: 100},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if mid == 0 {
		t.Fatal("expected non-zero manifest ID")
	}

	// Idempotent: re-push returns same ID.
	mid2, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    manifestDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   content,
		BlobDigests: []oci.BlobRef{
			{Digest: blobDgst, Size: 100},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if mid != mid2 {
		t.Errorf("expected idempotent ID %d, got %d", mid, mid2)
	}
}

func TestPutManifest_WithTag(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("manifest-v1")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
		Tag:       "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Verify tag exists.
	assertActiveTag(t, store.(*metastore.SQLiteStore), repoID, "latest")
}

func TestPutManifest_DigestOnlyCreatesExpiringTempTag(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("digest-only-child")
	manifestID, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:            dgst,
		MediaType:         "application/vnd.oci.image.manifest.v1+json",
		Content:           []byte(`{"schemaVersion":2}`),
		TempTagExpiration: oci.PushTempTagExpiration,
	})
	if err != nil {
		t.Fatal(err)
	}

	db := store.(*metastore.SQLiteStore).DB()
	var name string
	var hidden int
	var endMs sql.NullInt64
	if err := db.QueryRowContext(ctx,
		`SELECT name, hidden, lifetime_end_ms FROM tag WHERE manifest_id = ?`,
		manifestID).Scan(&name, &hidden, &endMs); err != nil {
		t.Fatal(err)
	}
	if hidden != 1 {
		t.Errorf("hidden = %d, want 1", hidden)
	}
	if !strings.HasPrefix(name, "$temp-") {
		t.Errorf("temp tag name %q, want $temp- prefix", name)
	}
	if !endMs.Valid {
		t.Fatal("digest-only temp tag must expire (lifetime_end_ms set)")
	}
	wantMin := time.Now().Add(50 * time.Minute).UnixMilli()
	wantMax := time.Now().Add(70 * time.Minute).UnixMilli()
	if endMs.Int64 < wantMin || endMs.Int64 > wantMax {
		t.Errorf("lifetime_end_ms = %d, want ~1 hour from now", endMs.Int64)
	}

	// Repeat PUT must not duplicate the temp tag (existing one still covers the window).
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:            dgst,
		MediaType:         "application/vnd.oci.image.manifest.v1+json",
		Content:           []byte(`{"schemaVersion":2}`),
		TempTagExpiration: oci.PushTempTagExpiration,
	}); err != nil {
		t.Fatal(err)
	}
	var count int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM tag WHERE manifest_id = ?`, manifestID).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Errorf("temp tags after repeat PUT: got %d, want 1", count)
	}
}

func TestPutManifest_TagReplace(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	// Push v1 with tag "latest".
	dgst1 := digest.FromString("manifest-v1")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst1,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":1}`),
		Tag:       "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Push v2 with same tag "latest" --- must not create duplicate active tags.
	dgst2 := digest.FromString("manifest-v2")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst2,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":2}`),
		Tag:       "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Exactly one active tag named "latest" should exist.
	assertActiveTagCount(t, store.(*metastore.SQLiteStore), repoID, "latest", 1)
}

func TestPutManifest_IndexWithChildren(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	// Push child manifests first (as would happen in a real push).
	childDgst1 := digest.FromString("child-amd64")
	childDgst2 := digest.FromString("child-arm64")
	for _, dgst := range []digest.Digest{childDgst1, childDgst2} {
		if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    dgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{}`),
		}); err != nil {
			t.Fatal(err)
		}
	}

	// Push the index referencing both children.
	indexDgst := digest.FromString("index-manifest")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       indexDgst,
		MediaType:    "application/vnd.oci.image.index.v1+json",
		Content:      []byte(`{"manifests":[...]}`),
		ChildDigests: []digest.Digest{childDgst1, childDgst2},
		Tag:          "latest",
	})
	if err != nil {
		t.Fatal(err)
	}
}

func TestPutManifest_IndexMaterializesChildLayers(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	configDgst := digest.FromString("child-config")
	layerDgst := digest.FromString("child-layer")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: configDgst, Size: 12}); err != nil {
		t.Fatal(err)
	}
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 24}); err != nil {
		t.Fatal(err)
	}

	childContent := []byte(`{"schemaVersion":2,"mediaType":"application/vnd.oci.image.manifest.v1+json","config":{"digest":"` + configDgst.String() + `"},"layers":[{"digest":"` + layerDgst.String() + `"}]}`)
	childDgst := digest.FromBytes(childContent)
	indexDgst := digest.FromString("index-only")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       indexDgst,
		MediaType:    "application/vnd.oci.image.index.v1+json",
		Content:      []byte(`{"manifests":[...]}`),
		ChildDigests: []digest.Digest{childDgst},
		ChildManifests: []oci.ManifestRecord{{
			Digest:    childDgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   childContent,
			BlobDigests: []oci.BlobRef{
				{Digest: configDgst, Size: 12},
				{Digest: layerDgst, Size: 24},
			},
		}},
		Tag: "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	db := store.(*metastore.SQLiteStore).DB()
	var childBytes string
	if err := db.QueryRowContext(ctx, `SELECT manifest_bytes FROM manifest WHERE digest = ?`, childDgst.String()).Scan(&childBytes); err != nil {
		t.Fatal(err)
	}
	if childBytes != string(childContent) {
		t.Errorf("child manifest_bytes = %q, want real JSON (not {})", childBytes)
	}

	var blobLinks int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*) FROM manifestblob mb
		JOIN manifest m ON m.id = mb.manifest_id
		WHERE m.digest = ?`, childDgst.String()).Scan(&blobLinks); err != nil {
		t.Fatal(err)
	}
	if blobLinks != 2 {
		t.Errorf("child manifestblob rows = %d, want 2 (config + layer)", blobLinks)
	}

	var childLinks int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*) FROM manifestchild mc
		JOIN manifest p ON p.id = mc.manifest_id
		JOIN manifest c ON c.id = mc.child_manifest_id
		WHERE p.digest = ? AND c.digest = ?`, indexDgst.String(), childDgst.String()).Scan(&childLinks); err != nil {
		t.Fatal(err)
	}
	if childLinks != 1 {
		t.Errorf("manifestchild rows = %d, want 1", childLinks)
	}

	var childID int64
	if err := db.QueryRowContext(ctx, `SELECT id FROM manifest WHERE digest = ?`, childDgst.String()).Scan(&childID); err != nil {
		t.Fatal(err)
	}
	var name string
	var hidden int
	var endMs sql.NullInt64
	if err := db.QueryRowContext(ctx, `SELECT name, hidden, lifetime_end_ms FROM tag WHERE manifest_id = ?`, childID).Scan(&name, &hidden, &endMs); err != nil {
		t.Fatal(err)
	}
	if hidden != 1 {
		t.Errorf("child hidden = %d, want 1", hidden)
	}
	if !strings.HasPrefix(name, "$temp-") {
		t.Errorf("child temp tag name %q, want $temp- prefix", name)
	}
	if !endMs.Valid {
		t.Fatal("index-created child must get an expiring $temp- tag")
	}

	// Repeat index PUT must not duplicate the child's temp tag.
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       indexDgst,
		MediaType:    "application/vnd.oci.image.index.v1+json",
		Content:      []byte(`{"manifests":[...]}`),
		ChildDigests: []digest.Digest{childDgst},
		ChildManifests: []oci.ManifestRecord{{
			Digest:    childDgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   childContent,
			BlobDigests: []oci.BlobRef{
				{Digest: configDgst, Size: 12},
				{Digest: layerDgst, Size: 24},
			},
		}},
		Tag: "latest",
	}); err != nil {
		t.Fatal(err)
	}
	var tagCount int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM tag WHERE manifest_id = ?`, childID).Scan(&tagCount); err != nil {
		t.Fatal(err)
	}
	if tagCount != 1 {
		t.Errorf("child tags after repeat index PUT: got %d, want 1", tagCount)
	}
}

func TestPutManifest_IndexDoesNotClobberNonEmptyChildBytes(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	realContent := []byte(`{"schemaVersion":2,"config":{"digest":"sha256:abc"}}`)
	childDgst := digest.FromString("already-written-child")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:            childDgst,
		MediaType:         "application/vnd.oci.image.manifest.v1+json",
		Content:           realContent,
		TempTagExpiration: oci.PushTempTagExpiration,
	}); err != nil {
		t.Fatal(err)
	}

	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       digest.FromString("parent-index"),
		MediaType:    "application/vnd.oci.image.index.v1+json",
		Content:      []byte(`{"manifests":[...]}`),
		ChildDigests: []digest.Digest{childDgst},
		ChildManifests: []oci.ManifestRecord{{
			Digest:    childDgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   realContent,
		}},
		Tag: "latest",
	}); err != nil {
		t.Fatal(err)
	}

	db := store.(*metastore.SQLiteStore).DB()
	var childBytes string
	if err := db.QueryRowContext(ctx, `SELECT manifest_bytes FROM manifest WHERE digest = ?`, childDgst.String()).Scan(&childBytes); err != nil {
		t.Fatal(err)
	}
	if childBytes != string(realContent) {
		t.Errorf("child manifest_bytes = %q, want %q (must not clobber to {})", childBytes, realContent)
	}
	var tagCount int
	if err := db.QueryRowContext(ctx, `
		SELECT count(*) FROM tag t
		JOIN manifest m ON m.id = t.manifest_id
		WHERE m.digest = ?`, childDgst.String()).Scan(&tagCount); err != nil {
		t.Fatal(err)
	}
	if tagCount != 1 {
		t.Errorf("child tags after index PUT: got %d, want 1 (must not duplicate $temp-)", tagCount)
	}
}

func TestPutManifest_PlaceholderUpsertDoesNotClobberNonEmptyBytes(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	realContent := []byte(`{"schemaVersion":2,"real":true}`)
	childDgst := digest.FromString("race-child")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    childDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   realContent,
	}); err != nil {
		t.Fatal(err)
	}

	db := store.(*metastore.SQLiteStore).DB()
	var mtID int64
	if err := db.QueryRowContext(ctx, `SELECT id FROM mediatype WHERE name = ?`, "application/vnd.oci.image.manifest.v1+json").Scan(&mtID); err != nil {
		t.Fatal(err)
	}
	// Simulate the concurrent race: index PUT's placeholder upsert runs after
	// the child digest PUT has already committed real JSON.
	if _, err := daldb.New(db).UpsertManifest(ctx, daldb.UpsertManifestParams{
		RepositoryID:  repoID,
		Digest:        childDgst.String(),
		MediaTypeID:   mtID,
		ManifestBytes: "{}",
	}); err != nil {
		t.Fatal(err)
	}

	var childBytes string
	if err := db.QueryRowContext(ctx, `SELECT manifest_bytes FROM manifest WHERE digest = ?`, childDgst.String()).Scan(&childBytes); err != nil {
		t.Fatal(err)
	}
	if childBytes != string(realContent) {
		t.Errorf("after placeholder upsert, manifest_bytes = %q, want %q", childBytes, realContent)
	}
}

func TestPutManifest_IndexReusesExistingBlobIDs(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	layerDgst := digest.FromString("shared-layer")
	blobID, err := store.PutBlob(ctx, oci.BlobRecord{Digest: layerDgst, Size: 40})
	if err != nil {
		t.Fatal(err)
	}

	childContent := []byte(`{"schemaVersion":2,"layers":[{"digest":"` + layerDgst.String() + `"}]}`)
	childDgst := digest.FromBytes(childContent)
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       digest.FromString("index-reuse-blob"),
		MediaType:    "application/vnd.oci.image.index.v1+json",
		Content:      []byte(`{"manifests":[]}`),
		ChildDigests: []digest.Digest{childDgst},
		ChildManifests: []oci.ManifestRecord{{
			Digest:      childDgst,
			MediaType:   "application/vnd.oci.image.manifest.v1+json",
			Content:     childContent,
			BlobDigests: []oci.BlobRef{{Digest: layerDgst, Size: 40}},
		}},
	}); err != nil {
		t.Fatal(err)
	}

	db := store.(*metastore.SQLiteStore).DB()
	var count int
	if err := db.QueryRowContext(ctx, `SELECT count(*) FROM imagestorage WHERE content_checksum = ?`, layerDgst.String()).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Errorf("imagestorage rows for layer = %d, want 1 (must reuse existing id)", count)
	}
	var linkedID int64
	if err := db.QueryRowContext(ctx, `
		SELECT mb.blob_id FROM manifestblob mb
		JOIN imagestorage s ON s.id = mb.blob_id
		WHERE s.content_checksum = ?`, layerDgst.String()).Scan(&linkedID); err != nil {
		t.Fatal(err)
	}
	if linkedID != blobID {
		t.Errorf("linked blob id = %d, want original %d", linkedID, blobID)
	}
}

func TestPutManifest_UnknownMediaType(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("custom-manifest")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.example.custom.v1+json",
		Content:   []byte(`{}`),
	})
	if err == nil {
		t.Fatal("expected error for unknown media type")
	}
}

func TestDeleteManifest(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("to-delete")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
		Tag:       "v1",
	})
	if err != nil {
		t.Fatal(err)
	}

	if err := store.DeleteManifest(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}

	// Deleting again should be a no-op.
	if err := store.DeleteManifest(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}
}

func TestPutTag(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("tagged-manifest")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
	})
	if err != nil {
		t.Fatal(err)
	}

	tagID, err := store.PutTag(ctx, repoID, oci.TagRecord{
		Name:   "stable",
		Digest: dgst,
	})
	if err != nil {
		t.Fatal(err)
	}
	if tagID == 0 {
		t.Fatal("expected non-zero tag ID")
	}
}

func TestDeleteTag(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("tagged-manifest")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
		Tag:       "removeme",
	})
	if err != nil {
		t.Fatal(err)
	}

	if err := store.DeleteTag(ctx, repoID, "removeme"); err != nil {
		t.Fatal(err)
	}

	// Deleting again should be a no-op (idempotent, like DeleteManifest).
	if err := store.DeleteTag(ctx, repoID, "removeme"); err != nil {
		t.Errorf("expected no-op on already-expired tag, got %v", err)
	}
}

func TestListReferrers_Empty(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("subject-manifest")
	refs, err := store.ListReferrers(ctx, repoID, subjectDgst, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(refs) != 0 {
		t.Errorf("referrers = %d, want 0", len(refs))
	}
}

func TestListReferrers_WithSubject(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("subject-manifest")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    subjectDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
		Tag:       "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	referrerDgst := digest.FromString("sbom-referrer")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       referrerDgst,
		MediaType:    "application/vnd.oci.image.manifest.v1+json",
		Content:      []byte(`{"schemaVersion":2,"subject":{"digest":"` + subjectDgst.String() + `"}}`),
		Subject:      subjectDgst,
		ArtifactType: "application/vnd.example.sbom.v1",
	})
	if err != nil {
		t.Fatal(err)
	}

	refs, err := store.ListReferrers(ctx, repoID, subjectDgst, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(refs) != 1 {
		t.Fatalf("referrers = %d, want 1", len(refs))
	}
	if refs[0].Digest != referrerDgst.String() {
		t.Errorf("digest = %s, want %s", refs[0].Digest, referrerDgst)
	}
	if refs[0].ArtifactType != "application/vnd.example.sbom.v1" {
		t.Errorf("artifactType = %q, want sbom", refs[0].ArtifactType)
	}
	if refs[0].Size <= 0 {
		t.Errorf("size = %d, want > 0", refs[0].Size)
	}
}

func TestPutManifest_RepeatSubjectPush_NoDuplicateProtectionTag(t *testing.T) {
	// Regression test: repeat pushes of the same subject/referrer manifest
	// (e.g. re-signing with cosign, CI re-running an attestation push) must
	// not create a new hidden protection tag row each time.
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("subject-manifest")
	referrerDgst := digest.FromString("sbom-referrer")
	referrer := oci.ManifestRecord{
		Digest:       referrerDgst,
		MediaType:    "application/vnd.oci.image.manifest.v1+json",
		Content:      []byte(`{"schemaVersion":2,"subject":{"digest":"` + subjectDgst.String() + `"}}`),
		Subject:      subjectDgst,
		ArtifactType: "application/vnd.example.sbom.v1",
	}

	manifestID, err := store.PutManifest(ctx, repoID, referrer)
	if err != nil {
		t.Fatal(err)
	}
	assertProtectionTagCount(t, store.(*metastore.SQLiteStore), manifestID)

	// Repeat push of the identical referrer manifest (same digest, same subject).
	manifestID2, err := store.PutManifest(ctx, repoID, referrer)
	if err != nil {
		t.Fatal(err)
	}
	if manifestID2 != manifestID {
		t.Fatalf("expected repeat push to resolve to the same manifest ID, got %d want %d", manifestID2, manifestID)
	}
	assertProtectionTagCount(t, store.(*metastore.SQLiteStore), manifestID)

	// And a third push, for good measure.
	if _, err := store.PutManifest(ctx, repoID, referrer); err != nil {
		t.Fatal(err)
	}
	assertProtectionTagCount(t, store.(*metastore.SQLiteStore), manifestID)
}

func TestPutManifest_SubjectPush_PreExistingLegacyProtectionTag_NoOp(t *testing.T) {
	// Simulates an already-affected install: a manifest that already has a
	// non-expiring tag from before this fix shipped (e.g. a duplicate
	// "$referrer-<digest>" row from a prior buggy push). The fix must detect
	// any existing non-expiring tag by manifest_id --- not by name --- and
	// skip creating another one.
	store := setupStore(t)
	ctx := t.Context()
	sqliteStore := store.(*metastore.SQLiteStore)

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	// Create the referrer manifest without a subject, so setSubjectAndProtect
	// is not yet invoked.
	referrerDgst := digest.FromString("sbom-referrer")
	manifestID, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    referrerDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
	})
	if err != nil {
		t.Fatal(err)
	}

	// Manually insert a legacy-style duplicate hidden tag, as the pre-fix
	// code would have left behind.
	db := sqliteStore.DB()
	var tagKindID int64
	if err := db.QueryRowContext(ctx, `SELECT id FROM tagkind WHERE name = 'tag'`).Scan(&tagKindID); err != nil {
		t.Fatal(err)
	}
	if _, err := db.ExecContext(ctx,
		`INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, tag_kind_id, hidden) VALUES (?, ?, ?, ?, ?, 1)`,
		"$referrer-"+referrerDgst.Encoded()[:12], repoID, manifestID, time.Now().UnixMilli(), tagKindID,
	); err != nil {
		t.Fatal(err)
	}
	assertProtectionTagCount(t, sqliteStore, manifestID)

	// Now push again with the subject set, as a real referrer push would.
	subjectDgst := digest.FromString("subject-manifest")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       referrerDgst,
		MediaType:    "application/vnd.oci.image.manifest.v1+json",
		Content:      []byte(`{"schemaVersion":2,"subject":{"digest":"` + subjectDgst.String() + `"}}`),
		Subject:      subjectDgst,
		ArtifactType: "application/vnd.example.sbom.v1",
	}); err != nil {
		t.Fatal(err)
	}

	// The pre-existing legacy row already satisfies the protection
	// invariant, so no new tag should have been created.
	assertProtectionTagCount(t, sqliteStore, manifestID)
}

func TestListReferrers_FilterByArtifactType(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("subject")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    subjectDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
	})
	if err != nil {
		t.Fatal(err)
	}

	sbomDgst := digest.FromString("sbom")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       sbomDgst,
		MediaType:    "application/vnd.oci.image.manifest.v1+json",
		Content:      []byte(`{"subject":{}}`),
		Subject:      subjectDgst,
		ArtifactType: "application/vnd.example.sbom.v1",
	})
	if err != nil {
		t.Fatal(err)
	}

	sigDgst := digest.FromString("signature")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:       sigDgst,
		MediaType:    "application/vnd.oci.image.manifest.v1+json",
		Content:      []byte(`{"subject":{}}`),
		Subject:      subjectDgst,
		ArtifactType: "application/vnd.example.signature.v1",
	})
	if err != nil {
		t.Fatal(err)
	}

	// All referrers
	all, err := store.ListReferrers(ctx, repoID, subjectDgst, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(all) != 2 {
		t.Fatalf("all referrers = %d, want 2", len(all))
	}

	// Filter by SBOM
	sboms, err := store.ListReferrers(ctx, repoID, subjectDgst, "application/vnd.example.sbom.v1")
	if err != nil {
		t.Fatal(err)
	}
	if len(sboms) != 1 {
		t.Fatalf("sbom referrers = %d, want 1", len(sboms))
	}
	if sboms[0].Digest != sbomDgst.String() {
		t.Errorf("digest = %s, want %s", sboms[0].Digest, sbomDgst)
	}

	// Filter by non-existent type
	none, err := store.ListReferrers(ctx, repoID, subjectDgst, "application/vnd.nonexistent")
	if err != nil {
		t.Fatal(err)
	}
	if len(none) != 0 {
		t.Errorf("nonexistent referrers = %d, want 0", len(none))
	}
}

func TestListReferrers_FallbackTagSchema(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("subject-for-fallback")

	// Create an OCI index manifest that lists referrers (the fallback tag content)
	referrerDgst := digest.FromString("fallback-referrer")
	indexContent := []byte(`{"schemaVersion":2,"mediaType":"application/vnd.oci.image.index.v1+json","manifests":[{"mediaType":"application/vnd.oci.image.manifest.v1+json","digest":"` + referrerDgst.String() + `","size":100,"artifactType":"application/vnd.example.sbom.v1","annotations":{"org.test":"value"}}]}`)
	indexDgst := digest.FromBytes(indexContent)

	// Store the index manifest
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    indexDgst,
		MediaType: "application/vnd.oci.image.index.v1+json",
		Content:   indexContent,
	})
	if err != nil {
		t.Fatal(err)
	}

	// Create the fallback tag: "sha256-<encoded>" pointing to the index
	_, err = store.PutTag(ctx, repoID, oci.TagRecord{
		Name:   "sha256-" + subjectDgst.Encoded(),
		Digest: indexDgst,
	})
	if err != nil {
		t.Fatal(err)
	}

	// Query referrers — should find the descriptor from the fallback tag
	refs, err := store.ListReferrers(ctx, repoID, subjectDgst, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(refs) != 1 {
		t.Fatalf("referrers = %d, want 1 (from fallback tag)", len(refs))
	}
	if refs[0].Digest != referrerDgst.String() {
		t.Errorf("digest = %s, want %s", refs[0].Digest, referrerDgst)
	}
	if refs[0].ArtifactType != "application/vnd.example.sbom.v1" {
		t.Errorf("artifactType = %q, want sbom", refs[0].ArtifactType)
	}
	if refs[0].Annotations["org.test"] != "value" {
		t.Errorf("annotations = %v, want org.test=value", refs[0].Annotations)
	}
}

func TestEnsureRepository_DefaultVisibilityPublic(t *testing.T) {
	store := setupStoreWithConfig(t, metastore.StoreConfig{CreatePrivateOnPush: false})
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "mirror", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	db := store.DB()
	var visibilityName string
	err = db.QueryRowContext(ctx,
		`SELECT v.name FROM repository r JOIN visibility v ON r.visibility_id = v.id WHERE r.id = ?`,
		repoID).Scan(&visibilityName)
	if err != nil {
		t.Fatal(err)
	}
	if visibilityName != "public" {
		t.Errorf("expected public visibility, got %q", visibilityName)
	}
}

func TestEnsureRepository_CreatePrivateOnPush(t *testing.T) {
	store := setupStoreWithConfig(t, metastore.StoreConfig{CreatePrivateOnPush: true})
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "mirror", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	db := store.DB()
	var visibilityName string
	err = db.QueryRowContext(ctx,
		`SELECT v.name FROM repository r JOIN visibility v ON r.visibility_id = v.id WHERE r.id = ?`,
		repoID).Scan(&visibilityName)
	if err != nil {
		t.Fatal(err)
	}
	if visibilityName != "private" {
		t.Errorf("expected private visibility, got %q", visibilityName)
	}
}

func TestEnsureRepository_ExistingRepoVisibilityUnchanged(t *testing.T) {
	store := setupStoreWithConfig(t, metastore.StoreConfig{CreatePrivateOnPush: false})
	ctx := t.Context()
	db := store.DB()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "mirror", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	// Manually change to private to simulate a user changing visibility.
	_, err = db.ExecContext(ctx,
		`UPDATE repository SET visibility_id = (SELECT id FROM visibility WHERE name = 'private') WHERE id = ?`,
		repoID)
	if err != nil {
		t.Fatal(err)
	}

	// Re-push (EnsureRepository again) should NOT change it back to public.
	repoID2, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "mirror", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if repoID2 != repoID {
		t.Fatalf("expected same repo ID %d, got %d", repoID, repoID2)
	}

	var visibilityName string
	err = db.QueryRowContext(ctx,
		`SELECT v.name FROM repository r JOIN visibility v ON r.visibility_id = v.id WHERE r.id = ?`,
		repoID).Scan(&visibilityName)
	if err != nil {
		t.Fatal(err)
	}
	if visibilityName != "private" {
		t.Errorf("expected visibility to remain private after re-push, got %q", visibilityName)
	}
}

// --- test helpers ---

func assertActiveTag(t *testing.T, s *metastore.SQLiteStore, repoID int64, tag string) {
	t.Helper()
	assertActiveTagCount(t, s, repoID, tag, 1)
}

func assertActiveTagCount(t *testing.T, s *metastore.SQLiteStore, repoID int64, tag string, want int) {
	t.Helper()
	db := s.DB()
	var count int
	err := db.QueryRowContext(context.Background(),
		`SELECT count(*) FROM tag WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL`,
		repoID, tag).Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != want {
		t.Errorf("active tags named %q: got %d, want %d", tag, count, want)
	}
}

// assertProtectionTagCount asserts exactly one non-expiring
// (lifetime_end_ms IS NULL) tag exists for a given manifest, regardless of
// name. Hidden protection tags created by setSubjectAndProtect use randomly
// generated names, so they can't be matched by name like assertActiveTagCount does.
func assertProtectionTagCount(t *testing.T, s *metastore.SQLiteStore, manifestID int64) {
	t.Helper()
	db := s.DB()
	var count int
	err := db.QueryRowContext(context.Background(),
		`SELECT count(*) FROM tag WHERE manifest_id = ? AND lifetime_end_ms IS NULL`,
		manifestID).Scan(&count)
	if err != nil {
		t.Fatal(err)
	}
	if count != 1 {
		t.Errorf("non-expiring tags for manifest %d: got %d, want 1", manifestID, count)
	}
}
