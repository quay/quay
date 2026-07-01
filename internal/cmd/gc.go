package cmd

import (
	"context"
	"flag"
	"fmt"
	"log/slog"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/dal/metastore"
	"github.com/quay/quay/internal/gc"
	"github.com/quay/quay/internal/oci/storage/local"
)

func newGCCmd() *Command {
	fs := flag.NewFlagSet("gc", flag.ContinueOnError)
	configPath := fs.String("config", "", "path to config.yaml (optional, overrides flags)")
	dataDir := fs.String("data-dir", ".", "root directory for DB, storage, certs")
	hostname := fs.String("hostname", "localhost", "server hostname")
	dryRun := fs.Bool("dry-run", false, "report what would be deleted without deleting")

	return &Command{
		Name:     "gc",
		Synopsis: "Run garbage collection (one-shot)",
		Flags:    fs,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			return runGC(ctx, *configPath, *dataDir, *hostname, *dryRun)
		},
	}
}

func runGC(ctx context.Context, configPath, dataDir, hostname string, dryRun bool) int {
	resolved, err := config.Resolve(configPath, dataDir, hostname)
	if err != nil {
		slog.Error("config error", "err", err)
		return 1
	}

	db, err := dbcore.Setup(ctx, resolved.DBPath)
	if err != nil {
		slog.Error("database setup error", "err", err)
		return 1
	}
	defer func() { _ = db.Close() }()

	store, err := metastore.NewSQLiteStore(ctx, db)
	if err != nil {
		slog.Error("metastore setup error", "err", err)
		return 1
	}

	blobs, err := local.New(resolved.StoragePath)
	if err != nil {
		slog.Error("blob store setup error", "err", err)
		return 1
	}

	collector := gc.NewSQLiteCollector(db, store, blobs, slog.Default())

	var stats gc.Stats
	if dryRun {
		slog.Info("gc dry-run: reporting what would be deleted")
		stats, err = collector.CollectDryRun(ctx)
	} else {
		stats, err = collector.Collect(ctx)
	}
	if err != nil {
		slog.Error("gc failed", "err", err)
		return 1
	}

	mode := "deleted"
	if dryRun {
		mode = "would delete"
	}
	fmt.Printf("GC complete (%s): %d tags, %d manifests, %d blobs, %d stale uploads, %d bytes reclaimed\n",
		mode, stats.TagsExpired, stats.ManifestsDeleted, stats.BlobsDeleted, stats.StaleUploadsRemoved, stats.BytesReclaimed)
	return 0
}
