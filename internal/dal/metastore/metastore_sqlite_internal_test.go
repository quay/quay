package metastore

import (
	"context"
	"errors"
	"path/filepath"
	"testing"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/oci"
)

func TestExpireActiveTagWaitsForUnusedLifetimeEnd(t *testing.T) {
	ctx := t.Context()
	db, err := dbcore.Setup(ctx, filepath.Join(t.TempDir(), "quay.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = db.Close() })

	store, err := NewSQLiteStore(ctx, db)
	if err != nil {
		t.Fatal(err)
	}
	repoID, err := store.EnsureRepository(ctx, oci.RepositoryName{Namespace: "library", Name: "nginx"})
	if err != nil {
		t.Fatal(err)
	}
	manifestID, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
		Digest:    digest.FromString("manifest-v1"),
		MediaType: "application/vnd.oci.image.manifest.v1+json",
		Content:   []byte(`{"schemaVersion":2}`),
	})
	if err != nil {
		t.Fatal(err)
	}

	seedOccupiedActiveStart := func(t *testing.T, tag string) (int64, int64) {
		t.Helper()
		futureStart := time.Now().Add(time.Hour).UnixMilli()
		_, err := db.ExecContext(ctx, `
			INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
			VALUES (?, ?, ?, ?, ?, ?)`,
			tag, repoID, manifestID, futureStart-1, futureStart, store.tagKindTag)
		if err != nil {
			t.Fatal(err)
		}
		result, err := db.ExecContext(ctx, `
			INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
			VALUES (?, ?, ?, ?, NULL, ?)`,
			tag, repoID, manifestID, futureStart, store.tagKindTag)
		if err != nil {
			t.Fatal(err)
		}
		activeTagID, err := result.LastInsertId()
		if err != nil {
			t.Fatal(err)
		}
		return futureStart, activeTagID
	}

	assertCurrentTag := func(t *testing.T, tag string, expectedDigest digest.Digest, expiredTagID, previousStart int64) {
		t.Helper()
		gotDigest, err := store.GetTagDigest(ctx, repoID, tag)
		if err != nil {
			t.Fatal(err)
		}
		if gotDigest != expectedDigest {
			t.Fatalf("tag digest = %s, want %s", gotDigest, expectedDigest)
		}

		tags, err := store.ListTags(ctx, repoID)
		if err != nil {
			t.Fatal(err)
		}
		var matches int
		for _, listedTag := range tags {
			if listedTag == tag {
				matches++
			}
		}
		if matches != 1 {
			t.Fatalf("ListTags returned %d entries for %q, want 1: %v", matches, tag, tags)
		}

		var expiredEnd, activeStart int64
		if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, expiredTagID).Scan(&expiredEnd); err != nil {
			t.Fatal(err)
		}
		if err := db.QueryRowContext(ctx, `
			SELECT lifetime_start_ms
			FROM tag
			WHERE repository_id = ? AND name = ? AND lifetime_end_ms IS NULL`,
			repoID, tag).Scan(&activeStart); err != nil {
			t.Fatal(err)
		}
		if expiredEnd != activeStart {
			t.Fatalf("expired lifetime_end_ms = %d, replacement lifetime_start_ms = %d", expiredEnd, activeStart)
		}
		if expiredEnd <= previousStart {
			t.Fatalf("transition = %d, want value after occupied active start %d", expiredEnd, previousStart)
		}
	}

	const tag = "v1"
	requestedEnd := time.Now().UnixMilli()
	_, err = db.ExecContext(ctx, `
		INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
		VALUES (?, ?, ?, ?, ?, ?)`,
		tag, repoID, manifestID, requestedEnd-1, requestedEnd, store.tagKindTag)
	if err != nil {
		t.Fatal(err)
	}
	result, err := db.ExecContext(ctx, `
		INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
		VALUES (?, ?, ?, ?, NULL, ?)`,
		tag, repoID, manifestID, requestedEnd, store.tagKindTag)
	if err != nil {
		t.Fatal(err)
	}
	activeTagID, err := result.LastInsertId()
	if err != nil {
		t.Fatal(err)
	}

	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback() //nolint:errcheck // rollback after commit is a no-op
	transitionMs, err := expireActiveTag(ctx, daldb.New(tx), repoID, tag, requestedEnd)
	if err != nil {
		t.Fatal(err)
	}
	if err := tx.Commit(); err != nil {
		t.Fatal(err)
	}

	var gotEnd int64
	if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, activeTagID).Scan(&gotEnd); err != nil {
		t.Fatal(err)
	}
	if gotEnd != transitionMs {
		t.Fatalf("lifetime_end_ms = %d, returned transition = %d", gotEnd, transitionMs)
	}
	if gotEnd <= requestedEnd {
		t.Fatalf("lifetime_end_ms = %d, want value after occupied millisecond %d", gotEnd, requestedEnd)
	}

	var total, distinct int
	if err := db.QueryRowContext(ctx, `
		SELECT COUNT(*), COUNT(DISTINCT lifetime_end_ms)
		FROM tag
		WHERE repository_id = ? AND name = ?`, repoID, tag).Scan(&total, &distinct); err != nil {
		t.Fatal(err)
	}
	if total != 2 || distinct != total {
		t.Fatalf("tag history rows = %d, distinct lifetime ends = %d", total, distinct)
	}

	t.Run("never expires before active lifetime start after clock rollback", func(t *testing.T) {
		const rollbackTag = "active-start-after-clock"
		futureStart := time.Now().Add(time.Hour).UnixMilli()
		result, err := db.ExecContext(ctx, `
			INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
			VALUES (?, ?, ?, ?, NULL, ?)`,
			rollbackTag, repoID, manifestID, futureStart, store.tagKindTag)
		if err != nil {
			t.Fatal(err)
		}
		tagID, err := result.LastInsertId()
		if err != nil {
			t.Fatal(err)
		}

		rollbackTx, err := db.BeginTx(ctx, nil)
		if err != nil {
			t.Fatal(err)
		}
		defer rollbackTx.Rollback() //nolint:errcheck // rollback after commit is a no-op
		transitionMs, err := expireActiveTag(
			ctx,
			daldb.New(rollbackTx),
			repoID,
			rollbackTag,
			time.Now().UnixMilli(),
		)
		if err != nil {
			t.Fatal(err)
		}
		if err := rollbackTx.Commit(); err != nil {
			t.Fatal(err)
		}

		var gotEnd int64
		if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, tagID).Scan(&gotEnd); err != nil {
			t.Fatal(err)
		}
		if transitionMs != futureStart || gotEnd != futureStart {
			t.Fatalf("transition = %d, lifetime_end_ms = %d, want active lifetime_start_ms %d", transitionMs, gotEnd, futureStart)
		}
	})

	t.Run("reselects a stale candidate after clock rollback", func(t *testing.T) {
		const rollbackTag = "stale-candidate-after-clock"
		activeStart := time.Now().UnixMilli() - 1
		staleCandidate := time.Now().Add(time.Hour).UnixMilli()
		_, err := db.ExecContext(ctx, `
			INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
			VALUES (?, ?, ?, ?, ?, ?)`,
			rollbackTag, repoID, manifestID, activeStart-1, staleCandidate, store.tagKindTag)
		if err != nil {
			t.Fatal(err)
		}
		result, err := db.ExecContext(ctx, `
			INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
			VALUES (?, ?, ?, ?, NULL, ?)`,
			rollbackTag, repoID, manifestID, activeStart, store.tagKindTag)
		if err != nil {
			t.Fatal(err)
		}
		tagID, err := result.LastInsertId()
		if err != nil {
			t.Fatal(err)
		}

		rollbackTx, err := db.BeginTx(ctx, nil)
		if err != nil {
			t.Fatal(err)
		}
		defer rollbackTx.Rollback() //nolint:errcheck // rollback after commit is a no-op
		waitCtx, cancel := context.WithTimeout(ctx, 500*time.Millisecond)
		defer cancel()
		transitionMs, err := expireActiveTag(waitCtx, daldb.New(rollbackTx), repoID, rollbackTag, staleCandidate)
		if err != nil {
			t.Fatal(err)
		}
		if err := rollbackTx.Commit(); err != nil {
			t.Fatal(err)
		}

		var gotEnd int64
		if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, tagID).Scan(&gotEnd); err != nil {
			t.Fatal(err)
		}
		if transitionMs != gotEnd {
			t.Fatalf("transition = %d, lifetime_end_ms = %d", transitionMs, gotEnd)
		}
		if transitionMs < activeStart {
			t.Fatalf("transition = %d, before active lifetime_start_ms %d", transitionMs, activeStart)
		}
		if transitionMs >= staleCandidate {
			t.Fatalf("transition = %d, want reselected value before stale candidate %d", transitionMs, staleCandidate)
		}
	})

	t.Run("PutTag replaces a rollback generation consistently", func(t *testing.T) {
		const rollbackTag = "put-tag-after-rollback"
		newDigest := digest.FromString("manifest-put-tag")
		if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    newDigest,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
		}); err != nil {
			t.Fatal(err)
		}
		futureStart, activeTagID := seedOccupiedActiveStart(t, rollbackTag)

		if _, err := store.PutTag(ctx, repoID, oci.TagRecord{Name: rollbackTag, Digest: newDigest}); err != nil {
			t.Fatal(err)
		}
		assertCurrentTag(t, rollbackTag, newDigest, activeTagID, futureStart)
	})

	t.Run("PutManifest replaces a rollback generation consistently", func(t *testing.T) {
		const rollbackTag = "put-manifest-after-rollback"
		newDigest := digest.FromString("manifest-put-manifest")
		futureStart, activeTagID := seedOccupiedActiveStart(t, rollbackTag)

		if _, err := store.PutManifest(ctx, repoID, oci.ManifestRecord{
			Digest:    newDigest,
			MediaType: "application/vnd.oci.image.manifest.v1+json",
			Content:   []byte(`{"schemaVersion":2}`),
			Tag:       rollbackTag,
		}); err != nil {
			t.Fatal(err)
		}
		assertCurrentTag(t, rollbackTag, newDigest, activeTagID, futureStart)
	})

	t.Run("deletes when clock rollback leaves active start occupied", func(t *testing.T) {
		const rollbackTag = "occupied-active-start"
		futureStart, activeTagID := seedOccupiedActiveStart(t, rollbackTag)

		deleteCtx, cancel := context.WithCancel(context.Background())
		defer cancel()
		if _, hasDeadline := deleteCtx.Deadline(); hasDeadline {
			t.Fatal("DeleteTag context unexpectedly has a deadline")
		}
		done := make(chan error, 1)
		go func() {
			done <- store.DeleteTag(deleteCtx, repoID, rollbackTag)
		}()
		select {
		case err := <-done:
			if err != nil {
				t.Fatal(err)
			}
		case <-time.After(time.Second):
			cancel()
			err := <-done
			t.Fatalf("DeleteTag waited for the rolled-back clock; after cancellation it returned %v", err)
		}

		var gotEnd int64
		if err := db.QueryRowContext(ctx, `SELECT lifetime_end_ms FROM tag WHERE id = ?`, activeTagID).Scan(&gotEnd); err != nil {
			t.Fatal(err)
		}
		if gotEnd <= futureStart {
			t.Fatalf("lifetime_end_ms = %d, want value after occupied active start %d", gotEnd, futureStart)
		}

		if _, err := store.GetTagDigest(ctx, repoID, rollbackTag); !errors.Is(err, oci.ErrNotExist) {
			t.Fatalf("GetTagDigest error = %v, want %v", err, oci.ErrNotExist)
		}
		tags, err := store.ListTags(ctx, repoID)
		if err != nil {
			t.Fatal(err)
		}
		for _, listedTag := range tags {
			if listedTag == rollbackTag {
				t.Fatalf("ListTags returned deleted tag %q: %v", rollbackTag, tags)
			}
		}

		var total, distinct int
		if err := db.QueryRowContext(ctx, `
			SELECT COUNT(*), COUNT(DISTINCT lifetime_end_ms)
			FROM tag
			WHERE repository_id = ? AND name = ?`, repoID, rollbackTag).Scan(&total, &distinct); err != nil {
			t.Fatal(err)
		}
		if total != 2 || distinct != total {
			t.Fatalf("tag history rows = %d, distinct lifetime ends = %d", total, distinct)
		}
	})
}
