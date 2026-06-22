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

func testStore(t *testing.T) (store *metastore.SQLiteStore, cleanup func()) {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	var err2 error
	store, err2 = metastore.NewSQLiteStore(t.Context(), db)
	if err2 != nil {
		db.Close()
		t.Fatal(err2)
	}
	cleanup = func() { db.Close() }
	return
}

func TestGetRepositoryID(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	id, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}

	got, err := store.GetRepositoryID(ctx, name)
	if err != nil {
		t.Fatal(err)
	}
	if got != id {
		t.Errorf("GetRepositoryID = %d, want %d", got, id)
	}

	_, err = store.GetRepositoryID(ctx, oci.RepositoryName{Namespace: "no", Name: "exist"})
	if err == nil {
		t.Fatal("expected error for nonexistent repo")
	}
}

func TestGetTagDigest(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	repoID, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("manifest-for-tag")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
		Tag:       "latest",
	}); err != nil {
		t.Fatal(err)
	}

	got, err := store.GetTagDigest(ctx, repoID, "latest")
	if err != nil {
		t.Fatal(err)
	}
	if got != dgst {
		t.Errorf("GetTagDigest = %s, want %s", got, dgst)
	}

	_, err = store.GetTagDigest(ctx, repoID, "nonexistent")
	if err == nil {
		t.Fatal("expected error for nonexistent tag")
	}
}

func TestGetManifestDigest(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	repoID, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}
	dgst := digest.FromString("test-manifest")

	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{}`),
	}); err != nil {
		t.Fatal(err)
	}

	got, err := store.GetManifestDigest(ctx, repoID, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if got != dgst {
		t.Errorf("GetManifestDigest = %s, want %s", got, dgst)
	}

	_, err = store.GetManifestDigest(ctx, repoID, digest.FromString("missing"))
	if err == nil {
		t.Fatal("expected error for nonexistent manifest")
	}
}

func TestBlobExists(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	dgst := digest.FromString("test-blob")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: 42}); err != nil {
		t.Fatal(err)
	}

	exists, err := store.BlobExists(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Error("BlobExists = false, want true")
	}

	exists, err = store.BlobExists(ctx, digest.FromString("missing"))
	if err != nil {
		t.Fatal(err)
	}
	if exists {
		t.Error("BlobExists = true for missing blob")
	}
}

func TestListTags(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	repoID, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}

	d1 := digest.FromString("m1")
	d2 := digest.FromString("m2")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: d1, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "v1",
	}); err != nil {
		t.Fatal(err)
	}
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: d2, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "v2",
	}); err != nil {
		t.Fatal(err)
	}

	tags, err := store.ListTags(ctx, repoID)
	if err != nil {
		t.Fatal(err)
	}
	if len(tags) != 2 {
		t.Fatalf("ListTags = %d tags, want 2", len(tags))
	}
}

func TestListRepositories(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	if _, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "a", Name: "one"}); err != nil {
		t.Fatal(err)
	}
	if _, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "b", Name: "two"}); err != nil {
		t.Fatal(err)
	}

	repos, err := store.ListRepositories(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(repos) < 2 {
		t.Fatalf("ListRepositories = %d, want >= 2", len(repos))
	}
}

func TestPutUploadedBlob(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	repoID, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}
	dgst := digest.FromString("uploaded-blob")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: 100}); err != nil {
		t.Fatal(err)
	}

	if err := store.PutUploadedBlob(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}
}

func TestCleanExpiredUploadedBlobs(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	err := store.CleanExpiredUploadedBlobs(ctx)
	if err != nil {
		t.Fatal(err)
	}
}
