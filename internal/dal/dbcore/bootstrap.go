package dbcore

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"log/slog"
)

// Setup opens the SQLite database at dbPath and ensures the schema is
// current. On a fresh database it initializes the schema; on an existing
// one it applies any pending migrations. Safe to call on every startup.
// The caller owns the returned *sql.DB and must close it.
func Setup(ctx context.Context, dbPath string) (*sql.DB, error) {
	db, err := OpenSQLite(dbPath)
	if err != nil {
		return nil, fmt.Errorf("open: %w", err)
	}
	if err := ensureSchema(ctx, db, dbPath); err != nil {
		_ = db.Close()
		return nil, err
	}
	return db, nil
}

func ensureSchema(ctx context.Context, db *sql.DB, dbPath string) error {
	var tableCount int
	err := db.QueryRowContext(ctx,
		"SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
	).Scan(&tableCount)
	if err != nil {
		return fmt.Errorf("check tables: %w", err)
	}

	if tableCount == 0 {
		slog.Info("initializing database")
		if err := InitDatabase(ctx, db, io.Discard); err != nil {
			return fmt.Errorf("init database: %w", err)
		}
	}

	ver, err := SchemaVersion(ctx, db)
	if err != nil {
		return fmt.Errorf("schema version: %w", err)
	}

	if ver == TargetVersion {
		return nil
	}

	slog.Info("upgrading database", "from", ver, "to", TargetVersion)

	backupPath, err := BackupDatabase(ctx, db, dbPath)
	if err != nil {
		return fmt.Errorf("backup: %w", err)
	}
	slog.Info("database backup created", "path", backupPath)

	if err := ApplyMigrations(ctx, db, ver, TargetVersion, io.Discard); err != nil {
		return fmt.Errorf("migrate (restore from %s): %w", backupPath, err)
	}

	_ = CleanOldBackups(dbPath, 3)
	return nil
}
