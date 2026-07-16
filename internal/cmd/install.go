package cmd

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"os/exec"
	"strings"

	"github.com/quay/quay/internal/installer"
)

func newInstallCmd() *Command {
	return newInstallCmdWithDeps(os.Stdin, runInstall)
}

func newInstallCmdWithDeps(stdin io.Reader, install func(context.Context, *installer.Config) int) *Command {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (auto-detected if not set)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	port := fs.String("port", "", "HTTPS port for the registry (default 8443; an existing port is preserved on upgrade)")
	sslCert := fs.String("ssl-cert", "", "path to TLS certificate (PEM)")
	sslKey := fs.String("ssl-key", "", "path to TLS private key (PEM)")
	sslSkipHostnameVerification := fs.Bool("ssl-skip-hostname-verification", false, "allow TLS certificate hostname to differ from -hostname")
	initUser := fs.String("init-user", "admin", "admin username for initial setup")
	initPasswordStdin := fs.Bool("init-password-stdin", false, "read the initial admin password from stdin")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", installer.DefaultImage, "container image to use")

	return &Command{
		Name:     "install",
		Synopsis: "Set up or upgrade registry (Quadlet service)",
		Flags:    fs,
		Run: func(ctx context.Context, cmd *Command, _ []string) int {
			if *hostname == "" {
				detected, err := detectHostname(ctx)
				if err != nil {
					fmt.Fprintf(os.Stderr, "error: could not auto-detect hostname: %v\nProvide -hostname explicitly.\n", err)
					cmd.Usage(os.Stderr)
					return 1
				}
				slog.Info("auto-detected hostname", "hostname", detected)
				*hostname = detected
			}
			if err := installer.ValidateSSLFlags(*sslCert, *sslKey); err != nil {
				fmt.Fprintln(os.Stderr, "error:", err)
				cmd.Usage(os.Stderr)
				return 1
			}
			var initPassword string
			if *initPasswordStdin {
				var err error
				initPassword, err = readInitPassword(stdin)
				if err != nil {
					fmt.Fprintln(os.Stderr, "error: read initial password:", err)
					return 1
				}
			}
			return install(ctx, &installer.Config{
				Hostname:                    *hostname,
				DataDir:                     *dataDir,
				Port:                        *port,
				SSLCert:                     *sslCert,
				SSLKey:                      *sslKey,
				SSLSkipHostnameVerification: *sslSkipHostnameVerification,
				InitUser:                    *initUser,
				InitPassword:                initPassword,
				InitPasswordSet:             *initPasswordStdin,
				ImageArchive:                *imageArchive,
				Image:                       *image,
			})
		},
	}
}

// readInitPassword follows the Podman password-stdin convention: consume the
// secret from stdin and remove one final LF (or CRLF) produced by a typical
// shell pipe. All other bytes, including surrounding spaces, are preserved.
func readInitPassword(r io.Reader) (string, error) {
	data, err := io.ReadAll(io.LimitReader(r, installer.MaxInitPasswordBytes+3))
	if err != nil {
		return "", err
	}
	password := string(data)
	if strings.HasSuffix(password, "\r\n") {
		password = strings.TrimSuffix(password, "\r\n")
	} else {
		password = strings.TrimSuffix(password, "\n")
	}
	if err := installer.ValidateInitPassword(password); err != nil {
		return "", err
	}
	return password, nil
}

func detectHostname(ctx context.Context) (string, error) {
	out, err := exec.CommandContext(ctx, "hostname", "-f").Output()
	if err != nil {
		return "", fmt.Errorf("'hostname -f' failed: %w", err)
	}
	fqdn := strings.TrimSpace(string(out))
	if fqdn == "" {
		return "", fmt.Errorf("'hostname -f' returned empty output")
	}
	return fqdn, nil
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
