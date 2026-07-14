package gc_test

import (
	"context"
	"database/sql"
	"errors"
	"log/slog"
	"os"
	"path/filepath"
	"sync"
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

func TestCollect_TwoTagsSharedManifest_PartialExpiry(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("shared-manifest")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "latest", dgst)
	insertTag(t, env, repoID, "v1.0", dgst)

	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "v1.0", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests (latest still live), got %d", stats.ManifestsDeleted)
	}
	_, err = env.q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID, Digest: dgst.String(),
	})
	if err != nil {
		t.Fatal("manifest should still exist")
	}
}

func TestCollect_AllTagsExpired_ManifestCollected(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("both-tags-expire")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "v1.0", dgst)
	insertTag(t, env, repoID, "v2.0", dgst)

	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "v1.0", pastMs)
	expireTag(t, env, repoID, "v2.0", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 2 {
		t.Fatalf("expected 2 expired tags, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest, got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_CrossRepoManifestChildProtection(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoA := ensureRepo(t, env, "org", "parent-repo")
	repoB := ensureRepo(t, env, "org", "child-repo")

	parentDgst := mustDigest("cross-repo-parent")
	insertManifest(t, env, repoA, parentDgst)
	insertTag(t, env, repoA, "latest", parentDgst)

	childDgst := mustDigest("cross-repo-child")
	childID := insertManifest(t, env, repoB, childDgst)

	parentID := getManifestID(t, env, repoA, parentDgst)
	if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
		RepositoryID:    repoA,
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
		t.Fatalf("expected 0 deleted manifests (cross-repo child protected), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_CrossRepoSubjectReferrerProtection(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoA := ensureRepo(t, env, "org", "base-repo")
	repoB := ensureRepo(t, env, "org", "referrer-repo")

	baseDgst := mustDigest("cross-repo-base")
	insertManifest(t, env, repoA, baseDgst)

	referrerDgst := mustDigest("cross-repo-referrer")
	_, err := env.q.UpsertManifest(ctx, daldb.UpsertManifestParams{
		RepositoryID:  repoB,
		Digest:        referrerDgst.String(),
		MediaTypeID:   1,
		ManifestBytes: `{"schemaVersion":2}`,
	})
	if err != nil {
		t.Fatal(err)
	}
	_, err = env.db.ExecContext(ctx,
		"UPDATE manifest SET subject = ? WHERE repository_id = ? AND digest = ?",
		baseDgst.String(), repoB, referrerDgst.String(),
	)
	if err != nil {
		t.Fatal(err)
	}
	insertTag(t, env, repoB, "sig", referrerDgst)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests (cross-repo subject protection), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_ChildSharedByTwoParents(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	childDgst := mustDigest("shared-child")
	childID := insertManifest(t, env, repoID, childDgst)

	parentADgst := mustDigest("parent-a")
	insertManifest(t, env, repoID, parentADgst)
	insertTag(t, env, repoID, "v1", parentADgst)
	parentAID := getManifestID(t, env, repoID, parentADgst)

	parentBDgst := mustDigest("parent-b")
	insertManifest(t, env, repoID, parentBDgst)
	insertTag(t, env, repoID, "v2", parentBDgst)
	parentBID := getManifestID(t, env, repoID, parentBDgst)

	for _, parentID := range []int64{parentAID, parentBID} {
		if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
			RepositoryID: repoID, ManifestID: parentID, ChildManifestID: childID,
		}); err != nil {
			t.Fatal(err)
		}
	}

	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "v1", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest (parent A only), got %d", stats.ManifestsDeleted)
	}
	_, err = env.q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID, Digest: childDgst.String(),
	})
	if err != nil {
		t.Fatal("shared child should survive")
	}
}

func TestCollect_DeepCascade_ThreeLevels(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	grandchildDgst := mustDigest("grandchild")
	grandchildID := insertManifest(t, env, repoID, grandchildDgst)

	childDgst := mustDigest("child-mid")
	childID := insertManifest(t, env, repoID, childDgst)

	parentDgst := mustDigest("parent-top")
	insertManifest(t, env, repoID, parentDgst)
	insertTag(t, env, repoID, "latest", parentDgst)
	parentID := getManifestID(t, env, repoID, parentDgst)

	if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
		RepositoryID: repoID, ManifestID: parentID, ChildManifestID: childID,
	}); err != nil {
		t.Fatal(err)
	}
	if err := env.q.LinkManifestChild(ctx, daldb.LinkManifestChildParams{
		RepositoryID: repoID, ManifestID: childID, ChildManifestID: grandchildID,
	}); err != nil {
		t.Fatal(err)
	}

	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "latest", pastMs)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.TagsExpired != 1 {
		t.Fatalf("expected 1 expired tag, got %d", stats.TagsExpired)
	}
	if stats.ManifestsDeleted != 3 {
		t.Fatalf("expected 3 deleted manifests (parent+child+grandchild), got %d", stats.ManifestsDeleted)
	}
}

