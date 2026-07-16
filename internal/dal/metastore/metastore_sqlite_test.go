package metastore_test

import (
	"context"
	"database/sql"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

func setupStore(t *testing.T) oci.MetadataStore {
	t.Helper()
	return setupStoreWithOptions(t)
}

func setupStoreWithNow(t *testing.T, nowMs func() int64) oci.MetadataStore {
	t.Helper()
	return setupStoreWithOptions(t, metastore.WithNowFunc(nowMs))
}

func setupStoreWithOptions(t *testing.T, opts ...metastore.SQLiteStoreOption) oci.MetadataStore {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	store, err := metastore.NewSQLiteStore(t.Context(), db, opts...)
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func setupConcurrentStores(t *testing.T, nowMs func() int64) (first, second *metastore.SQLiteStore, lockDB *sql.DB) {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	firstDB, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = firstDB.Close() })
	secondDB, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = secondDB.Close() })
	lockDB, err = dbcore.OpenSQLite(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = lockDB.Close() })

	first, err = metastore.NewSQLiteStore(t.Context(), firstDB, metastore.WithNowFunc(nowMs))
	if err != nil {
		t.Fatal(err)
	}
	second, err = metastore.NewSQLiteStore(t.Context(), secondDB, metastore.WithNowFunc(nowMs))
	if err != nil {
		t.Fatal(err)
	}
	return first, second, lockDB
}

type concurrentTagOperationResult struct {
	name string
	err  error
}

func holdWriterLock(t *testing.T, db *sql.DB) *sql.Tx {
	t.Helper()
	tx, err := db.BeginTx(t.Context(), nil)
	if err != nil {
		t.Fatalf("begin writer lock transaction: %v", err)
	}
	t.Cleanup(func() { _ = tx.Rollback() })
	if _, err := tx.ExecContext(t.Context(),
		`UPDATE alembic_version SET version_num = version_num`,
	); err != nil {
		t.Fatalf("acquire writer lock: %v", err)
	}
	return tx
}

func assertTagOperationsBlocked(
	t *testing.T,
	stores []*metastore.SQLiteStore,
	results <-chan concurrentTagOperationResult,
) {
	t.Helper()
	require.Eventually(t, func() bool {
		for _, store := range stores {
			if store.DB().Stats().InUse != 1 {
				return false
			}
		}
		return true
	}, time.Second, time.Millisecond, "store operations did not check out their database connections")

	select {
	case result := <-results:
		t.Fatalf("%s returned before the writer lock was released: %v", result.name, result.err)
	case <-time.After(100 * time.Millisecond):
	}
}

func collectTagOperationResults(
	t *testing.T,
	stores []*metastore.SQLiteStore,
	results <-chan concurrentTagOperationResult,
) {
	t.Helper()
	for range stores {
		select {
		case result := <-results:
			if result.err != nil {
				t.Errorf("%s: %v", result.name, result.err)
			}
		case <-time.After(2 * time.Second):
			t.Fatal("tag operation did not complete after the writer lock was released")
		}
	}
	require.Eventually(t, func() bool {
		for _, store := range stores {
			if store.DB().Stats().InUse != 0 {
				return false
			}
		}
		return true
	}, time.Second, time.Millisecond, "tag operations did not release their database connections")
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

func TestPutManifest_SameDigestTagRetryNoop(t *testing.T) {
	now := int64(10_000)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst := digest.FromString("manifest-retry")
	record := oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":1}`),
		Tag:       "latest",
	}

	if _, err := store.PutManifest(ctx, repoID, record); err != nil {
		t.Fatal(err)
	}
	rows := getTagRows(t, store.(*metastore.SQLiteStore), repoID, "latest")
	if len(rows) != 1 {
		t.Fatalf("tag rows after first push: got %d, want 1", len(rows))
	}
	firstTagID := rows[0].id

	now++
	if _, err := store.PutManifest(ctx, repoID, record); err != nil {
		t.Fatal(err)
	}

	rows = getTagRows(t, store.(*metastore.SQLiteStore), repoID, "latest")
	if len(rows) != 1 {
		t.Fatalf("tag rows after retry: got %d, want 1", len(rows))
	}
	if rows[0].id != firstTagID {
		t.Fatalf("tag row ID after retry: got %d, want %d", rows[0].id, firstTagID)
	}
	assertActiveTagCount(t, store.(*metastore.SQLiteStore), repoID, "latest", 1)
}

