package gc

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/dal/daldb"
	"github.com/quay/quay/internal/oci"
)

const staleUploadThreshold = 48 * time.Hour

var nullInt64 = func(v int64) sql.NullInt64 { return sql.NullInt64{Int64: v, Valid: true} }

// SQLiteCollector implements Collector using SQLite and a BlobStore.
type SQLiteCollector struct {
	db    *sql.DB
	store oci.MetadataStore
	blobs oci.BlobStore
	log   *slog.Logger
}

// NewSQLiteCollector creates a collector that uses SQLite transactions for
// metadata operations and the BlobStore for storage file deletion.
func NewSQLiteCollector(db *sql.DB, store oci.MetadataStore, blobs oci.BlobStore, log *slog.Logger) *SQLiteCollector {
	return &SQLiteCollector{db: db, store: store, blobs: blobs, log: log}
}

func (c *SQLiteCollector) Collect(ctx context.Context) (Stats, error) {
	return c.collect(ctx, false)
}

func (c *SQLiteCollector) CollectDryRun(ctx context.Context) (Stats, error) {
	return c.collect(ctx, true)
}

func (c *SQLiteCollector) collect(ctx context.Context, dryRun bool) (Stats, error) {
	var total Stats

	// Phase 0: Clean expired uploadedblob markers.
	if !dryRun {
		if err := c.store.CleanExpiredUploadedBlobs(ctx); err != nil {
			return total, fmt.Errorf("gc: clean expired uploaded blobs: %w", err)
		}
	}

	// Phase 1: Expire tags past their grace period.
	expired, err := c.expireTags(ctx, dryRun)
	if err != nil {
		return total, fmt.Errorf("gc: expire tags: %w", err)
	}
	total.TagsExpired = expired

	// Phase 2: Collect orphaned manifests (globally).
	manifests, err := c.collectManifests(ctx, dryRun)
	if err != nil {
		return total, fmt.Errorf("gc: collect manifests: %w", err)
	}
	total.ManifestsDeleted = manifests

	// Phase 3: Collect orphaned blobs and delete storage files.
	blobs, bytes, err := c.collectBlobs(ctx, dryRun)
	if err != nil {
		return total, fmt.Errorf("gc: collect blobs: %w", err)
	}
	total.BlobsDeleted = blobs
	total.BytesReclaimed = bytes

	// Phase 4: Clean stale uploads (abandoned uploads older than 48 hours).
	if !dryRun {
		stale, err := c.blobs.CleanStaleUploads(ctx, staleUploadThreshold)
		if err != nil {
			return total, fmt.Errorf("gc: clean stale uploads: %w", err)
		}
		if stale.Removed > 0 {
			total.StaleUploadsRemoved = stale.Removed
			total.BytesReclaimed += stale.BytesFreed
			c.log.Info("gc: cleaned stale uploads", "removed", stale.Removed, "bytes_freed", stale.BytesFreed)
		}
	}

	return total, nil
}

// expireTags deletes tags whose lifetime_end_ms + namespace grace period
// has elapsed.
func (c *SQLiteCollector) expireTags(ctx context.Context, dryRun bool) (int, error) {
	q := daldb.New(c.db)
	tags, err := q.FindExpiredTags(ctx)
	if err != nil {
		return 0, err
	}
	if dryRun {
		return len(tags), nil
	}

	for _, tag := range tags {
		if err := q.DeleteExpiredTag(ctx, tag.ID); err != nil {
			return 0, fmt.Errorf("delete tag %d (%s): %w", tag.ID, tag.Name, err)
		}
		c.log.Debug("gc: expired tag", "tag", tag.Name, "repo_id", tag.RepositoryID)
	}
	return len(tags), nil
}

// collectManifests finds and deletes manifests with no live tags, no parent
// references (manifestchild), and no subject references (OCI referrers).
// Runs iteratively because deleting a manifest list may orphan its children.
func (c *SQLiteCollector) collectManifests(ctx context.Context, dryRun bool) (int, error) {
	q := daldb.New(c.db)
	total := 0

	for {
		orphans, err := q.FindOrphanedManifests(ctx)
		if err != nil {
			return total, err
		}
		if len(orphans) == 0 {
			break
		}
		if dryRun {
			total += len(orphans)
			break
		}

		for _, m := range orphans {
			if err := c.deleteManifest(ctx, q, m.ID); err != nil {
				return total, fmt.Errorf("delete manifest %d (%s): %w", m.ID, m.Digest, err)
			}
			total++
			c.log.Debug("gc: deleted manifest", "digest", m.Digest, "repo_id", m.RepositoryID)
		}
	}
	return total, nil
}

// deleteManifest removes a single manifest and all its dependent rows
// within a transaction.
func (c *SQLiteCollector) deleteManifest(ctx context.Context, q *daldb.Queries, manifestID int64) error {
	tx, err := c.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return err
	}
	defer func() { _ = tx.Rollback() }()

	tq := q.WithTx(tx)

	if err := tq.DeleteManifestLabels(ctx, manifestID); err != nil {
		return err
	}
	if err := tq.DeleteManifestChildren(ctx, daldb.DeleteManifestChildrenParams{
		ManifestID:      manifestID,
		ChildManifestID: manifestID,
	}); err != nil {
		return err
	}
	if err := tq.DeleteManifestBlobs(ctx, manifestID); err != nil {
		return err
	}
	if err := tq.DeleteManifestSecurityStatus(ctx, manifestID); err != nil {
		return err
	}
	if err := tq.DeleteTagsByManifest(ctx, nullInt64(manifestID)); err != nil {
		return err
	}
	if err := tq.DeleteManifest(ctx, manifestID); err != nil {
		return err
	}
	return tx.Commit()
}

// collectBlobs finds orphaned blobs (not in manifestblob, not protected by
// uploadedblob), deletes their DB rows, then deletes the storage files.
func (c *SQLiteCollector) collectBlobs(ctx context.Context, dryRun bool) (int, int64, error) {
	q := daldb.New(c.db)
	orphans, err := q.FindOrphanedBlobs(ctx)
	if err != nil {
		return 0, 0, err
	}
	if len(orphans) == 0 {
		return 0, 0, nil
	}

	var totalBytes int64
	for _, b := range orphans {
		if b.ImageSize.Valid {
			totalBytes += b.ImageSize.Int64
		}
	}

	if dryRun {
		return len(orphans), totalBytes, nil
	}

	// Delete DB rows first, then storage files. Orphaned files on disk
	// are harmless; orphaned DB rows pointing to missing files are not.
	for _, b := range orphans {
		if err := q.DeleteImageStorage(ctx, b.ID); err != nil {
			return 0, 0, fmt.Errorf("delete imagestorage %d: %w", b.ID, err)
		}
	}

	// Delete actual files from storage. Failures here are logged but
	// not fatal — the DB rows are already gone, so the blobs won't be
	// served. The files become storage-only orphans (harmless).
	deleted := 0
	for _, b := range orphans {
		if !b.ContentChecksum.Valid || b.ContentChecksum.String == "" {
			deleted++
			continue
		}
		dgst, err := digest.Parse(b.ContentChecksum.String)
		if err != nil {
			c.log.Warn("gc: invalid digest, skipping storage delete", "checksum", b.ContentChecksum.String, "err", err)
			deleted++
			continue
		}
		if err := c.blobs.Delete(ctx, dgst); err != nil {
			c.log.Warn("gc: storage delete failed", "digest", dgst, "err", err)
		}
		deleted++
	}

	return deleted, totalBytes, nil
}
