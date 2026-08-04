package quay

import (
	"context"
	"log/slog"

	"github.com/quay/quay/internal/gc"
	"github.com/quay/quay/internal/oci"
)

func startGC(ctx context.Context, store gc.Store, blobs oci.BlobStore, blobLocks oci.BlobLocker) chan struct{} {
	collector := gc.NewCollector(store, blobs, blobLocks, slog.Default())
	worker := gc.NewWorker(collector, gc.DefaultConfig(), slog.Default())
	done := make(chan struct{})
	go func() {
		defer close(done)
		_ = worker.Run(ctx)
	}()
	return done
}