func TestCollect_SharedChecksumBlobDedup(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	content := []byte("shared-checksum-blob")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}

	liveBlobID, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}
	manifestDgst := mustDigest("live-manifest-with-shared-blob")
	manifestID := insertManifest(t, env, repoID, manifestDgst)
	insertTag(t, env, repoID, "latest", manifestDgst)
	linkBlobToManifest(t, env, repoID, manifestID, liveBlobID)

	res, err := env.db.ExecContext(ctx,
		`INSERT INTO imagestorage (uuid, image_size, uploading, cas_path, content_checksum)
		 VALUES (?, ?, 0, 1, ?)`,
		"uuid-orphan-duplicate", int64(len(content)), dgst.String(),
	)
	if err != nil {
		t.Fatal(err)
	}
	orphanID, _ := res.LastInsertId()
	_ = orphanID

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.BlobsDeleted != 1 {
		t.Fatalf("expected 1 deleted blob (orphan duplicate), got %d", stats.BlobsDeleted)
	}
	_, err = env.blobs.Stat(ctx, dgst)
	if err != nil {
		t.Fatal("storage file should survive (another imagestorage row shares the checksum)")
	}
}

func TestCollect_ExpiredUploadedBlobStopsProtecting(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	content := []byte("soon-unprotected-blob")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}
	_, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}
	if err := env.store.PutUploadedBlob(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}

	_, err = env.db.ExecContext(ctx,
		"UPDATE uploadedblob SET expires_at = datetime('now', '-2 hours')")
	if err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.BlobsDeleted != 1 {
		t.Fatalf("expected 1 deleted blob (expired uploadedblob), got %d", stats.BlobsDeleted)
	}
	_, err = env.blobs.Stat(ctx, dgst)
	if err == nil {
		t.Fatal("storage file should be deleted")
	}
}

func TestCollect_Idempotent(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("idempotent-manifest")
	insertManifest(t, env, repoID, dgst)
	insertTag(t, env, repoID, "old", dgst)
	pastMs := time.Now().Add(-30 * 24 * time.Hour).UnixMilli()
	expireTag(t, env, repoID, "old", pastMs)

	stats1, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats1.TagsExpired != 1 || stats1.ManifestsDeleted != 1 {
		t.Fatalf("first cycle: expected 1 tag + 1 manifest, got %+v", stats1)
	}

	stats2, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats2.TagsExpired != 0 || stats2.ManifestsDeleted != 0 || stats2.BlobsDeleted != 0 {
		t.Fatalf("second cycle: expected all zeros, got %+v", stats2)
	}
}

func TestCollect_ConcurrentPushDuringGC(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	orphanContent := []byte("orphan-for-concurrent-test")
	orphanDgst := digest.FromBytes(orphanContent)
	if err := env.blobs.PutContent(ctx, orphanDgst, orphanContent); err != nil {
		t.Fatal(err)
	}
	_, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: orphanDgst, Size: int64(len(orphanContent))})
	if err != nil {
		t.Fatal(err)
	}

	pushContent := []byte("pushed-during-gc")
	pushDgst := digest.FromBytes(pushContent)

	var wg sync.WaitGroup
	var gcErr error
	var gcStats gc.Stats

	wg.Add(2)
	go func() {
		defer wg.Done()
		gcStats, gcErr = env.collector.Collect(ctx)
	}()
	go func() {
		defer wg.Done()
		if err := env.blobs.PutContent(ctx, pushDgst, pushContent); err != nil {
			return
		}
		_, _ = env.store.PutBlob(ctx, oci.BlobRecord{Digest: pushDgst, Size: int64(len(pushContent))})
		_ = env.store.PutUploadedBlob(ctx, repoID, pushDgst)
	}()
	wg.Wait()

	if gcErr != nil {
		t.Fatalf("GC should complete without error: %v", gcErr)
	}
	_ = gcStats

	_, err = env.blobs.Stat(ctx, pushDgst)
	if err != nil {
		t.Fatal("pushed blob should survive GC")
	}
}

func TestCollect_NeverTaggedManifest(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")
	dgst := mustDigest("never-tagged")
	insertManifest(t, env, repoID, dgst)

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.ManifestsDeleted != 1 {
		t.Fatalf("expected 1 deleted manifest (never tagged), got %d", stats.ManifestsDeleted)
	}
}

