package migrate

import (
	"context"
	"crypto/tls"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/quay/quay/internal/dal/dbcore"
)

const markerFile = ".migration-in-progress"

// validate checks source integrity and target readiness.
func (m *Migrator) validate(ctx context.Context) error {
	if _, err := os.Stat(m.Source.DBPath); err != nil {
		return fmt.Errorf("source database not found: %s", m.Source.DBPath)
	}

	db, err := dbcore.OpenSQLite(m.Source.DBPath)
	if err != nil {
		return fmt.Errorf("open source database: %w", err)
	}
	defer func() { _ = db.Close() }()

	if err := dbcore.IntegrityCheck(ctx, db); err != nil {
		return fmt.Errorf("source database is corrupted — run 'PRAGMA integrity_check' on %s to diagnose: %w",
			m.Source.DBPath, err)
	}

	ver, err := dbcore.SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("read schema version: %w", err)
	}
	if ver == "" {
		return fmt.Errorf("source database has no alembic version — not a Quay database")
	}
	slog.Info("source schema version", "version", ver)

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

	if !m.SkipInstall {
		if m.Source.ImageArchive == "" && m.Source.Image == "" {
			return fmt.Errorf("no image archive found — provide -image-archive or -image flag")
		}
	}

	slog.Info("validation passed")
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
