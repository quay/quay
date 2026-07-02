package gc_test

import (
	"context"
	"database/sql"
	"log/slog"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/gc"
	"github.com/quay/quay/internal/oci"
	"github.com/quay/quay/internal/oci/storage/local"
)

type testEnv struct {
	db        *sql.DB
	store     oci.MetadataStore
	blobs     oci.BlobStore
	collector gc.Collector
	q         *daldb.Queries
}

func setup(t *testing.T) *testEnv {
	t.Helper()
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = db.Close() })

	store, err := metastore.NewSQLiteStore(t.Context(), db)
	if err != nil {
		t.Fatal(err)
	}

	storagePath := filepath.Join(dir, "storage")
	blobs, err := local.New(storagePath)
	if err != nil {
		t.Fatal(err)
	}

	log := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelDebug}))
	gcStore := gc.NewSQLiteStore(db)
	collector := gc.NewCollector(gcStore, blobs, log)

	return &testEnv{
		db:        db,
		store:     store,
		blobs:     blobs,
		collector: collector,
		q:         daldb.New(db),
	}
}

func mustDigest(s string) digest.Digest {
	return digest.FromString(s)
}

// ensureRepo creates a repository and returns its ID.
func ensureRepo(t *testing.T, env *testEnv, ns, name string) int64 {
	t.Helper()
	id, err := env.store.EnsureRepository(t.Context(), oci.RepositoryName{Namespace: ns, Name: name})
	if err != nil {
		t.Fatal(err)
	}
	return id
}

// insertManifest creates a manifest and returns its ID.
func insertManifest(t *testing.T, env *testEnv, repoID int64, dgst digest.Digest) int64 {
	t.Helper()
	id, err := env.store.PutManifest(t.Context(), repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
	})
	if err != nil {
		t.Fatal(err)
	}
	return id
}

// insertTag creates a live tag pointing to a manifest.
func insertTag(t *testing.T, env *testEnv, repoID int64, name string, dgst digest.Digest) {
	t.Helper()
	_, err := env.store.PutTag(t.Context(), repoID, oci.TagRecord{Name: name, Digest: dgst})
	if err != nil {
		t.Fatal(err)
	}
}

// linkBlobToManifest creates a manifestblob row.
func linkBlobToManifest(t *testing.T, env *testEnv, repoID, manifestID, blobID int64) {
	t.Helper()
	if err := env.q.LinkManifestBlob(t.Context(), daldb.LinkManifestBlobParams{
		RepositoryID: repoID,
		ManifestID:   manifestID,
		BlobID:       blobID,
	}); err != nil {
		t.Fatal(err)
	}
}

// expireTag sets lifetime_end_ms on a tag.
func expireTag(t *testing.T, env *testEnv, repoID int64, name string, endMs int64) {
	t.Helper()
	res, err := env.q.ExpireActiveTag(t.Context(), daldb.ExpireActiveTagParams{
		LifetimeEndMs: sql.NullInt64{Int64: endMs, Valid: true},
		RepositoryID:  repoID,
		Name:          name,
	})
	if err != nil {
		t.Fatal(err)
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		t.Fatalf("no active tag %q found to expire", name)
	}
}

func TestCollect_NoGarbage(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("manifest-live")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "latest", dgst)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 0 || stats.ManifestsDeleted != 0 || stats.BlobsDeleted != 0 {
		t.Fatalf("expected no garbage, got %+v", stats)
	}
}

func TestCollect_ExpiredTagAndOrphanedManifest(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("manifest-to-expire")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "old", dgst)

	// Expire the tag far in the past (beyond the default 14-day grace period).
	pastMs := (time.Now().Add(-30 * 24 * time.Hour)).UnixMilli()
	expireTag(t, env, repoID, "old", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest, got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_OrphanedBlob(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	content := []byte("orphaned-blob-data")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}
	_, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.BlobsDeleted != 1 {
		t.Fatalf("expected 1 deleted blob, got %d", stats.BlobsDeleted)
	}

	// Verify storage file is gone.
	_, err = env.blobs.Stat(ctx, dgst)
	if err == nil {
		t.Fatal("expected blob storage to be deleted")
	}
}

func TestCollect_BlobProtectedByUploadedBlob(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	content := []byte("protected-blob")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}
	_, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}

	// Protect with uploadedblob (expires in 1 hour).
	if err := env.store.PutUploadedBlob(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.BlobsDeleted != 0 {
		t.Fatalf("expected 0 deleted blobs (protected by uploadedblob), got %d", stats.BlobsDeleted)
	}

	// Verify storage file still exists.
	_, err = env.blobs.Stat(ctx, dgst)
	if err != nil {
		t.Fatalf("blob should still exist: %v", err)
	}
}

