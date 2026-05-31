package cmd

import (
	"context"
	"crypto/x509"
	"flag"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/quay/quay/internal/registry"
	"github.com/quay/quay/internal/system"
)

const (
	defaultImage       = "quay.io/quay/quay-mirror:latest"
	quadletServiceName = "quay"
)

type installOpts struct {
	hostname     string
	dataDir      string
	imageArchive string
	image        string
}

type installer struct {
	images  system.ImageLoader
	systemd system.ServiceManager
	quadlet *system.QuadletManager
	env     *system.Env
	fs      system.FileSystem
}

func newInstallCmd() *Command {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	hostname := fs.String("hostname", "", "server hostname for TLS and config (required)")
	dataDir := fs.String("data-dir", "/var/lib/quay", "directory for database, storage, and certs")
	imageArchive := fs.String("image-archive", "", "path to container image tar (offline mode)")
	image := fs.String("image", defaultImage, "container image to use")

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
			if err := validateHostname(*hostname); err != nil {
				fmt.Fprintf(os.Stderr, "error: invalid hostname: %v\n", err)
				return 1
			}

			opts := installOpts{
				hostname:     *hostname,
				dataDir:      *dataDir,
				imageArchive: *imageArchive,
				image:        *image,
			}

			return runInstall(ctx, opts)
		},
	}
}

func runInstall(ctx context.Context, opts installOpts) int {
	env, err := system.NewEnv()
	if err != nil {
		slog.Error("environment error", "err", err)
		return 1
	}

	runner := system.NewExecRunner(os.Stderr)
	fs := system.OSFS{}

	inst := &installer{
		images:  system.NewPodmanLoader(runner),
		systemd: system.NewSystemdManager(runner, env),
		quadlet: system.NewQuadletManager(fs, env),
		env:     env,
		fs:      fs,
	}

	return inst.run(ctx, opts)
}

func (inst *installer) run(ctx context.Context, opts installOpts) int {
	imageRef, err := inst.resolveImage(ctx, opts.imageArchive, opts.image)
	if err != nil {
		slog.Error("image resolution failed", "err", err)
		return 1
	}

	if inst.quadlet.Exists(quadletServiceName) {
		if err := inst.upgrade(ctx, imageRef); err != nil {
			slog.Error("upgrade failed", "err", err)
			return 1
		}
	} else {
		if err := inst.freshInstall(ctx, opts, imageRef); err != nil {
			slog.Error("install failed", "err", err)
			return 1
		}
	}

	healthURL := fmt.Sprintf("https://%s:8443/healthz", opts.hostname)
	certPath := filepath.Join(opts.dataDir, "ssl.cert")
	slog.Info("waiting for registry to start")
	if err := inst.waitForHealth(ctx, healthURL, certPath, 30*time.Second); err != nil {
		slog.Error("health check failed", "err", err)
		return 1
	}

	credPath := filepath.Join(opts.dataDir, "credentials")
	slog.Info("registry running", "url", fmt.Sprintf("https://%s:8443", opts.hostname), "credentials", credPath)
	return 0
}

func (inst *installer) resolveImage(ctx context.Context, archive, image string) (string, error) {
	if archive != "" {
		slog.Info("loading container image", "archive", archive)
		ref, err := inst.images.Load(ctx, archive)
		if err != nil {
			return "", fmt.Errorf("loading image: %w", err)
		}
		slog.Info("loaded image", "ref", ref)
		return ref, nil
	}
	slog.Info("pulling container image", "image", image)
	if err := inst.images.Pull(ctx, image); err != nil {
		return "", fmt.Errorf("pulling image: %w", err)
	}
	return image, nil
}

func (inst *installer) upgrade(ctx context.Context, imageRef string) error {
	slog.Info("existing installation detected, upgrading")

	slog.Info("stopping registry")
	if err := inst.systemd.Stop(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("stop service: %w", err)
	}

	if err := inst.quadlet.UpdateImage(quadletServiceName, imageRef); err != nil {
		return fmt.Errorf("update quadlet: %w", err)
	}
	slog.Info("updated quadlet", "path", inst.env.QuadletPath(quadletServiceName))

	if err := inst.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}
	if err := inst.systemd.Start(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("start service: %w", err)
	}
	return nil
}

func (inst *installer) freshInstall(ctx context.Context, opts installOpts, imageRef string) error {
	for _, dir := range []string{opts.dataDir, filepath.Join(opts.dataDir, "storage")} {
		if err := inst.fs.MkdirAll(dir, 0o750); err != nil {
			return fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	spec := system.QuadletSpec{
		Image:    imageRef,
		DataDir:  opts.dataDir,
		Hostname: opts.hostname,
		Port:     "8443",
	}
	if err := inst.quadlet.Install(quadletServiceName, spec); err != nil {
		return fmt.Errorf("install quadlet: %w", err)
	}
	slog.Info("quadlet installed", "path", inst.env.QuadletPath(quadletServiceName))

	if err := inst.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}
	if err := inst.systemd.Enable(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("enable service: %w", err)
	}

	if inst.env.Mode == system.UserMode {
		_ = inst.systemd.EnableLinger(ctx)
	}
	return nil
}

func (inst *installer) waitForHealth(ctx context.Context, url, certPath string, timeout time.Duration) error {
	caCert, err := inst.fs.ReadFile(certPath)
	if err != nil {
		return fmt.Errorf("read TLS certificate: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(caCert) {
		return fmt.Errorf("parse TLS certificate: %s", certPath)
	}
	tlsCfg := registry.SecureTLSConfig()
	tlsCfg.RootCAs = pool
	client := &http.Client{
		Timeout:   2 * time.Second,
		Transport: &http.Transport{TLSClientConfig: tlsCfg},
	}
	return system.WaitForHealth(ctx, client, url, timeout)
}

func validateHostname(hostname string) error {
	if len(hostname) > 253 {
		return fmt.Errorf("exceeds 253 characters (got %d)", len(hostname))
	}
	if net.ParseIP(hostname) != nil {
		return nil
	}
	labels := strings.Split(hostname, ".")
	for _, label := range labels {
		if label == "" {
			return fmt.Errorf("contains empty label")
		}
		if len(label) > 63 {
			return fmt.Errorf("label %q exceeds 63 characters", label)
		}
		if !isAlphanumeric(rune(label[0])) || !isAlphanumeric(rune(label[len(label)-1])) {
			return fmt.Errorf("label %q must start and end with alphanumeric character", label)
		}
		for _, c := range label {
			if !isAlphanumeric(c) && c != '-' {
				return fmt.Errorf("label %q contains invalid character %q", label, c)
			}
		}
	}
	return nil
}

func isAlphanumeric(c rune) bool {
	return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9')
}
