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
	if now := time.Now().UnixMilli(); gotEnd > now {
		t.Fatalf("lifetime_end_ms = %d, ahead of wall clock %d", gotEnd, now)
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

	t.Run("stops on cancellation after clock rollback", func(t *testing.T) {
		const rollbackTag = "clock-rollback"
		futureEnd := time.Now().Add(time.Hour).UnixMilli()
		for _, lifetimeEnd := range []any{futureEnd, nil} {
			_, err := db.ExecContext(ctx, `
				INSERT INTO tag (name, repository_id, manifest_id, lifetime_start_ms, lifetime_end_ms, tag_kind_id)
				VALUES (?, ?, ?, ?, ?, ?)`,
				rollbackTag, repoID, manifestID, futureEnd, lifetimeEnd, store.tagKindTag)
			if err != nil {
				t.Fatal(err)
			}
		}

		waitTx, err := db.BeginTx(ctx, nil)
		if err != nil {
			t.Fatal(err)
		}
		waitCtx, cancel := context.WithTimeout(ctx, 50*time.Millisecond)
		defer cancel()
		_, err = expireActiveTag(waitCtx, daldb.New(waitTx), repoID, rollbackTag, futureEnd)
		_ = waitTx.Rollback()
		if !errors.Is(err, context.DeadlineExceeded) {
			t.Fatalf("expireActiveTag error = %v, want context deadline exceeded", err)
		}
	})
}
