package gc

import "context"

// Store abstracts the metadata operations that GC needs. The collector
// calls these methods without knowing which database is behind them.
// Each mutation method handles its own FK cleanup and transactions
// internally so the collector stays pure orchestration logic.
type Store interface {
	// CleanExpiredUploadedBlobs removes uploadedblob rows past their expiry.
	CleanExpiredUploadedBlobs(ctx context.Context) error

	// FindExpiredTags returns tags whose soft-delete grace period has elapsed.
	FindExpiredTags(ctx context.Context) ([]ExpiredTag, error)

	// DeleteExpiredTags deletes the given tags and their dependent rows
	// (e.g., tag notifications) in a single transaction.
	DeleteExpiredTags(ctx context.Context, ids []int64) error

	// FindOrphanedManifests returns manifests with no tags, no manifestchild
	// parents, and no subject referrers. Checks are global, not repo-scoped.
	FindOrphanedManifests(ctx context.Context) ([]OrphanedManifest, error)

	// DeleteManifest removes a manifest and all dependent rows (labels,
	// children, blobs, security status, tags) in a single transaction.
	DeleteManifest(ctx context.Context, id int64) error

	// FindOrphanedBlobs returns blobs not referenced by any manifest or
	// active uploadedblob.
	FindOrphanedBlobs(ctx context.Context) ([]OrphanedBlob, error)

	// DeleteBlobRecords removes blob metadata and dependent rows (placements,
	// signatures) in a single transaction. Returns only the checksums whose
	// storage files are safe to delete (no other imagestorage row shares them).
	DeleteBlobRecords(ctx context.Context, ids []int64) (safeChecksums []string, err error)
}

// ExpiredTag is a tag whose grace period has elapsed.
type ExpiredTag struct {
	ID           int64
	Name         string
	RepositoryID int64
}

// OrphanedManifest is a manifest with no references.
type OrphanedManifest struct {
	ID           int64
	RepositoryID int64
	Digest       string
}

// OrphanedBlob is a blob with no manifest or upload protection.
type OrphanedBlob struct {
	ID              int64
	ContentChecksum string
	ImageSize       int64
}
