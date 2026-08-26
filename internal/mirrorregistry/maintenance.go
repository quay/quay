package mirrorregistry

import (
	"context"
	"log/slog"

	"github.com/quay/quay/internal/gc"
)

func startGC(ctx context.Context, collector gc.Collector) chan struct{} {
	worker := gc.NewWorker(collector, gc.DefaultConfig(), slog.Default())
	done := make(chan struct{})
	go func() {
		defer close(done)
		_ = worker.Run(ctx)
	}()
	return done
}
