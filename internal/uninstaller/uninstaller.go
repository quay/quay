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

// validateDataDir returns an error when path, after normalisation, is a
// known-dangerous filesystem location.  It rejects the filesystem root "/",
// bare current-directory references such as ".", and the current user's home
// directory.  The check runs before any destructive step so that a bad
// data-dir never causes a partial uninstall.
func validateDataDir(path string) error {
	if path == "" {
		return fmt.Errorf("data directory path is empty")
	}
	// Reject bare current-directory references before resolving them.
	if filepath.Clean(path) == "." {
		return fmt.Errorf("data directory %q is a relative current-directory reference: refusing to remove", path)
	}
	// Resolve to an absolute, clean path so that "///", relative paths, and
	// symlink-like constructs are all normalised before comparison.
	resolved, err := filepath.Abs(path)
	if err != nil {
		return fmt.Errorf("resolve data directory path: %w", err)
	}
	// Reject the filesystem root (covers "/", "///", etc.).
	if resolved == "/" {
		return fmt.Errorf("data directory %q resolves to a filesystem root: refusing to remove", path)
	}
	// Reject the user's home directory.
	home, err := os.UserHomeDir()
	if err == nil {
		if resolved == filepath.Clean(home) {
			return fmt.Errorf("data directory %q resolves to the user home directory: refusing to remove", path)
		}
	}
	return nil
}

// Run performs the uninstall sequence: stop service, remove Quadlet file,
// reload systemd, conditionally remove data, and disable linger.
func (u *Uninstaller) Run(ctx context.Context, cfg *Config) error {
	// Validate the data directory before any service or filesystem operation
	// so that a dangerous path causes a clean failure with no partial work.
	if cfg.AutoApprove {
		if err := validateDataDir(cfg.DataDir); err != nil {
			return fmt.Errorf("data directory validation: %w", err)
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
