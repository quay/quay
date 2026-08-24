package migrate

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"os"
	"path/filepath"
	"strings"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/installer"
)

const (
	quayAppUnit      = "quay-app.service"
	quayPodUnit      = "quay-pod.service"
	quayPostgresUnit = "quay-postgres.service"
	quayRedisUnit    = "quay-redis.service"
)

// upgradeSchema opens the copied database, backs it up, and runs the bridge
// migration to bring it to the Go binary's target schema version.
func (m *Migrator) upgradeSchema(ctx context.Context) error {
	dbPath := filepath.Join(m.DataDir, "quay.db")
	if m.Source.DatabaseKind == databasePostgres {
		dbPath = m.postgresPartialDBPath()
	}

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
		if m.Source.DatabaseKind == databasePostgres {
			return fmt.Errorf("converted PostgreSQL database unexpectedly has target schema version %q", ver)
		}
		slog.Info("schema is current", "version", ver)
		return nil
	}

	slog.Info("upgrading schema", "from", ver, "to", dbcore.TargetVersion)

	backupPath, err := dbcore.BackupDatabase(ctx, db, dbPath)
	if err != nil {
		return fmt.Errorf("backup: %w", err)
	}
	slog.Info("database backup created", "path", backupPath)

	if err := dbcore.RunBridge(ctx, db); err != nil {
		return fmt.Errorf("bridge migration (restore from %s): %w", backupPath, err)
	}

	if err := dbcore.IntegrityCheck(ctx, db); err != nil {
		return fmt.Errorf("post-migration integrity check: %w", err)
	}
	if err := dbcore.ForeignKeyCheck(ctx, db); err != nil {
		return fmt.Errorf("post-migration foreign key check: %w", err)
	}

	if m.Source.DatabaseKind == databasePostgres {
		return m.publishConvertedDatabase(ctx, db, dbPath, backupPath)
	}

	return nil
}

func (m *Migrator) publishConvertedDatabase(ctx context.Context, db *sql.DB, dbPath, backupPath string) error {
	if _, err := db.ExecContext(ctx, "PRAGMA wal_checkpoint(TRUNCATE)"); err != nil {
		return fmt.Errorf("checkpoint converted database: %w", err)
	}
	if err := db.Close(); err != nil {
		return fmt.Errorf("close converted database: %w", err)
	}
	targetPath := filepath.Join(m.DataDir, "quay.db")
	if _, err := os.Stat(targetPath); err == nil {
		return fmt.Errorf("target database already exists")
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat target database: %w", err)
	}
	if err := os.Rename(dbPath, targetPath); err != nil {
		return fmt.Errorf("publish converted database: %w", err)
	}
	if backupPath != "" {
		if err := os.Remove(backupPath); err != nil && !os.IsNotExist(err) {
			slog.Warn("failed to remove converted database backup", "path", backupPath, "err", err)
		}
	}
	return nil
}

// stopSourceServices stops source systemd services to free the listen port and flush WAL.
func (m *Migrator) stopSourceServices(ctx context.Context) error { //nolint:unparam // keeps error return for phase-method consistency
	if m.Runner == nil {
		slog.Info("no command runner, skipping service stop")
		return nil
	}

	if len(m.Source.UnitFiles) == 0 {
		discovered := m.discoverOMRScope(ctx)
		if discovered == "" {
			slog.Info("no OMR services detected, skipping stop")
			return nil
		}
		m.Source.SystemdScope = discovered
		slog.Info("discovered running OMR services via probe", "scope", discovered)
	}

	for _, svc := range omrServiceNames {
		slog.Info("stopping service", "service", svc)
		if err := m.runSourceService(ctx, "stop", svc+".service"); err != nil {
			slog.Warn("failed to stop service (may already be stopped)", "service", svc, "err", err)
		}
	}

	slog.Info("old OMR services stopped (or already inactive)")
	return nil
}

// discoverOMRScope probes quay-app.service (the port-binding service) in
// system then user scope, matching the probe order in detectSystemd.
func (m *Migrator) discoverOMRScope(ctx context.Context) string {
	unit := omrServiceNames[0] + ".service"
	for _, scope := range []struct {
		name string
		args []string
	}{
		{scopeSystem, []string{"is-active", "--quiet", unit}},
		{scopeUser, []string{systemdUserFlag, "is-active", "--quiet", unit}},
	} {
		if err := m.Runner.Run(ctx, "systemctl", scope.args...); err == nil {
			return scope.name
		}
	}
	return ""
}

