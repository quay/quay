package migrate

import (
	"context"
	"crypto/tls"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/config"
	"github.com/quay/quay/internal/dal/dbcore"
	"github.com/quay/quay/internal/installer"
	"github.com/quay/quay/internal/system"
)

const markerFile = ".migration-in-progress"

// validate checks source compatibility, authentication policy, and target readiness.
// All source database checks are read-only and finish before source shutdown.
func (m *Migrator) validate(ctx context.Context) error {
	if !m.SkipInstall {
		if err := system.ValidateCgroupsForQuadlet(ctx, m.Runner); err != nil {
			return fmt.Errorf("system compatibility: %w", err)
		}
	}

	db, err := dbcore.OpenSQLiteReadOnly(m.Source.DBPath)
	if err != nil {
		return fmt.Errorf("open source database: %w", err)
	}
	defer func() { _ = db.Close() }()

	if err := m.validateSourceAuth(ctx, db); err != nil {
		return fmt.Errorf("source authentication preflight: %w", err)
	}
	if err := dbcore.ValidateSourceCompatibility(ctx, db); err != nil {
		return err
	}
	if err := m.validateRegistryJWTSource(ctx); err != nil {
		return err
	}

	if m.Source.ConfigDir != "" {
		certPath := filepath.Join(m.Source.ConfigDir, "ssl.cert")
		keyPath := filepath.Join(m.Source.ConfigDir, "ssl.key")
		if err := validateCertKeyPair(certPath, keyPath); err != nil {
			return fmt.Errorf("TLS certificate validation: %w", err)
		}
	}

	if m.Source.StoragePath != "" {
		if err := validateStorageDir(m.Source.StoragePath); err != nil {
			return fmt.Errorf("storage validation: %w", err)
		}
	}

	if err := validateTargetDir(m.DataDir); err != nil {
		return err
	}

	if err := m.validateInstallInputs(); err != nil {
		return err
	}

	slog.Info("validation passed")
	return nil
}

func (m *Migrator) validateRegistryJWTSource(ctx context.Context) error {
	if m.Source.ConfigDir == "" {
		return fmt.Errorf("source config directory not detected — provide -source-certs with config.yaml, quay.pem, and quay.kid")
	}
	sourcePath := filepath.Join(m.Source.ConfigDir, runtimeConfigFile)
	sourceCfg, err := config.Load(sourcePath)
	if err != nil {
		return fmt.Errorf("load source config for registry JWT key validation: %w", err)
	}
	key, _, err := loadApprovedRegistryJWTSigningKey(ctx, m.Source.DBPath, m.Source.ConfigDir, sourceCfg, m.Runner)
	if err != nil {
		return fmt.Errorf("registry JWT key validation: %w", err)
	}
	m.sourceRegistryJWTKey = key
	return nil
}

func (m *Migrator) validateInstallInputs() error {
	if m.SkipInstall {
		return nil
	}
	if m.Source.Hostname == "" {
		return fmt.Errorf("hostname not detected — provide -hostname")
	}
	if err := installer.ValidateHostname(m.Source.Hostname); err != nil {
		return fmt.Errorf("invalid hostname %q: %w", m.Source.Hostname, err)
	}
	if m.Source.ImageArchive == "" && m.Source.Image == "" {
		return fmt.Errorf("no image archive found — provide -image-archive or -image flag")
	}
	return nil
}

func validateCertKeyPair(certPath, keyPath string) error {
	if _, err := os.Stat(certPath); err != nil {
		return fmt.Errorf("cert not found: %s", certPath)
	}
	if _, err := os.Stat(keyPath); err != nil {
		return fmt.Errorf("key not found: %s", keyPath)
	}
	_, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return fmt.Errorf("cert/key mismatch: %w", err)
	}
	return nil
}

func validateStorageDir(path string) error {
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("storage directory not found: %s", path)
	}
	if !info.IsDir() {
		return fmt.Errorf("storage path is not a directory: %s", path)
	}
	return nil
}

func validateTargetDir(path string) error {
	entries, err := os.ReadDir(path)
	if os.IsNotExist(err) {
		return nil // will be created
	}
	if err != nil {
		return fmt.Errorf("read target directory: %w", err)
	}

	for _, e := range entries {
		if e.Name() == markerFile {
			slog.Info("found migration marker, resuming previous migration")
			return nil
		}
	}

	if len(entries) > 0 {
		return fmt.Errorf("target directory %s is not empty — specify a clean directory or remove existing files", path)
	}
	return nil
}
