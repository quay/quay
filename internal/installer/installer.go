// Package installer implements the install and upgrade workflow for the
// registry's Quadlet-based systemd deployment.
package installer

import (
	"context"
	"crypto/x509"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"path/filepath"
	"time"

	"github.com/quay/quay/internal/registry"
	"github.com/quay/quay/internal/system"
)

const (
	// DefaultImage is the default container image for the registry.
	DefaultImage = "quay.io/quay/quay-mirror:latest"

	quadletServiceName = "quay"
)

// Config holds the parameters for an install or upgrade operation.
type Config struct {
	Hostname     string
	DataDir      string
	ImageArchive string
	Image        string
}

// Installer orchestrates fresh installs and upgrades of the registry
// as a Quadlet systemd service.
type Installer struct {
	images  system.ImageLoader
	runner  system.CommandRunner
	systemd system.ServiceManager
	quadlet *system.QuadletManager
	env     *system.Env
	fs      system.FileSystem
}

// New detects the runtime environment and creates an Installer with the
// appropriate system backends.
func New(stderr io.Writer) (*Installer, error) {
	env, err := system.NewEnv()
	if err != nil {
		return nil, fmt.Errorf("detect environment: %w", err)
	}

	runner := system.NewExecRunner(stderr)
	fs := system.OSFS{}

	return &Installer{
		images:  system.NewPodmanLoader(runner),
		runner:  runner,
		systemd: system.NewSystemdManager(runner, env),
		quadlet: system.NewQuadletManager(fs, env),
		env:     env,
		fs:      fs,
	}, nil
}

// Run performs an install or upgrade based on whether a Quadlet unit already
// exists.
func (inst *Installer) Run(ctx context.Context, cfg Config) error {
	imageRef, err := inst.resolveImage(ctx, cfg.ImageArchive, cfg.Image)
	if err != nil {
		return fmt.Errorf("image resolution: %w", err)
	}

	if inst.quadlet.Exists(quadletServiceName) {
		if err := inst.upgrade(ctx, imageRef); err != nil {
			return fmt.Errorf("upgrade: %w", err)
		}
	} else {
		if err := inst.freshInstall(ctx, cfg, imageRef); err != nil {
			return fmt.Errorf("install: %w", err)
		}
	}

	healthURL := fmt.Sprintf("https://%s:8443/healthz", cfg.Hostname)
	certPath := filepath.Join(cfg.DataDir, "ssl.cert")
	slog.Info("waiting for registry to start")
	if err := inst.waitForHealth(ctx, healthURL, certPath, 30*time.Second); err != nil {
		inst.dumpContainerLogs(ctx)
		return fmt.Errorf("health check: %w", err)
	}

	credPath := filepath.Join(cfg.DataDir, "credentials")
	slog.Info("registry running", "url", fmt.Sprintf("https://%s:8443", cfg.Hostname), "credentials", credPath)
	return nil
}

func (inst *Installer) resolveImage(ctx context.Context, archive, image string) (string, error) {
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

func (inst *Installer) upgrade(ctx context.Context, imageRef string) error {
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

func (inst *Installer) freshInstall(ctx context.Context, cfg Config, imageRef string) error {
	for _, dir := range []string{cfg.DataDir, filepath.Join(cfg.DataDir, "storage")} {
		if err := inst.fs.MkdirAll(dir, 0o750); err != nil {
			return fmt.Errorf("create directory %s: %w", dir, err)
		}
	}

	spec := system.QuadletSpec{
		Image:    imageRef,
		DataDir:  cfg.DataDir,
		Hostname: cfg.Hostname,
		Port:     "8443",
	}
	if err := inst.quadlet.Install(quadletServiceName, spec); err != nil {
		return fmt.Errorf("install quadlet: %w", err)
	}
	slog.Info("quadlet installed", "path", inst.env.QuadletPath(quadletServiceName))

	if err := inst.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}
	if err := inst.systemd.Start(ctx, quadletServiceName); err != nil {
		return fmt.Errorf("start service: %w", err)
	}

	if inst.env.Mode == system.UserMode {
		_ = inst.systemd.EnableLinger(ctx)
	}
	return nil
}

func (inst *Installer) waitForHealth(ctx context.Context, url, certPath string, timeout time.Duration) error {
	deadline := time.After(timeout)

	// Wait for the container to generate the TLS certificate.
	for {
		if _, err := inst.fs.Stat(certPath); err == nil {
			break
		}
		select {
		case <-deadline:
			return fmt.Errorf("timed out waiting for certificate: %s", certPath)
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(500 * time.Millisecond):
		}
	}

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

func (inst *Installer) dumpContainerLogs(ctx context.Context) {
	slog.Info("dumping container logs for diagnostics")
	_ = inst.runner.Run(ctx, "podman", "logs", quadletServiceName)
	_ = inst.runner.Run(ctx, "systemctl", "status", quadletServiceName)
}