func (m *Migrator) stopPostgresApp(ctx context.Context) error {
	return m.runSourceService(ctx, "stop", quayAppUnit)
}

func (m *Migrator) stopPostgresRemainingServices(ctx context.Context) error {
	var errs []error
	for _, service := range []string{quayPostgresUnit, quayRedisUnit, quayPodUnit} {
		if err := m.runSourceService(ctx, "stop", service); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func (m *Migrator) rollbackPostgresSource(ctx context.Context) error {
	var errs []error
	inst, err := installer.New(m.Out)
	if err != nil {
		errs = append(errs, fmt.Errorf("create installer for rollback: %w", err))
	} else if err := inst.RemoveFailedInstallation(ctx); err != nil {
		errs = append(errs, fmt.Errorf("remove failed target install: %w", err))
	}
	for _, service := range []string{quayPodUnit, quayPostgresUnit, quayRedisUnit, quayAppUnit} {
		if err := m.runSourceService(ctx, "start", service); err != nil {
			errs = append(errs, err)
		}
	}
	return errors.Join(errs...)
}

func (m *Migrator) runSourceService(ctx context.Context, action, service string) error {
	if m.Runner == nil {
		return fmt.Errorf("no command runner for %s %s", action, service)
	}
	args := []string{action, service}
	if m.Source.SystemdScope == scopeUser {
		args = append([]string{systemdUserFlag}, args...)
	}
	if err := m.Runner.Run(ctx, "systemctl", args...); err != nil {
		return fmt.Errorf("%s %s: %w", action, service, err)
	}
	return nil
}

// install chains into the existing installer to create the Quadlet unit and start the service.
func (m *Migrator) install(ctx context.Context) error {
	inst, err := installer.New(m.Out)
	if err != nil {
		return fmt.Errorf("create installer: %w", err)
	}
	if m.Source.DatabaseKind == databasePostgres && inst.HasInstallation() {
		return fmt.Errorf("an existing target Quay installation must be removed before PostgreSQL migration")
	}

	configPath := ""
	port := m.Source.Port
	runtimeConfigPath := filepath.Join(m.DataDir, runtimeConfigFile)
	if _, err := os.Stat(runtimeConfigPath); err == nil {
		configPath = "/data/" + runtimeConfigFile
		port, err = runtimeConfigPort(runtimeConfigPath)
		if err != nil {
			return err
		}
	} else if !os.IsNotExist(err) {
		return fmt.Errorf("stat runtime config: %w", err)
	}

	cfg := &installer.Config{
		Hostname:     m.Source.Hostname,
		DataDir:      m.DataDir,
		ImageArchive: m.Source.ImageArchive,
		Image:        m.Source.Image,
		ConfigPath:   configPath,
		Port:         port,
	}

	slog.Info("installing new registry", "hostname", cfg.Hostname, "data-dir", cfg.DataDir)
	if err := inst.Run(ctx, cfg); err != nil {
		return fmt.Errorf("install: %w", err)
	}

	removeMarker(m.DataDir)
	slog.Info("new registry installed and running")
	return nil
}

func runtimeConfigPort(path string) (string, error) {
	cfg, err := config.Load(path)
	if err != nil {
		return "", fmt.Errorf("load runtime config: %w", err)
	}
	return runtimeServerHostnamePort(cfg.ServerHostname)
}

func runtimeServerHostnamePort(serverHostname string) (string, error) {
	_, port, err := net.SplitHostPort(serverHostname)
	if err != nil {
		hostname := strings.Trim(serverHostname, "[]")
		if net.ParseIP(hostname) != nil || !strings.Contains(serverHostname, ":") {
			return "8443", nil
		}
		return "", fmt.Errorf("parse runtime SERVER_HOSTNAME %q: %w", serverHostname, err)
	}
	if port == "" {
		return "8443", nil
	}
	if err := installer.ValidatePort(port); err != nil {
		return "", fmt.Errorf("invalid runtime SERVER_HOSTNAME port %q: %w", port, err)
	}
	return port, nil
}
