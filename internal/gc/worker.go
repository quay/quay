package gc

import (
	"context"
	"fmt"
	"log/slog"
	"time"
)

// Worker runs GC cycles on a timer in the background.
type Worker struct {
	collector Collector
	interval  time.Duration
	log       *slog.Logger
}

// NewWorker creates a background GC worker.
func NewWorker(collector Collector, cfg Config, log *slog.Logger) *Worker {
	interval := cfg.Interval
	if interval <= 0 {
		interval = DefaultConfig().Interval
	}
	return &Worker{
		collector: collector,
		interval:  interval,
		log:       log,
	}
}

// Run blocks until ctx is canceled, running a GC cycle every interval.
func (w *Worker) Run(ctx context.Context) error {
	w.log.Info("gc worker started", "interval", w.interval)

	ticker := time.NewTicker(w.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			w.log.Info("gc worker stopped")
			return ctx.Err()
		case <-ticker.C:
			stats, err := w.safeCollect(ctx)
			if err != nil {
				w.log.Error("gc cycle failed", "err", err)
				continue
			}
			if stats.TagsExpired+stats.ManifestsDeleted+stats.BlobsDeleted+stats.StaleUploadsRemoved > 0 {
				w.log.Info("gc cycle complete",
					"tags_expired", stats.TagsExpired,
					"manifests_deleted", stats.ManifestsDeleted,
					"blobs_deleted", stats.BlobsDeleted,
					"stale_uploads_removed", stats.StaleUploadsRemoved,
					"bytes_reclaimed", stats.BytesReclaimed,
				)
			}
		}
	}
}

func (w *Worker) safeCollect(ctx context.Context) (stats Stats, err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("gc cycle panicked: %v", r)
		}
	}()
	return w.collector.Collect(ctx)
}
