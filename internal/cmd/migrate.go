package cmd

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/quay/quay/internal/installer"
	"github.com/quay/quay/internal/migrate"
	"github.com/quay/quay/internal/system"
)

func newMigrateCmd() *Command {
	fs := flag.NewFlagSet("migrate", flag.ContinueOnError)
	dataDir := fs.String("data-dir", "/var/lib/quay", "target directory for new installation")
	hostname := fs.String("hostname", "", "server hostname (auto-detected from old config)")
	image := fs.String("image", installer.DefaultImage, "container image reference")
	imageArchive := fs.String("image-archive", "", "path to container image tar (auto-detected)")

	sourceRoot := fs.String("source-root", "", "old quay-install directory")
	sourceDB := fs.String("source-db", "", "old SQLite database file path")
	sourceStorage := fs.String("source-storage", "", "old blob storage path")
	sourceCerts := fs.String("source-certs", "", "old TLS cert directory")

	dryRun := fs.Bool("dry-run", false, "show migration plan without making changes")
	cleanup := fs.Bool("cleanup", false, "remove old OMR after successful migration")
	skipVerify := fs.Bool("skip-verify", false, "skip post-migration verification")
	skipInstall := fs.Bool("skip-install", false, "only migrate data, do not deploy Quadlet service")

	return &Command{
		Name:     "migrate",
		Synopsis: "Migrate from mirror-registry (OMR) to this binary",
		Flags:    fs,
		Run: func(ctx context.Context, _ *Command, _ []string) int {
			return runMigrate(ctx, &migrate.Migrator{
				DataDir:       *dataDir,
				Hostname:      *hostname,
				Image:         *image,
				ImageArchive:  *imageArchive,
				SourceRoot:    *sourceRoot,
				SourceDB:      *sourceDB,
				SourceStorage: *sourceStorage,
				SourceCerts:   *sourceCerts,
				DryRun:        *dryRun,
				Cleanup:       *cleanup,
				SkipVerify:    *skipVerify,
				SkipInstall:   *skipInstall,
				Out:           os.Stderr,
				Runner:        system.NewExecRunner(os.Stderr),
			})
		},
	}
}

func runMigrate(ctx context.Context, m *migrate.Migrator) int {
	if err := m.Run(ctx); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	return 0
}
