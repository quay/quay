package migrate

import (
	"context"
	"fmt"
	"log/slog"
	"path/filepath"

	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/installer"
)

// upgradeSchema opens the copied database, backs it up, and runs the bridge
// migration to bring it to the Go binary's target schema version.
func (m *Migrator) upgradeSchema(ctx context.Context) error {
	dbPath := filepath.Join(m.DataDir, "quay.db")

	db, err := dbcore.OpenSQLite(dbPath)
	if err != nil {
		return fmt.Errorf("open database: %w", err)
	}
	defer func() { _ = db.Close() }()

	ver, err := dbcore.SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("read schema version: %w", err)
	}

	if ver == dbcore.TargetVersion {
		slog.Info("schema is current", "version", ver)
		return nil
	}

	slog.Info("upgrading schema", "from", ver, "to", dbcore.TargetVersion)

	backupPath, err := dbcore.BackupDatabase(ctx, db, dbPath)
	if err != nil {
		return fmt.Errorf("backup: %w", err)
	}
	slog.Info("database backup created", "path", backupPath)

	if err := dbcore.RunBridge(ctx, db, m.Out); err != nil {
		return fmt.Errorf("bridge migration (restore from %s): %w", backupPath, err)
	}

	if err := dbcore.IntegrityCheck(ctx, db); err != nil {
		return fmt.Errorf("post-migration integrity check: %w", err)
	}

	return nil
}

// stopOldOMR stops old OMR systemd services to free port 8443 and flush WAL.
func (m *Migrator) stopOldOMR(ctx context.Context) error { //nolint:unparam // error return kept for phase interface consistency
	if m.Runner == nil {
		slog.Info("no command runner, skipping service stop")
		return nil
	}
	if len(m.Source.UnitFiles) == 0 {
		slog.Info("no OMR services detected, skipping stop")
		return nil
	}

	var scopeArgs []string
	if m.Source.SystemdScope == scopeUser {
		scopeArgs = []string{"--user"}
	}

	for _, svc := range omrServiceNames {
		args := make([]string, len(scopeArgs), len(scopeArgs)+2)
		copy(args, scopeArgs)
		args = append(args, "stop", svc+".service")
		slog.Info("stopping service", "service", svc)
		if err := m.Runner.Run(ctx, "systemctl", args...); err != nil {
			slog.Warn("failed to stop service (may already be stopped)", "service", svc, "err", err)
		}
	}

	slog.Info("old OMR services stopped")
	return nil
}

// install chains into the existing installer to create the Quadlet unit and start the service.
func (m *Migrator) install(ctx context.Context) error {
	inst, err := installer.New(m.Out)
	if err != nil {
		return fmt.Errorf("create installer: %w", err)
	}

	cfg := installer.Config{
		Hostname:     m.Source.Hostname,
		DataDir:      m.DataDir,
		ImageArchive: m.Source.ImageArchive,
		Image:        m.Source.Image,
	}

	slog.Info("installing new registry", "hostname", cfg.Hostname, "data-dir", cfg.DataDir)
	if err := inst.Run(ctx, cfg); err != nil {
		return fmt.Errorf("install: %w", err)
	}

	removeMarker(m.DataDir)
	slog.Info("new registry installed and running")
	return nil
}
