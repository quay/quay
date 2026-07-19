package cmd

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/quay/quay/internal/installer"
)

func newInstallCmd() *Command {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (required)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	port := fs.String("port", "", "HTTPS port for the registry (default 8443; an existing port is preserved on upgrade)")
	sslCert := fs.String("ssl-cert", "", "path to TLS certificate (PEM)")
	sslKey := fs.String("ssl-key", "", "path to TLS private key (PEM)")
	sslSkipHostnameVerification := fs.Bool("ssl-skip-hostname-verification", false, "allow TLS certificate hostname to differ from -hostname")
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
			if err := installer.ValidateSSLFlags(*sslCert, *sslKey); err != nil {
				fmt.Fprintln(os.Stderr, "error:", err)
				cmd.Usage(os.Stderr)
				return 1
			}
			return runInstall(ctx, &installer.Config{
				Hostname:                    *hostname,
				DataDir:                     *dataDir,
				Port:                        *port,
				SSLCert:                     *sslCert,
				SSLKey:                      *sslKey,
				SSLSkipHostnameVerification: *sslSkipHostnameVerification,
				ImageArchive:                *imageArchive,
				Image:                       *image,
			})
		},
	}
}

func runInstall(ctx context.Context, cfg *installer.Config) int {
	if err := installer.ValidateHostname(cfg.Hostname); err != nil {
		slog.Error("invalid hostname", "err", err)
		return 1
	}

	inst, err := installer.New(os.Stderr)
	if err != nil {
		slog.Error("installer setup failed", "err", err)
		return 1
	}

	if err := inst.Run(ctx, cfg); err != nil {
		slog.Error("install failed", "err", err)
		return 1
	}

	return 0
}