func TestCollect_BlobReferencedByManifest(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	manifestDgst := mustDigest("live-manifest")
	manifestID := insertManifest(t, env, repoID, manifestDgst)
	insertTag(t, env, repoID, "latest", manifestDgst)

	content := []byte("referenced-blob")
	blobDgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, blobDgst, content); err != nil {
		t.Fatal(err)
	}
	blobID, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: blobDgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}
	linkBlobToManifest(t, env, repoID, manifestID, blobID)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.BlobsDeleted != 0 {
		t.Fatalf("expected 0 deleted blobs (referenced by manifest), got %d", stats.BlobsDeleted)
	}
}

func TestCollect_ManifestChildProtected(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	// Create parent manifest list (tagged).
	parentDgst := mustDigest("parent-manifest-list")
	insertManifest(t, env, repoID, parentDgst)
	insertTag(t, env, repoID, "latest", parentDgst)

	// Create child manifest (untagged, but referenced by parent).
	childDgst := mustDigest("child-platform-manifest")
	childID := insertManifest(t, env, repoID, childDgst)

	// Link child to parent via manifestchild.
	parentID := getManifestID(t, env, repoID, parentDgst)
	if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
		RepositoryID:    repoID,
		ManifestID:      parentID,
		ChildManifestID: childID,
	}); err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests (child protected by parent), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_ManifestProtectedAsReferrerTarget(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	// Create the base manifest (UNTAGGED — would normally be orphaned).
	baseDgst := mustDigest("base-manifest")
	insertManifest(t, env, repoID, baseDgst)

	// Create a referrer manifest (tagged) with subject pointing to base.
	// This protects the BASE from GC because another manifest's subject
	// field references it.
	referrerDgst := mustDigest("referrer-manifest")
	_, err := env.q.UpsertManifest(ctx, daldb.UpsertManifestParams{
		RepositoryID:  repoID,
		Digest:        referrerDgst.String(),
		MediaTypeID:   1,
		ManifestBytes: `{"schemaVersion":2}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	// Set the subject field on the referrer to point at the base.
	_, err = env.db.ExecContext(ctx,
		"UPDATE manifest SET subject = ? WHERE repository_id = ? AND digest = ?",
		baseDgst.String(), repoID, referrerDgst.String(),
	)
	if err != nil {
		t.Fatal(err)
	}
	insertTag(t, env, repoID, "sig", referrerDgst)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	// The base manifest should survive because the referrer's subject points to it.
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests (base protected as referrer target), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_CascadeParentToChildren(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	// Parent manifest list with an expired tag.
	parentDgst := mustDigest("parent-expired")
	insertManifest(t, env, repoID, parentDgst)
	insertTag(t, env, repoID, "old-list", parentDgst)

	// Two children, untagged.
	child1Dgst := mustDigest("child-1")
	child1ID := insertManifest(t, env, repoID, child1Dgst)
	child2Dgst := mustDigest("child-2")
	child2ID := insertManifest(t, env, repoID, child2Dgst)

	parentID := getManifestID(t, env, repoID, parentDgst)
	for _, childID := range []int64{child1ID, child2ID} {
		if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
			RepositoryID:    repoID,
			ManifestID:      parentID,
			ChildManifestID: childID,
		}); err != nil {
			t.Fatal(err)
		}
	}

	// Expire the parent's tag far in the past.
	pastMs := (time.Now().Add(-30 * 24 * time.Hour)).UnixMilli()
	expireTag(t, env, repoID, "old-list", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	// Parent + 2 children should all be deleted.
	if stats.ManifestsDeleted != 3 {
		t.Fatalf("expected 3 deleted manifests (parent + 2 children), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_TagWithinGracePeriodSurvives(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("recently-expired-manifest")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "recent", dgst)

	// Expire the tag 5 days ago — within the default 14-day grace period.
	fiveDaysAgoMs := time.Now().Add(-5 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "recent", fiveDaysAgoMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 0 {
		t.Fatalf("expected 0 expired tags (within grace period), got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests, got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_MultipleRepos(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	// Repo A: has an expired tag.
	repoA := ensureRepo(t, env, "org", "app-a")
	dgstA := mustDigest("manifest-a")
	insertManifest(t, env, repoA, dgstA)
	insertTag(t, env, repoA, "old", dgstA)
	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoA, "old", pastMs)

	// Repo B: has a live tag — should be untouched.
	repoB := ensureRepo(t, env, "org", "app-b")
	dgstB := mustDigest("manifest-b")
	insertManifest(t, env, repoB, dgstB)
	insertTag(t, env, repoB, "latest", dgstB)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag (from repo A), got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest (from repo A), got %d", stats.ManifestsDeleted)
	}

	// Verify repo B's manifest still exists.
	_, err = env.q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoB,
		Digest:       dgstB.String(),
	})
	if err != nil {
		t.Fatalf("repo B manifest should survive: %v", err)
	}
}

func TestCollect_SharedBlobSurvivesPartialManifestDeletion(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	// Create a shared blob (like a common base layer).
	sharedContent := []byte("shared-base-layer-data")
	sharedDgst := digest.FromBytes(sharedContent)
	if err := env.blobs.PutContent(ctx, sharedDgst, sharedContent); err != nil {
		t.Fatal(err)
	}
	sharedBlobID, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: sharedDgst, Size: int64(len(sharedContent))})
	if err != nil {
		t.Fatal(err)
	}

	// Manifest A (tagged "latest") references the shared blob.
	dgstA := mustDigest("manifest-a-live")
	manifestA := insertManifest(t, env, repoID, dgstA)
	insertTag(t, env, repoID, "latest", dgstA)
	linkBlobToManifest(t, env, repoID, manifestA, sharedBlobID)

	// Manifest B (tag expired) also references the shared blob.
	dgstB := mustDigest("manifest-b-expired")
	manifestB := insertManifest(t, env, repoID, dgstB)
	insertTag(t, env, repoID, "old", dgstB)
	linkBlobToManifest(t, env, repoID, manifestB, sharedBlobID)

	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "old", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest (B), got %d", stats.ManifestsDeleted)
	}
	// Shared blob must survive — still referenced by manifest A.
	if stats.BlobsDeleted != 0 {
		t.Fatalf("expected 0 deleted blobs (shared blob still referenced by A), got %d", stats.BlobsDeleted)
	}
	_, err = env.blobs.Stat(ctx, sharedDgst)
	if err != nil {
		t.Fatalf("shared blob storage should survive: %v", err)
	}
}

func TestCollect_StaleUploadMissingStartedAtFallsBackToMtime(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	// Create an upload directory manually WITHOUT a startedat file.
	uploadID, err := env.blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}

	// Write data but no startedat.
	w, err := env.blobs.UploadWriter(ctx, uploadID, false)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write([]byte("data without startedat")); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	// Backdate the data file's mtime to 3 days ago.
	localBlobs := env.blobs.(*local.Driver)
	dataPath := filepath.Join(localBlobs.RootDir(), "uploads", uploadID, "data")
	threeDaysAgo := time.Now().Add(-72 * time.Hour)
	if err := os.Chtimes(dataPath, threeDaysAgo, threeDaysAgo); err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.StaleUploadsRemoved != 1 {
		t.Fatalf("expected 1 stale upload removed (mtime fallback), got %d", stats.StaleUploadsRemoved)
	}
}

func TestCollect_StaleUploadRemoved(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	// Create an upload and write a startedat timestamp 3 days ago.
	uploadID, err := env.blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}

	threeDaysAgo := time.Now().Add(-72 * time.Hour).UTC().Format(time.RFC3339)
	if err := env.blobs.PutUploadState(ctx, uploadID, "startedat", []byte(threeDaysAgo)); err != nil {
		t.Fatal(err)
	}

	// Write some data to the upload.
	w, err := env.blobs.UploadWriter(ctx, uploadID, false)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := w.Write([]byte("abandoned upload data - 500MB pretend")); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.StaleUploadsRemoved != 1 {
		t.Fatalf("expected 1 stale upload removed, got %d", stats.StaleUploadsRemoved)
	}

	// Verify the upload directory is gone.
	_, err = env.blobs.UploadStat(ctx, uploadID)
	if err == nil {
		t.Fatal("expected stale upload to be removed")
	}
}

func TestCollect_RecentUploadSurvives(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	// Create an upload with startedat = now (fresh, within 48h threshold).
	uploadID, err := env.blobs.InitUpload(ctx)
	if err != nil {
		t.Fatal(err)
	}

	now := time.Now().UTC().Format(time.RFC3339)
	if err := env.blobs.PutUploadState(ctx, uploadID, "startedat", []byte(now)); err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.StaleUploadsRemoved != 0 {
		t.Fatalf("expected 0 stale uploads removed (recent upload), got %d", stats.StaleUploadsRemoved)
	}

	// Verify the upload still exists.
	_, err = env.blobs.UploadStat(ctx, uploadID)
	if err != nil {
		t.Fatalf("recent upload should survive GC: %v", err)
	}
}

func getManifestID(t *testing.T, env *testEnv, repoID int64, dgst digest.Digest) int64 {
	t.Helper()
	m, err := env.q.GetManifestByDigest(ctx(t), daldb.GetManifestByDigestParams{
		RepositoryID: repoID,
		Digest:       dgst.String(),
	})
	if err != nil {
		t.Fatal(err)
	}
	return m.ID
}

func ctx(t *testing.T) context.Context {
	t.Helper()
	return t.Context()
}
