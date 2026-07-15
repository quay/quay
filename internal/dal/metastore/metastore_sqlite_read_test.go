package metastore_test

import (
	"bytes"
	"context"
	"path/filepath"
	"testing"

	"github.com/opencontainers/go-digest"
	"github.com/stretchr/testify/require"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/oci"
)

func testStore(t *testing.T, opts ...metastore.SQLiteStoreOption) (store *metastore.SQLiteStore, cleanup func()) {
	t.Helper()
	dbPath := filepath.Join(t.TempDir(), "quay.db")
	db, err := dbcore.Setup(t.Context(), dbPath)
	if err != nil {
		t.Fatal(err)
	}
	var err2 error
	store, err2 = metastore.NewSQLiteStore(t.Context(), db, opts...)
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

func TestGetManifestContent(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	name := oci.RepositoryName{Namespace: "ns", Name: "repo"}
	repoID, err := store.EnsureRepository(ctx, name)
	if err != nil {
		t.Fatal(err)
	}
	content := []byte(`{"schemaVersion":2}`)
	dgst := digest.FromBytes(content)

	if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    dgst,
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   content,
	}); err != nil {
		t.Fatal(err)
	}

	got, err := store.GetManifestContent(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, content) {
		t.Errorf("GetManifestContent = %s, want %s", got, content)
	}

	_, err = store.GetManifestContent(ctx, digest.FromString("missing"))
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
	require.ElementsMatch(t, []string{"v1", "v2"}, tags)
}

func TestListTags_RollbackRetarget(t *testing.T) {
	const tagStart = int64(100_000)
	now := tagStart
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "rollback-retarget"})
	require.NoError(t, err)

	firstDigest := digest.FromString("rollback-retarget-first")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: firstDigest, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	})
	require.NoError(t, err)

	now--
	secondDigest := digest.FromString("rollback-retarget-second")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: secondDigest, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	})
	require.NoError(t, err)

	rows := getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 2)
	require.Equal(t, tagStart, rows[0].lifetimeStartMs)
	require.Equal(t, tagStart, rows[0].lifetimeEndMs.Int64)
	require.Equal(t, tagStart, rows[1].lifetimeStartMs)
	require.False(t, rows[1].lifetimeEndMs.Valid)
	assertTagIntervalsValid(t, store, repoID, "latest")

	activeDigest, err := store.GetTagDigest(ctx, repoID, "latest")
	require.NoError(t, err)
	require.Equal(t, secondDigest, activeDigest)

	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)

	now = tagStart
	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)
}

func TestListTags_RollbackRetargetWithinPreviousInterval(t *testing.T) {
	now := int64(100)
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "rollback-overlap"})
	require.NoError(t, err)

	for _, manifest := range []struct {
		time   int64
		digest digest.Digest
	}{
		{time: 100, digest: digest.FromString("rollback-overlap-first")},
		{time: 200, digest: digest.FromString("rollback-overlap-second")},
		{time: 150, digest: digest.FromString("rollback-overlap-third")},
	} {
		now = manifest.time
		_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest: manifest.digest, MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content: []byte(`{}`), Tag: "latest",
		})
		require.NoError(t, err)
	}

	rows := getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 3)
	require.Equal(t, int64(100), rows[0].lifetimeStartMs)
	require.Equal(t, int64(200), rows[0].lifetimeEndMs.Int64)
	require.Equal(t, int64(200), rows[1].lifetimeStartMs)
	require.Equal(t, int64(200), rows[1].lifetimeEndMs.Int64)
	require.Equal(t, int64(200), rows[2].lifetimeStartMs)
	require.False(t, rows[2].lifetimeEndMs.Valid)
	assertTagIntervalsValid(t, store, repoID, "latest")

	activeDigest, err := store.GetTagDigest(ctx, repoID, "latest")
	require.NoError(t, err)
	require.Equal(t, digest.FromString("rollback-overlap-third"), activeDigest)

	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)

	now = 200
	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)
}

func TestListTags_RollbackDelete(t *testing.T) {
	const tagStart = int64(110_000)
	now := tagStart
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "rollback-delete"})
	require.NoError(t, err)

	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: digest.FromString("rollback-delete"), MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	})
	require.NoError(t, err)

	now--
	require.NoError(t, store.DeleteTag(ctx, repoID, "latest"))

	rows := getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 1)
	require.Equal(t, tagStart, rows[0].lifetimeStartMs)
	require.Equal(t, tagStart, rows[0].lifetimeEndMs.Int64)
	assertTagIntervalsValid(t, store, repoID, "latest")

	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Empty(t, tags)

	now = tagStart
	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Empty(t, tags)
}