func TestPutManifest_TagRetargetAvoidsExpiredTimestampCollision(t *testing.T) {
	now := int64(20_000)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	dgst1 := digest.FromString("manifest-collision-v1")
	dgst2 := digest.FromString("manifest-collision-v2")
	dgst3 := digest.FromString("manifest-collision-v3")

	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst1,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":1}`),
		Tag:       "latest",
	}); err != nil {
		t.Fatal(err)
	}

	now++
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst2,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":2}`),
		Tag:       "latest",
	}); err != nil {
		t.Fatal(err)
	}

	// Retarget in the same millisecond as the existing expired row. The old
	// expire query attempted to reuse this lifetime_end_ms and violated the
	// tag_repository_id_name_lifetime_end_ms unique index.
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst3,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":3}`),
		Tag:       "latest",
	}); err != nil {
		t.Fatal(err)
	}

	got, err := store.GetTagDigest(ctx, repoID, "latest")
	if err != nil {
		t.Fatal(err)
	}
	if got != dgst3 {
		t.Fatalf("active tag digest: got %s, want %s", got, dgst3)
	}
	assertActiveTagCount(t, store.(*metastore.SQLiteStore), repoID, "latest", 1)
	assertExpiredTagCount(t, store.(*metastore.SQLiteStore), repoID, "latest", 2)
	assertTagIntervalsValid(t, store.(*metastore.SQLiteStore), repoID, "latest")
}

func TestPutManifest_TagRetargetClampsBackwardClock(t *testing.T) {
	now := int64(40_000)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	for i, dgst := range []digest.Digest{
		digest.FromString("backward-retarget-v1"),
		digest.FromString("backward-retarget-v2"),
	} {
		if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    dgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
			Tag:       "latest",
		}); err != nil {
			t.Fatal(err)
		}
		if i == 0 {
			now--
		}
	}

	rows := getTagRows(t, store.(*metastore.SQLiteStore), repoID, "latest")
	if len(rows) != 2 {
		t.Fatalf("tag rows = %d, want 2", len(rows))
	}
	if !rows[0].lifetimeEndMs.Valid || rows[0].lifetimeEndMs.Int64 != 40_000 {
		t.Fatalf("expired tag end = %v, want 40000", rows[0].lifetimeEndMs)
	}
	if rows[1].lifetimeStartMs != 40_000 {
		t.Fatalf("replacement tag start = %d, want 40000", rows[1].lifetimeStartMs)
	}
	assertTagIntervalsValid(t, store.(*metastore.SQLiteStore), repoID, "latest")
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

func TestPutTag_ConcurrentStoresSerializeRetargets(t *testing.T) {
	first, second, lockDB := setupConcurrentStores(t, func() int64 { return 60_000 })
	ctx := t.Context()

	repoID, err := first.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	digests := []digest.Digest{digest.FromString("concurrent-put-one"), digest.FromString("concurrent-put-two")}
	for _, dgst := range digests {
		if _, err := first.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    dgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
		}); err != nil {
			t.Fatal(err)
		}
	}

	writerLock := holdWriterLock(t, lockDB)
	stores := []*metastore.SQLiteStore{first, second}
	names := []string{"first PutTag", "second PutTag"}
	results := make(chan concurrentTagOperationResult, len(stores))
	for i, store := range stores {
		dgst := digests[i]
		name := names[i]
		go func() {
			_, err := store.PutTag(ctx, repoID, oci.TagRecord{Name: "latest", Digest: dgst})
			results <- concurrentTagOperationResult{name: name, err: err}
		}()
	}
	assertTagOperationsBlocked(t, stores, results)
	require.NoError(t, writerLock.Rollback())
	collectTagOperationResults(t, stores, results)

	if rows := getTagRows(t, first, repoID, "latest"); len(rows) != 2 {
		t.Fatalf("tag rows = %d, want 2", len(rows))
	}
	assertActiveTagCount(t, first, repoID, "latest", 1)
	assertTagIntervalsValid(t, first, repoID, "latest")
}

