// Package uninstaller implements the removal workflow for the registry's
// Quadlet-based systemd deployment.
package uninstaller

import (
	"context"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/system"
)

const serviceName = "quay"

// Config holds the parameters for an uninstall operation.
type Config struct {
	DataDir     string
	AutoApprove bool
}

// Uninstaller removes the registry's Quadlet-based systemd deployment.
type Uninstaller struct {
	systemd system.ServiceManager
	quadlet *system.QuadletManager
	env     *system.Env
	fs      system.FileSystem
}

// New detects the runtime environment and creates an Uninstaller.
func New(stderr io.Writer) (*Uninstaller, error) {
	env, err := system.NewEnv()
	if err != nil {
		return nil, fmt.Errorf("detect environment: %w", err)
	}

	runner := system.NewExecRunner(stderr)
	fs := system.OSFS{}

	return &Uninstaller{
		systemd: system.NewSystemdManager(runner, env),
		quadlet: system.NewQuadletManager(fs, env),
		env:     env,
		fs:      fs,
	}, nil
}

// validateDataDir checks that dir is safe to pass to os.RemoveAll. It rejects
// relative paths, the root filesystem, and the user's home directory, which
// could cause catastrophic data loss if supplied by accident.
func validateDataDir(dir string) error {
	if !filepath.IsAbs(dir) {
		return fmt.Errorf("data directory must be an absolute path, got %q", dir)
	}

	abs := filepath.Clean(dir)

	if abs == "/" {
		return fmt.Errorf("refusing to remove root directory %q", abs)
	}

	home, err := os.UserHomeDir()
	if err == nil && abs == home {
		return fmt.Errorf("refusing to remove home directory %q", abs)
	}

	return nil
}

// Run performs the uninstall sequence: stop service, remove Quadlet file,
// reload systemd, conditionally remove data, and disable linger.
func (u *Uninstaller) Run(ctx context.Context, cfg *Config) error {
	if cfg.AutoApprove {
		if err := validateDataDir(cfg.DataDir); err != nil {
			return fmt.Errorf("unsafe data directory: %w", err)
		}
	}

	if err := u.systemd.Stop(ctx, serviceName); err != nil {
		if errors.Is(err, system.ErrUnitNotFound) {
			slog.Info("service not running, continuing")
		} else {
			return fmt.Errorf("stop service: %w", err)
		}
	}

	if err := u.quadlet.Remove(serviceName); err != nil {
		return fmt.Errorf("remove quadlet: %w", err)
	}
	slog.Info("removed quadlet unit", "path", u.env.QuadletPath(serviceName))

	if err := u.systemd.DaemonReload(ctx); err != nil {
		return fmt.Errorf("reload systemd: %w", err)
	}

	if cfg.AutoApprove {
		if err := u.fs.RemoveAll(cfg.DataDir); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("remove data directory: %w", err)
		}
		slog.Info("removed data directory", "path", cfg.DataDir)
	}

	if u.env.Mode == system.UserMode {
		if err := u.systemd.DisableLinger(ctx); err != nil {
			slog.Warn("failed to disable linger", "err", err)
		}
	}

	slog.Info("uninstall complete")
	return nil
}
