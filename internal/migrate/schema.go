package migrate

import (
	"context"
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

// stopSourceServices stops source systemd services to free port 8443 and flush WAL.
func (m *Migrator) stopSourceServices(ctx context.Context) error {
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

	var stopErrs []error
	for _, svc := range omrServiceNames {
		args := make([]string, len(scopeArgs), len(scopeArgs)+2)
		copy(args, scopeArgs)
		args = append(args, "stop", svc+".service")
		slog.Info("stopping service", "service", svc)
		if err := m.Runner.Run(ctx, "systemctl", args...); err != nil {
			stopErrs = append(stopErrs, fmt.Errorf("stop OMR service %s: %w", svc, err))
			slog.Warn("failed to stop service (may already be stopped)", "service", svc, "err", err)
		}
	}
	if err := errors.Join(stopErrs...); err != nil {
		return fmt.Errorf("stop old OMR services: %w", err)
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

	configPath := ""
	port := ""
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