func TestPutAndDeleteTag_ConcurrentStoresSerialize(t *testing.T) {
	first, second, lockDB := setupConcurrentStores(t, func() int64 { return 70_000 })
	ctx := t.Context()

	repoID, err := first.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	digest1 := digest.FromString("concurrent-delete-one")
	digest2 := digest.FromString("concurrent-delete-two")
	for _, dgst := range []digest.Digest{digest1, digest2} {
		if _, err := first.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    dgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
		}); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := first.PutTag(ctx, repoID, oci.TagRecord{Name: "latest", Digest: digest1}); err != nil {
		t.Fatal(err)
	}

	writerLock := holdWriterLock(t, lockDB)
	stores := []*metastore.SQLiteStore{first, second}
	results := make(chan concurrentTagOperationResult, len(stores))
	go func() {
		_, err := first.PutTag(ctx, repoID, oci.TagRecord{Name: "latest", Digest: digest2})
		results <- concurrentTagOperationResult{name: "PutTag", err: err}
	}()
	go func() {
		results <- concurrentTagOperationResult{name: "DeleteTag", err: second.DeleteTag(ctx, repoID, "latest")}
	}()
	assertTagOperationsBlocked(t, stores, results)
	require.NoError(t, writerLock.Rollback())
	collectTagOperationResults(t, stores, results)

	rows := getTagRows(t, first, repoID, "latest")
	if len(rows) != 2 {
		t.Fatalf("tag rows = %d, want 2", len(rows))
	}
	active := 0
	for _, row := range rows {
		if !row.lifetimeEndMs.Valid {
			active++
		}
	}
	if active > 1 {
		t.Fatalf("active tag rows = %d, want at most 1", active)
	}
	assertTagIntervalsValid(t, first, repoID, "latest")
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

