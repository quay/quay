package migrate

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
)

// cleanup removes old OMR services, containers, volumes, and secrets.
func (m *Migrator) cleanup(ctx context.Context) error {
	slog.Info("cleaning up old OMR installation")

	if err := m.stopAndDisableUnits(ctx); err != nil {
		return err
	}

	// The old quay-app container and quay-pod keep the volumes in use.
	for _, obj := range []struct{ kind, name string }{
		{"container", sourceContainerName},
		{"pod", podName},
	} {
		if err := m.removePodmanObject(ctx, obj.kind, obj.name); err != nil {
			return err
		}
	}
	for _, vol := range m.Source.VolumeNames {
		if err := m.removePodmanObject(ctx, "volume", vol); err != nil {
			return err
		}
	}

	if err := m.removeRedisSecret(ctx); err != nil {
		slog.Warn("failed to remove redis secret", "err", err)
	}

	if err := m.removeUnitFiles(); err != nil {
		return fmt.Errorf("remove unit files: %w", err)
	}

	if err := m.reloadSystemd(ctx); err != nil {
		slog.Warn("failed to reload systemd", "err", err)
	}

	slog.Info("old OMR installation cleaned up — ~/quay-install directory preserved (may contain rootCA distributed to clients)")
	return nil
}

func (m *Migrator) removeUnitFiles() error {
	for _, path := range m.Source.UnitFiles {
		slog.Info("removing unit file", "path", path)
		if err := os.Remove(path); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("remove %s: %w", path, err)
		}
	}
	return nil
}

// stopAndDisableUnits keeps the old services from restarting the containers
// cleanup removes, now or after a reboot.
func (m *Migrator) stopAndDisableUnits(ctx context.Context) error {
	if m.Runner == nil {
		return nil
	}
	units := make([]string, 0, len(m.Source.UnitFiles))
	for _, path := range m.Source.UnitFiles {
		unit := filepath.Base(path)
		slog.Info("stopping service", "service", unit)
		if err := m.runSourceService(ctx, "stop", unit); err != nil {
			slog.Warn("failed to stop service (may already be stopped)", "service", unit, "err", err)
		}
		units = append(units, unit)
	}
	return m.disableSourceServices(ctx, units...)
}

// removePodmanObject stops and removes a container or pod, or removes a
// volume, accepting one that is already gone. Volumes are never forced, so
// a volume something else still uses fails the cleanup.
func (m *Migrator) removePodmanObject(ctx context.Context, kind, name string) error {
	if m.Runner == nil {
		return nil
	}
	exists, err := m.podmanObjectExists(ctx, kind, name)
	if err != nil {
		return fmt.Errorf("check podman %s %s: %w", kind, name, err)
	}
	if !exists {
		slog.Info("podman object already removed", "kind", kind, "name", name)
		return nil
	}
	actions := []string{"stop", "rm"}
	if kind == "volume" {
		actions = []string{"rm"}
	}
	for _, action := range actions {
		slog.Info("removing old OMR podman object", "kind", kind, "action", action, "name", name)
		if err := m.Runner.Run(ctx, "podman", kind, action, name); err != nil {
			return fmt.Errorf("podman %s %s %s: %w", kind, action, name, err)
		}
	}
	return nil
}

// podmanObjectExists relies on podman's exists commands exiting 1 for a
// missing object; any other failure is an error.
func (m *Migrator) podmanObjectExists(ctx context.Context, kind, name string) (bool, error) {
	err := m.Runner.Run(ctx, "podman", kind, "exists", name)
	var exit interface{ ExitCode() int }
	if errors.As(err, &exit) && exit.ExitCode() == 1 {
		return false, nil
	}
	return err == nil, err
}

func (m *Migrator) removeRedisSecret(ctx context.Context) error {
	if m.Runner == nil {
		return nil
	}
	slog.Info("removing podman secret", "name", "redis_pass")
	return m.Runner.Run(ctx, "podman", "secret", "rm", "redis_pass")
}

func (m *Migrator) reloadSystemd(ctx context.Context) error {
	if m.Runner == nil {
		return nil
	}
	var args []string
	if m.Source.SystemdScope == scopeUser {
		args = []string{systemdUserFlag}
	}
	args = append(args, "daemon-reload")
	return m.Runner.Run(ctx, "systemctl", args...)
}