func TestWorker_StopsOnContextCancel(t *testing.T) {
	env := setup(t)

	worker := gc.NewWorker(env.collector, gc.Config{Interval: 50 * time.Millisecond},
		slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelError})))

	ctx, cancel := context.WithCancel(t.Context())
	errCh := make(chan error, 1)
	go func() { errCh <- worker.Run(ctx) }()

	time.Sleep(150 * time.Millisecond)
	cancel()

	select {
	case err := <-errCh:
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got %v", err)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("worker did not stop within 5 seconds")
	}
}

func TestCollect_ReferrerManifestProtectedByHiddenTag(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	// Push a base manifest (tagged).
	baseDgst := mustDigest("base-image")
	insertManifest(t, env, repoID, baseDgst)
	insertTag(t, env, repoID, "latest", baseDgst)

	// Push a referrer manifest (no user tag) with subject pointing to base.
	// PutManifest should create a hidden tag automatically.
	referrerDgst := mustDigest("sbom-referrer")
	_, err := env.store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    referrerDgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
		Subject:   baseDgst,
	})
	if err != nil {
		t.Fatal(err)
	}

	stats, err := env.collector.Collect(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if stats.ManifestsDeleted != 0 {
		t.Fatalf("expected 0 deleted manifests (referrer protected by hidden tag), got %d", stats.ManifestsDeleted)
	}

	// Verify both manifests still exist.
	_, err = env.q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID, Digest: baseDgst.String(),
	})
	if err != nil {
		t.Fatal("base manifest should exist")
	}
	_, err = env.q.GetManifestByDigest(ctx, daldb.GetManifestByDigestParams{
		RepositoryID: repoID, Digest: referrerDgst.String(),
	})
	if err != nil {
		t.Fatal("referrer manifest should exist (protected by hidden tag)")
	}
}

// TestRace_GCRevalidatesBeforeDelete simulates the race where GC finds an
// orphan candidate, then uploadedblob protection is added before GC deletes.
// GC must revalidate and skip the now-protected blob.
func TestRace_GCRevalidatesBeforeDelete(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	content := []byte("blob-in-flight")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}
	_, err := env.store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}

	// Step 1: GC finds the unprotected blob as orphan.
	gcStore := gc.NewSQLiteStore(env.db)
	orphans, err := gcStore.FindOrphanedBlobs(ctx)
	if err != nil {
		t.Fatal(err)
	}
	if len(orphans) == 0 {
		t.Fatal("expected FindOrphanedBlobs to find the unprotected blob")
	}

	// Step 2: Upload finishes — protection added.
	if err := env.store.PutUploadedBlob(ctx, repoID, dgst); err != nil {
		t.Fatal(err)
	}

	// Step 3: GC processes candidates — must skip the now-protected blob.
	ids := make([]int64, len(orphans))
	for i, o := range orphans {
		ids[i] = o.ID
	}
	safeChecksums, err := gcStore.DeleteBlobRecords(ctx, ids)
	if err != nil {
		t.Fatal(err)
	}
	if len(safeChecksums) > 0 {
		t.Fatalf("expected 0 safe checksums (blob now protected), got %v", safeChecksums)
	}

	// Verify blob survived in DB, uploadedblob intact, storage file intact.
	var count int
	if err := env.db.QueryRowContext(ctx, "SELECT COUNT(*) FROM imagestorage WHERE content_checksum = ?", dgst.String()).Scan(&count); err != nil {
		t.Fatal(err)
	}
	if count == 0 {
		t.Fatal("imagestorage row should survive")
	}
	_, err = env.blobs.Stat(ctx, dgst)
	if err != nil {
		t.Fatal("storage file should survive")
	}
}

// TestRace_AtomicBlobProtection verifies PutRepositoryBlob writes both
// imagestorage and uploadedblob in a single transaction so no window
// exists for GC to find an unprotected blob.
func TestRace_AtomicBlobProtection(t *testing.T) {
	env := setup(t)
	ctx := t.Context()

	repoID := ensureRepo(t, env, "library", "nginx")

	content := []byte("atomic-blob")
	dgst := digest.FromBytes(content)
	if err := env.blobs.PutContent(ctx, dgst, content); err != nil {
		t.Fatal(err)
	}

	// Use PutRepositoryBlob (atomic) instead of separate PutBlob + PutUploadedBlob.
	_, err := env.store.PutRepositoryBlob(ctx, repoID, oci.BlobRecord{Digest: dgst, Size: int64(len(content))})
	if err != nil {
		t.Fatal(err)
	}

	// GC should NOT find this blob as orphaned — uploadedblob was written atomically.
	gcStore := gc.NewSQLiteStore(env.db)
	orphans, err := gcStore.FindOrphanedBlobs(ctx)
	if err != nil {
		t.Fatal(err)
	}
	for _, o := range orphans {
		if o.ContentChecksum == dgst.String() {
			t.Fatalf("blob %s should NOT be found as orphaned (atomic protection)", dgst)
		}
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
