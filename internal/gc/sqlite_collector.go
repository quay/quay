package gc

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	"github.com/opencontainers/go-digest"

	"github.com/quay/quay/internal/oci"
)

const staleUploadThreshold = 48 * time.Hour

// Collector runs the four-phase GC algorithm. It depends on a Store for
// metadata operations and a BlobStore for storage file deletion. It has no
// knowledge of SQL, transactions, or FK relationships — the Store handles
// all of that.
type collector struct {
	store Store
	blobs oci.BlobStore
	log   *slog.Logger
}

// NewCollector creates a Collector from a metadata Store and a BlobStore.
func NewCollector(store Store, blobs oci.BlobStore, log *slog.Logger) Collector {
	return &collector{store: store, blobs: blobs, log: log}
}

// Collect runs a full GC cycle.
func (c *collector) Collect(ctx context.Context) (Stats, error) {
	var total Stats

	// Phase 0: Clean expired uploadedblob markers.
	if err := c.store.CleanExpiredUploadedBlobs(ctx); err != nil {
		return total, fmt.Errorf("gc: clean expired uploaded blobs: %w", err)
	}

	// Phase 1: Expire tags past their grace period.
	expired, err := c.expireTags(ctx)
	if err != nil {
		return total, fmt.Errorf("gc: expire tags: %w", err)
	}
	total.TagsExpired = expired

	// Phase 2: Collect orphaned manifests (globally, iterative for cascades).
	manifests, err := c.collectManifests(ctx)
	if err != nil {
		return total, fmt.Errorf("gc: collect manifests: %w", err)
	}
	total.ManifestsDeleted = manifests

	// Phase 3: Collect orphaned blobs and delete storage files.
	blobCount, blobBytes, err := c.collectBlobs(ctx)
	if err != nil {
		return total, fmt.Errorf("gc: collect blobs: %w", err)
	}
	total.BlobsDeleted = blobCount
	total.BytesReclaimed = blobBytes

	// Phase 4: Clean stale uploads (abandoned uploads older than 48 hours).
	stale, err := c.blobs.CleanStaleUploads(ctx, staleUploadThreshold)
	if err != nil {
		return total, fmt.Errorf("gc: clean stale uploads: %w", err)
	}
	if stale.Removed > 0 {
		total.StaleUploadsRemoved = stale.Removed
		total.BytesReclaimed += stale.BytesFreed
		c.log.Info("gc: cleaned stale uploads", "removed", stale.Removed, "bytes_freed", stale.BytesFreed)
	}

	return total, nil
}

func (c *collector) expireTags(ctx context.Context) (int, error) {
	tags, err := c.store.FindExpiredTags(ctx)
	if err != nil {
		return 0, err
	}
	if len(tags) == 0 {
		return 0, nil
	}

	ids := make([]int64, len(tags))
	for i, t := range tags {
		ids[i] = t.ID
	}
	if err := c.store.DeleteExpiredTags(ctx, ids); err != nil {
		return 0, err
	}
	for _, tag := range tags {
		c.log.Debug("gc: expired tag", "tag", tag.Name, "repo_id", tag.RepositoryID)
	}
	return len(tags), nil
}

// collectManifests iteratively finds and deletes orphaned manifests.
// Iterative because deleting a manifest list orphans its children,
// which need another pass to detect.
func (c *collector) collectManifests(ctx context.Context) (int, error) {
	const maxIterations = 100
	total := 0

	for i := 0; i < maxIterations; i++ {
		orphans, err := c.store.FindOrphanedManifests(ctx)
		if err != nil {
			return total, err
		}
		if len(orphans) == 0 {
			break
		}

		for _, m := range orphans {
			if err := c.store.DeleteManifest(ctx, m.ID); err != nil {
				return total, fmt.Errorf("delete manifest %d (%s): %w", m.ID, m.Digest, err)
			}
			total++
			c.log.Debug("gc: deleted manifest", "digest", m.Digest, "repo_id", m.RepositoryID)
		}

		if i == maxIterations-1 {
			c.log.Warn("gc: manifest collection hit iteration limit", "limit", maxIterations, "deleted_so_far", total)
		}
	}
	return total, nil
}

// collectBlobs finds orphaned blobs, deletes their DB records (with FK
// cleanup), then deletes only the storage files that are safe to remove.
func (c *collector) collectBlobs(ctx context.Context) (deleted int, bytesFreed int64, err error) {
	orphans, err := c.store.FindOrphanedBlobs(ctx)
	if err != nil {
		return 0, 0, err
	}
	if len(orphans) == 0 {
		return 0, 0, nil
	}

	var totalBytes int64
	ids := make([]int64, len(orphans))
	for i, b := range orphans {
		ids[i] = b.ID
		totalBytes += b.ImageSize
	}

	// Delete DB records and get back only checksums safe to delete from storage.
	safeChecksums, err := c.store.DeleteBlobRecords(ctx, ids)
	if err != nil {
		return 0, 0, err
	}

	// Delete storage files. Failures are logged but not fatal — DB records
	// are already gone so the blobs won't be served.
	for _, checksum := range safeChecksums {
		dgst, err := digest.Parse(checksum)
		if err != nil {
			c.log.Warn("gc: invalid digest, skipping storage delete", "checksum", checksum, "err", err)
			continue
		}
		if err := c.blobs.Delete(ctx, dgst); err != nil {
			c.log.Warn("gc: storage delete failed", "digest", dgst, "err", err)
		}
	}

	return len(orphans), totalBytes, nil
}
