package cmd

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/quay/quay/internal/installer"
	"github.com/quay/quay/internal/system"
)

func newInstallCmd() *Command {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (required)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", installer.DefaultImage, "container image to use")

	return &Command{
		Name:     "install",
		Synopsis: "Set up or upgrade registry (Quadlet service)",
		Flags:    fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if *hostname == "" {
				fmt.Fprintln(os.Stderr, "error: -hostname is required")
				cmd.Usage(os.Stderr)
				return 1
			}
			return runInstall(ctx, *hostname, *dataDir, *imageArchive, *image)
		},
	}
}

func runInstall(ctx context.Context, hostname, dataDir, imageArchive, image string) int {
	if err := installer.ValidateHostname(hostname); err != nil {
		slog.Error("invalid hostname", "err", err)
		return 1
	}

	env, err := system.NewEnv()
	if err != nil {
		slog.Error("environment error", "err", err)
		return 1
	}

	runner := system.NewExecRunner(os.Stderr)
	fs := system.OSFS{}

	inst := installer.New(
		system.NewPodmanLoader(runner),
		system.NewSystemdManager(runner, env),
		system.NewQuadletManager(fs, env),
		env,
		fs,
	)

	if err := inst.Run(ctx, installer.Config{
		Hostname:     hostname,
		DataDir:      dataDir,
		ImageArchive: imageArchive,
		Image:        image,
	}); err != nil {
		slog.Error("install failed", "err", err)
		return 1
	}

	return 0
}