func TestListTags_RollbackDeleteDoesNotResurrectHistory(t *testing.T) {
	now := int64(100)
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "rollback-delete-history"})
	require.NoError(t, err)

	for _, manifest := range []struct {
		time   int64
		digest digest.Digest
	}{
		{time: 100, digest: digest.FromString("rollback-delete-history-first")},
		{time: 200, digest: digest.FromString("rollback-delete-history-second")},
	} {
		now = manifest.time
		_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest: manifest.digest, MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content: []byte(`{}`), Tag: "latest",
		})
		require.NoError(t, err)
	}

	now = 150
	require.NoError(t, store.DeleteTag(ctx, repoID, "latest"))

	rows := getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 2)
	require.Equal(t, int64(100), rows[0].lifetimeStartMs)
	require.Equal(t, int64(200), rows[0].lifetimeEndMs.Int64)
	require.Equal(t, int64(200), rows[1].lifetimeStartMs)
	require.Equal(t, int64(200), rows[1].lifetimeEndMs.Int64)
	assertTagIntervalsValid(t, store, repoID, "latest")

	_, err = store.GetTagDigest(ctx, repoID, "latest")
	require.ErrorIs(t, err, oci.ErrNotExist)
	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Empty(t, tags)

	now = 200
	_, err = store.GetTagDigest(ctx, repoID, "latest")
	require.ErrorIs(t, err, oci.ErrNotExist)
	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Empty(t, tags)
}

func TestListTags_RollbackDeleteThenRecreateClampsToHistory(t *testing.T) {
	now := int64(100)
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "rollback-recreate"})
	require.NoError(t, err)

	for _, manifest := range []struct {
		time   int64
		digest digest.Digest
	}{
		{time: 100, digest: digest.FromString("rollback-recreate-history")},
		{time: 200, digest: digest.FromString("rollback-recreate-deleted")},
	} {
		now = manifest.time
		_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest: manifest.digest, MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content: []byte(`{}`), Tag: "latest",
		})
		require.NoError(t, err)
	}

	now = 150
	require.NoError(t, store.DeleteTag(ctx, repoID, "latest"))
	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Empty(t, tags)

	recreatedDigest := digest.FromString("rollback-recreate-active")
	recreatedRecord := oci.ManifestRecord{
		Digest: recreatedDigest, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "latest",
	}
	_, err = store.PutManifest(ctx, repoID, recreatedRecord)
	require.NoError(t, err)

	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)
	activeDigest, err := store.GetTagDigest(ctx, repoID, "latest")
	require.NoError(t, err)
	require.Equal(t, recreatedDigest, activeDigest)

	rows := getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 3)
	require.Equal(t, int64(100), rows[0].lifetimeStartMs)
	require.Equal(t, int64(200), rows[0].lifetimeEndMs.Int64)
	require.Equal(t, int64(200), rows[1].lifetimeStartMs)
	require.Equal(t, int64(200), rows[1].lifetimeEndMs.Int64)
	require.Equal(t, int64(200), rows[2].lifetimeStartMs)
	require.False(t, rows[2].lifetimeEndMs.Valid)
	activeTagID := rows[2].id
	assertTagIntervalsValid(t, store, repoID, "latest")

	_, err = store.PutManifest(ctx, repoID, recreatedRecord)
	require.NoError(t, err)
	rows = getTagRows(t, store, repoID, "latest")
	require.Len(t, rows, 3)
	require.Equal(t, activeTagID, rows[2].id)

	now = 200
	tags, err = store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.Equal(t, []string{"latest"}, tags)
	activeDigest, err = store.GetTagDigest(ctx, repoID, "latest")
	require.NoError(t, err)
	require.Equal(t, recreatedDigest, activeDigest)
}

