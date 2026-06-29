package migrate

import (
	"context"
	"fmt"
	"log/slog"
	"os"
)

// cleanup removes old OMR services, volumes, and secrets.
func (m *Migrator) cleanup(ctx context.Context) error {
	slog.Info("cleaning up old OMR installation")

	if err := m.removeUnitFiles(); err != nil {
		return fmt.Errorf("remove unit files: %w", err)
	}

	m.removeVolumes(ctx)

	if err := m.removeRedisSecret(ctx); err != nil {
		slog.Warn("failed to remove redis secret", "err", err)
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

func (m *Migrator) removeVolumes(ctx context.Context) {
	if m.Runner == nil {
		return
	}
	for _, vol := range m.Source.VolumeNames {
		slog.Info("removing podman volume", "name", vol)
		if err := m.Runner.Run(ctx, "podman", "volume", "rm", vol); err != nil {
			slog.Warn("failed to remove volume", "name", vol, "err", err)
		}
	}
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
		args = []string{"--user"}
	}
	args = append(args, "daemon-reload")
	return m.Runner.Run(ctx, "systemctl", args...)
}
