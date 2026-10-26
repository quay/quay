package cmd

import (
	"context"
	"flag"
	"fmt"
	"log/slog"
	"os"

	"github.com/quay/quay/internal/installer"
)

func newUpgradeCmd() *Command {
	return newUpgradeCmdWithDeps(runUpgrade)
}

func newUpgradeCmdWithDeps(upgrade func(context.Context, *installer.Config) int) *Command {
	fs := flag.NewFlagSet("upgrade", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (existing hostname is preserved when omitted)")
	dataDir := fs.String("data-dir", "", "directory for database, storage, and certs (detected from the existing installation when omitted)")
	port := fs.String("port", "", "HTTPS port for the registry (existing port is preserved when omitted)")
	sslCert := fs.String("ssl-cert", "", "path to replacement TLS certificate (PEM)")
	sslKey := fs.String("ssl-key", "", "path to replacement TLS private key (PEM)")
	sslSkipHostnameVerification := fs.Bool("ssl-skip-hostname-verification", false, "allow TLS certificate hostname to differ from -hostname")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")

	return &Command{
		Name:        "upgrade",
		Synopsis:    "Upgrade an existing registry installation",
		Description: "Updates the container image of an installed registry in place, preserving its data, hostname, and port. Fails if the registry is not installed; use '" + BinaryName + " install' first.",
		Flags:       fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if err := installer.ValidateSSLFlags(*sslCert, *sslKey); err != nil {
				fmt.Fprintln(os.Stderr, "error:", err)
				cmd.Usage(os.Stderr)
				return 1
			}
			return upgrade(ctx, &installer.Config{
				Hostname:                    *hostname,
				DataDir:                     *dataDir,
				Port:                        *port,
				SSLCert:                     *sslCert,
				SSLKey:                      *sslKey,
				SSLSkipHostnameVerification: *sslSkipHostnameVerification,
				ImageArchive:                *imageArchive,
				Image:                       installer.DefaultImage,
			})
		},
	}
}

func runUpgrade(ctx context.Context, cfg *installer.Config) int {
	inst, err := installer.New(os.Stderr)
	if err != nil {
		slog.Error("installer setup failed", "err", err)
		return 1
	}

	if err := inst.Upgrade(ctx, cfg); err != nil {
		slog.Error("upgrade failed", "err", err)
		return 1
	}

	return 0
}