func TestListTags_UsesCurrentLifetimeInterval(t *testing.T) {
	const futureStart = int64(120_000)
	now := futureStart
	store, cleanup := testStore(t, metastore.WithNowFunc(func() int64 { return now }))
	defer cleanup()
	ctx := t.Context()

	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "intervals"})
	require.NoError(t, err)

	firstDigest := digest.FromString("interval-first")
	firstManifestID, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: firstDigest, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "future-active",
	})
	require.NoError(t, err)

	now--
	secondDigest := digest.FromString("interval-second")
	_, err = store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest: secondDigest, MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content: []byte(`{}`), Tag: "future-active",
	})
	require.NoError(t, err)

	_, err = store.DB().ExecContext(ctx, `
		INSERT INTO tag (
			name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
		)
		SELECT 'current-finite', ?, ?, ?, ?, id
		FROM tagkind
		WHERE name = 'tag'`, repoID, firstManifestID, now-1, now+1)
	require.NoError(t, err)
	_, err = store.DB().ExecContext(ctx, `
		INSERT INTO tag (
			name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
		)
		SELECT 'future-finite', ?, ?, ?, ?, id
		FROM tagkind
		WHERE name = 'tag'`, repoID, firstManifestID, now+1, now+2)
	require.NoError(t, err)
	_, err = store.DB().ExecContext(ctx, `
		INSERT INTO tag (
			name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id
		)
		SELECT 'expired-finite', ?, ?, ?, ?, id
		FROM tagkind
		WHERE name = 'tag'`, repoID, firstManifestID, now-2, now-1)
	require.NoError(t, err)

	currentRows := getTagRows(t, store, repoID, "current-finite")
	require.Len(t, currentRows, 1)
	require.LessOrEqual(t, currentRows[0].lifetimeStartMs, now)
	require.Greater(t, currentRows[0].lifetimeEndMs.Int64, now)
	futureRows := getTagRows(t, store, repoID, "future-finite")
	require.Len(t, futureRows, 1)
	require.Greater(t, futureRows[0].lifetimeStartMs, now)
	require.Greater(t, futureRows[0].lifetimeEndMs.Int64, futureRows[0].lifetimeStartMs)
	expiredRows := getTagRows(t, store, repoID, "expired-finite")
	require.Len(t, expiredRows, 1)
	require.LessOrEqual(t, expiredRows[0].lifetimeEndMs.Int64, now)

	rows := getTagRows(t, store, repoID, "future-active")
	require.Len(t, rows, 2)
	require.Equal(t, futureStart, rows[0].lifetimeStartMs)
	require.Equal(t, futureStart, rows[0].lifetimeEndMs.Int64)
	require.Equal(t, futureStart, rows[1].lifetimeStartMs)
	require.False(t, rows[1].lifetimeEndMs.Valid)

	currentDigest, err := store.GetTagDigest(ctx, repoID, "current-finite")
	require.NoError(t, err)
	require.Equal(t, firstDigest, currentDigest)
	_, err = store.GetTagDigest(ctx, repoID, "future-finite")
	require.ErrorIs(t, err, oci.ErrNotExist)
	_, err = store.GetTagDigest(ctx, repoID, "expired-finite")
	require.ErrorIs(t, err, oci.ErrNotExist)
	activeDigest, err := store.GetTagDigest(ctx, repoID, "future-active")
	require.NoError(t, err)
	require.Equal(t, secondDigest, activeDigest)

	tags, err := store.ListTags(ctx, repoID)
	require.NoError(t, err)
	require.ElementsMatch(t, []string{"current-finite", "future-active"}, tags)
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

func TestDeleteUploadedBlobRemovesOnlyRepoScopedUploadLink(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	ctx := context.Background()

	repoOne, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "one"})
	if err != nil {
		t.Fatal(err)
	}
	repoTwo, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "ns", Name: "two"})
	if err != nil {
		t.Fatal(err)
	}
	dgst := digest.FromString("uploaded-blob")
	if _, err := store.PutBlob(ctx, oci.BlobRecord{Digest: dgst, Size: 100}); err != nil {
		t.Fatal(err)
	}
	if err := store.PutUploadedBlob(ctx, repoOne, dgst); err != nil {
		t.Fatal(err)
	}
	if err := store.PutUploadedBlob(ctx, repoTwo, dgst); err != nil {
		t.Fatal(err)
	}

	rows, err := store.DeleteUploadedBlob(ctx, repoOne, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if rows != 1 {
		t.Fatalf("DeleteUploadedBlob rows = %d, want 1", rows)
	}

	linked, err := store.BlobLinkedToRepo(ctx, repoOne, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if linked {
		t.Fatal("BlobLinkedToRepo = true for deleted repo upload link")
	}

	linked, err = store.BlobLinkedToRepo(ctx, repoTwo, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !linked {
		t.Fatal("BlobLinkedToRepo = false for untouched repo upload link")
	}

	exists, err := store.BlobExists(ctx, dgst)
	if err != nil {
		t.Fatal(err)
	}
	if !exists {
		t.Fatal("BlobExists = false after deleting one repo upload link")
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