func TestDeleteTagAvoidsExpiredTimestampCollision(t *testing.T) {
	now := int64(30_000)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    digest.FromString("delete-collision-v1"),
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":1}`),
		Tag:       "removeme",
	}); err != nil {
		t.Fatal(err)
	}

	now++
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    digest.FromString("delete-collision-v2"),
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"v":2}`),
		Tag:       "removeme",
	}); err != nil {
		t.Fatal(err)
	}

	if err := store.DeleteTag(ctx, repoID, "removeme"); err != nil {
		t.Fatal(err)
	}

	assertActiveTagCount(t, store.(*metastore.SQLiteStore), repoID, "removeme", 0)
	assertExpiredTagCount(t, store.(*metastore.SQLiteStore), repoID, "removeme", 2)
	assertTagIntervalsValid(t, store.(*metastore.SQLiteStore), repoID, "removeme")
}

func TestDeleteTagClampsBackwardClock(t *testing.T) {
	now := int64(50_000)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    digest.FromString("backward-delete"),
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
		Tag:       "removeme",
	}); err != nil {
		t.Fatal(err)
	}

	now--
	if err := store.DeleteTag(ctx, repoID, "removeme"); err != nil {
		t.Fatal(err)
	}

	rows := getTagRows(t, store.(*metastore.SQLiteStore), repoID, "removeme")
	if len(rows) != 1 {
		t.Fatalf("tag rows = %d, want 1", len(rows))
	}
	if !rows[0].lifetimeEndMs.Valid || rows[0].lifetimeEndMs.Int64 != 50_000 {
		t.Fatalf("expired tag end = %v, want 50000", rows[0].lifetimeEndMs)
	}
	assertTagIntervalsValid(t, store.(*metastore.SQLiteStore), repoID, "removeme")
}

func TestPutManifest_TagRecreateClampsToExpiredEndAfterBackwardClock(t *testing.T) {
	now := int64(100)
	store := setupStoreWithNow(t, func() int64 { return now })
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: digest.FromString("rollback-recreate-first"), MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	}); err != nil {
		t.Fatal(err)
	}

	now = 300
	if err := store.DeleteTag(ctx, repoID, "latest"); err != nil {
		t.Fatal(err)
	}

	now = 200
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: digest.FromString("rollback-recreate-second"), MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	}); err != nil {
		t.Fatal(err)
	}

	rows := getTagRows(t, store.(*metastore.SQLiteStore), repoID, "latest")
	if len(rows) != 2 {
		t.Fatalf("tag rows = %d, want 2", len(rows))
	}
	if rows[1].lifetimeStartMs != 300 {
		t.Fatalf("recreated tag start = %d, want prior end 300", rows[1].lifetimeStartMs)
	}
	assertTagIntervalsValid(t, store.(*metastore.SQLiteStore), repoID, "latest")
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

func TestPutManifest_ReferrerProtectionUsesFullDigestIdentity(t *testing.T) {
	store := setupStore(t)
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}

	subjectDgst := digest.FromString("shared-subject")
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    subjectDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
	}); err != nil {
		t.Fatal(err)
	}

	sharedPrefix := strings.Repeat("a", 12)
	referrerDigests := []digest.Digest{
		digest.NewDigestFromEncoded(digest.SHA256, sharedPrefix+strings.Repeat("1", 52)),
		digest.NewDigestFromEncoded(digest.SHA256, sharedPrefix+strings.Repeat("2", 52)),
	}
	for _, referrerDgst := range referrerDigests {
		record := oci.ManifestRecord{
			Digest:    referrerDgst,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
			Subject:   subjectDgst,
		}
		if _, err := store.PutManifest(ctx, repoID, record); err != nil {
			t.Fatal(err)
		}
	}

	// Retrying the same referrer must keep its existing protection row.
	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    referrerDigests[0],
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
		Subject:   subjectDgst,
	}); err != nil {
		t.Fatal(err)
	}

	rows, err := store.(*metastore.SQLiteStore).DB().QueryContext(ctx,
		`SELECT t.name, m.digest
		 FROM tag AS t
		 JOIN manifest AS m ON m.id = t.manifest_id
		 WHERE t.repository_id = ? AND t.hidden = 1 AND t.lifetime_end_ms IS NULL
		 ORDER BY t.name`, repoID)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = rows.Close() }()

	want := map[string]string{
		"$referrer-sha256-" + referrerDigests[0].Encoded(): referrerDigests[0].String(),
		"$referrer-sha256-" + referrerDigests[1].Encoded(): referrerDigests[1].String(),
	}
	got := make(map[string]string)
	for rows.Next() {
		var name, manifestDigest string
		if err := rows.Scan(&name, &manifestDigest); err != nil {
			t.Fatal(err)
		}
		got[name] = manifestDigest
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	if len(got) != len(want) {
		t.Fatalf("active hidden protection rows = %v, want %v", got, want)
	}
	for name, manifestDigest := range want {
		if got[name] != manifestDigest {
			t.Errorf("protection row %q points to %q, want %q", name, got[name], manifestDigest)
		}
	}
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

// --- test helpers ---

type tagRow struct {
	id              int64
	manifestID      sql.NullInt64
	lifetimeStartMs int64
	lifetimeEndMs   sql.NullInt64
}

func getTagRows(t *testing.T, s *metastore.SQLiteStore, repoID int64, tag string) []tagRow {
	t.Helper()
	db := s.DB()
	rows, err := db.QueryContext(context.Background(),
		`SELECT id, manifest_id, lifetime_start_ms, lifetime_end_ms
		 FROM tag
		 WHERE repository_id = ? AND name = ?
		 ORDER BY id`,
		repoID, tag)
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = rows.Close() }()

	var result []tagRow
	for rows.Next() {
		var row tagRow
		if err := rows.Scan(&row.id, &row.manifestID, &row.lifetimeStartMs, &row.lifetimeEndMs); err != nil {
			t.Fatal(err)
		}
		result = append(result, row)
	}
	if err := rows.Err(); err != nil {
		t.Fatal(err)
	}
	return result
}

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

func assertExpiredTagCount(t *testing.T, s *metastore.SQLiteStore, repoID int64, tag string, want int) {
	t.Helper()
	rows := getTagRows(t, s, repoID, tag)
	got := 0
	for _, row := range rows {
		if !row.lifetimeEndMs.Valid {
			continue
		}
		got++
	}
	if got != want {
		t.Fatalf("expired tags named %q: got %d, want %d", tag, got, want)
	}
}

func assertTagIntervalsValid(t *testing.T, s *metastore.SQLiteStore, repoID int64, tag string) {
	t.Helper()
	rows := getTagRows(t, s, repoID, tag)
	for i, row := range rows {
		if row.lifetimeEndMs.Valid && row.lifetimeEndMs.Int64 < row.lifetimeStartMs {
			t.Fatalf("tag row %d has invalid interval: start=%d end=%d", row.id, row.lifetimeStartMs, row.lifetimeEndMs.Int64)
		}
		if i > 0 && rows[i-1].lifetimeEndMs.Valid && rows[i-1].lifetimeEndMs.Int64 > row.lifetimeStartMs {
			t.Fatalf(
				"tag rows %d and %d overlap: prior end=%d current start=%d",
				rows[i-1].id, row.id, rows[i-1].lifetimeEndMs.Int64, row.lifetimeStartMs,
			)
		}
	}
}
