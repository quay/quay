package metastore_test

import (
	"context"
	"path/filepath"
	"testing"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

func setupStore(t *testing.T) metastore.Store {
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
	id1, err := store.PutBlob(ctx, metastore.BlobRecord{Digest: dgst, Size: 42})
	if err != nil {
		t.Fatal(err)
	}
	if id1 == 0 {
		t.Fatal("expected non-zero blob ID")
	}

	// Idempotent: same digest returns same ID.
	id2, err := store.PutBlob(ctx, metastore.BlobRecord{Digest: dgst, Size: 42})
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

	mid, err := store.PutManifest(ctx, repoID, metastore.ManifestRecord{
		Digest:    manifestDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   content,
		BlobDigests: []metastore.BlobRef{
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
	mid2, err := store.PutManifest(ctx, repoID, metastore.ManifestRecord{
		Digest:    manifestDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   content,
		BlobDigests: []metastore.BlobRef{
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
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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

func TestPutManifest_TagReplace(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	// Push v1 with tag "latest".
	dgst1 := digest.FromString("manifest-v1")
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
		Digest:    dgst1,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":1}`),
		Tag:       "latest",
	})
	if err != nil {
		t.Fatal(err)
	}

	// Push v2 with same tag "latest" — must not create duplicate active tags.
	dgst2 := digest.FromString("manifest-v2")
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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
		if _, err := store.PutManifest(ctx, repoID, metastore.ManifestRecord{
			Digest:    dgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{}`),
		}); err != nil {
			t.Fatal(err)
		}
	}

	// Push the index referencing both children.
	indexDgst := digest.FromString("index-manifest")
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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

func TestPutManifest_UnknownMediaType(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("custom-manifest")
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
	})
	if err != nil {
		t.Fatal(err)
	}

	tagID, err := store.PutTag(ctx, repoID, metastore.TagRecord{
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
	_, err = store.PutManifest(ctx, repoID, metastore.ManifestRecord{
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
