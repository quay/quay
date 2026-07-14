// Package gc implements garbage collection for the registry.
package gc

import (
	"context"
	"time"
)

// Collector defines the garbage collection strategy. Implementations handle
// finding and deleting expired tags, orphaned manifests, and orphaned blobs.
// The interface is backend-agnostic — swap the implementation to change the
// storage engine (e.g., SQLite → PostgreSQL) without touching the worker.
type Collector interface {
	// Collect runs a full GC cycle: clean expired upload markers, expire
	// tags past their grace period, collect orphaned manifests, then
	// collect orphaned blobs and delete their storage files.
	Collect(ctx context.Context) (Stats, error)
}

// Stats summarizes a single GC cycle.
type Stats struct {
	TagsExpired      int
	ManifestsDeleted int
	// BlobsDeleted counts imagestorage metadata rows actually deleted.
	BlobsDeleted        int
	StaleUploadsRemoved int
	// BytesReclaimed counts successful physical blob and stale-upload deletion.
	BytesReclaimed int64
}

// Config tunes the GC worker behavior.
type Config struct {
	// Interval between GC cycles. Default: 30s.
	Interval time.Duration
}

// DefaultConfig returns production defaults.
func DefaultConfig() Config {
	return Config{
		Interval: 30 * time.Second,
	}
}
